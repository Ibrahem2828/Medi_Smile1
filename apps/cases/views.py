# apps/cases/views.py
from copy import deepcopy
import uuid
from django.db import models
from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.permissions import IsAuthenticatedAndActive

from .models import Case, CaseAssignmentRequest, CaseHistory, CaseSession, AIAnalysisSession, AIProposedCase
from .serializers import (
    CaseSerializer,
    CaseCreateSerializer,
    CaseUpdateSerializer,
    CaseStatusUpdateSerializer,
    CaseAssignSupervisorSerializer,
    CaseAssignmentRequestDecisionSerializer,
    CaseAssignmentRequestSerializer,
    StudentAssignmentRequestSerializer,
    CaseSessionSerializer,
    CaseSessionCreateSerializer,
    CaseSessionReviewSerializer,
    AIProposalBatchSerializer,
    AIProposalDecisionSerializer,
    AIProposalNextSerializer,
    SupervisorCaseDecisionSerializer,
    AssignmentDecisionSerializer,
)
from .permissions import (
    CanViewCase,
    CanUpdateCase,
    CanManageCaseStatus,
    CanAssignSupervisor,
    CanRequestAssignment,
    CanCreateCase,
    CanCreateSession,
    CanReviewSession,
)
from .services import create_case, create_case_from_proposal, request_case_assignment
from django.core.exceptions import ValidationError
import logging
import traceback
from django.db import transaction

logger = logging.getLogger(__name__)


def _case_id_visible_to_patient(case_id, patient) -> bool:
    try:
        case_uuid = uuid.UUID(str(case_id))
    except (TypeError, ValueError):
        return False
    return Case.objects.filter(id=case_uuid, patient=patient).exists()


def _sanitize_ai_metadata(metadata, *, patient):
    if not isinstance(metadata, dict):
        return metadata
    cleaned = dict(metadata)
    case_id = cleaned.get("case_id")
    if case_id and not _case_id_visible_to_patient(case_id, patient):
        cleaned.pop("case_id", None)
    return cleaned


def _sanitize_ai_raw_proposal(raw_proposal, *, patient):
    if not isinstance(raw_proposal, dict):
        return raw_proposal
    cleaned = deepcopy(raw_proposal)
    if "case_id" in cleaned and not _case_id_visible_to_patient(cleaned.get("case_id"), patient):
        cleaned.pop("case_id", None)
    if isinstance(cleaned.get("metadata"), dict):
        cleaned["metadata"] = _sanitize_ai_metadata(cleaned["metadata"], patient=patient)
    return cleaned


# ============================================================
# Case List & Create
# ============================================================
class CaseListCreateView(generics.ListCreateAPIView):
    """
    List cases and allow patients to create a case directly.
    """

    permission_classes = [IsAuthenticatedAndActive, CanCreateCase]
    http_method_names = ["get", "post"]

    def get_queryset(self):
        user = self.request.user
        role_name = getattr(getattr(user, "role", None), "name", None)
        if not role_name:
            logger.warning("cases.list: user %s has no role; returning empty queryset", getattr(user, "id", None))
            return Case.objects.none()

        if role_name == Role.TECH_SUPPORT:
            return Case.objects.all()

        if role_name == Role.PATIENT:
            return Case.objects.filter(patient=user)

        if role_name == Role.STUDENT:
            student_university_id = getattr(getattr(user, "studentprofile_profile", None), "university_id", None)
            return Case.objects.filter(
                models.Q(student=user) | models.Q(is_public=True, university_id=student_university_id)
            )

        if role_name == Role.SUPERVISOR:
            return Case.objects.filter(supervisor=user)

        if role_name == Role.UNIVERSITY_ADMIN:
            admin_profile = getattr(user, "universityadminprofile_profile", None)
            if not admin_profile or not admin_profile.university_id:
                # Missing profile/university should not crash; return no cases instead of 500/502.
                logger.warning(
                    "cases.list: university admin missing profile/university (user=%s, profile=%s)",
                    getattr(user, "id", None),
                    bool(admin_profile),
                )
                return Case.objects.none()
            return Case.objects.filter(university_id=admin_profile.university_id)

        return Case.objects.none()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CaseCreateSerializer
        return CaseSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticatedAndActive(), CanCreateCase()]
        return [IsAuthenticatedAndActive()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            case = create_case(patient=request.user, data=serializer.validated_data)
        except ValidationError as exc:
            return Response(
                {
                    "status": "error",
                    "message": "Invalid data",
                    "errors": getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"status": "success", "data": CaseSerializer(case).data},
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# Case Detail & Update
# ============================================================
class CaseDetailView(generics.RetrieveUpdateAPIView):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticatedAndActive, CanViewCase, CanUpdateCase]

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticatedAndActive(), CanViewCase()]
        return [IsAuthenticatedAndActive(), CanUpdateCase()]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return CaseUpdateSerializer
        return CaseSerializer


class CaseStatusUpdateView(generics.UpdateAPIView):
    """
    Dedicated status transition endpoint for NEW/unassigned cases and onward.
    """

    queryset = Case.objects.all()
    serializer_class = CaseStatusUpdateSerializer
    permission_classes = [IsAuthenticatedAndActive, CanManageCaseStatus]
    http_method_names = ["patch"]


class CaseAssignSupervisorView(generics.UpdateAPIView):
    """
    Assign a supervisor to a case and scope it to that supervisor's university.
    """

    queryset = Case.objects.all()
    serializer_class = CaseAssignSupervisorSerializer
    permission_classes = [IsAuthenticatedAndActive, CanAssignSupervisor]
    http_method_names = ["patch"]


# ============================================================
# Assignment Requests
# ============================================================
class CaseAssignmentRequestCreateView(generics.CreateAPIView):
    serializer_class = StudentAssignmentRequestSerializer
    permission_classes = [IsAuthenticatedAndActive, CanRequestAssignment]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            req = request_case_assignment(
                student=request.user,
                case_id=self.kwargs["pk"],
                message=serializer.validated_data.get("message"),
            )
        except ValidationError as exc:
            return Response(
                {
                    "status": "error",
                    "message": "Invalid data",
                    "errors": getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"status": "success", "message": "Assignment requested.", "data": {"request_id": str(req.id)}})


class CaseAssignmentRequestDecisionView(generics.UpdateAPIView):
    """
    Supervisor accepts/rejects a student's assignment request.
    """

    queryset = CaseAssignmentRequest.objects.all()
    serializer_class = CaseAssignmentRequestDecisionSerializer
    permission_classes = [IsAuthenticatedAndActive]
    http_method_names = ["patch"]


# ============================================================
# Sessions
# ============================================================
class CaseSessionListView(generics.ListAPIView):
    serializer_class = CaseSessionSerializer
    permission_classes = [IsAuthenticatedAndActive]

    def get_queryset(self):
        case_id = self.kwargs["case_id"]
        user = self.request.user

        qs = CaseSession.objects.filter(case_id=case_id)

        if user.role.name == Role.PATIENT:
            qs = qs.filter(case__patient=user)

        elif user.role.name == Role.STUDENT:
            qs = qs.filter(student=user)

        elif user.role.name == Role.SUPERVISOR:
            qs = qs.filter(supervisor=user)

        return qs


class CaseSessionCreateView(generics.CreateAPIView):
    serializer_class = CaseSessionCreateSerializer
    permission_classes = [IsAuthenticatedAndActive, CanCreateSession]

    def perform_create(self, serializer):
        serializer.save()


class CaseSessionReviewView(generics.UpdateAPIView):
    queryset = CaseSession.objects.all()
    serializer_class = CaseSessionReviewSerializer
    permission_classes = [IsAuthenticatedAndActive, CanReviewSession]
    http_method_names = ["patch"]


# ============================================================
# AI Proposals Flow (patient)
# ============================================================

class AIProposalIngestView(generics.CreateAPIView):
    """
    Patient submits AI fusion output (multiple proposals). No case is created here.
    """
    serializer_class = AIProposalBatchSerializer
    permission_classes = [IsAuthenticatedAndActive]

    def perform_create(self, serializer):
        serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
        except ValidationError as exc:
            return Response(
                {
                    "status": "error",
                    "message": "Invalid request",
                    "errors": getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("AI proposal ingest failed", exc_info=exc)
            errors = str(exc) or repr(exc)
            if getattr(settings, "EXPOSE_ERROR_DETAILS", False):
                errors = {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
            return Response(
                {"status": "error", "message": "Unexpected error. See errors for details.", "errors": errors},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        session = serializer.instance
        proposals_count = session.proposals.count() if session else 0
        next_path = f"/api/cases/ai/proposals/{session.id}/next/" if session else None
        return Response(
            {
                "status": "success",
                "message": "AI proposals stored. Review the next proposal to create a case.",
                "data": {
                    "session_id": str(session.id),
                    "university": str(session.university_id) if session and session.university_id else None,
                    "proposals_count": proposals_count,
                    "next": next_path,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class AIProposalNextView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request, session_id):
        session = AIAnalysisSession.objects.filter(id=session_id, patient=request.user).first()
        if not session:
            return Response({"status": "error", "message": "Session not found or not accessible."}, status=status.HTTP_404_NOT_FOUND)

        proposals = list(session.proposals.filter(status=AIProposedCase.Status.PENDING_PATIENT))
        def sort_key(p):
            fusion = p.fusion_decision or {}
            urgency = (fusion.get("urgency_level") or "").lower()
            urgency_rank = {"high": 3, "medium": 2, "low": 1}.get(urgency, 0)
            match_score = fusion.get("match_score") or 0.0
            return (-urgency_rank, -match_score, p.created_at)
        proposals.sort(key=sort_key)
        proposal = proposals[0] if proposals else None
        if not proposal:
            return Response({"status": "success", "message": "No pending proposals.", "data": None})

        metadata = _sanitize_ai_metadata(proposal.metadata or {}, patient=request.user)
        raw_proposal = _sanitize_ai_raw_proposal(proposal.raw_proposal or {}, patient=request.user)
        data = AIProposalNextSerializer(
            {
                "session_id": session.id,
                "proposal_id": proposal.proposal_id,
                "tooth_id": proposal.tooth_id,
                "fusion_decision": proposal.fusion_decision or {},
                "medical_report": proposal.medical_report or {},
                "metadata": metadata,
                "raw_proposal": raw_proposal,
            }
        ).data
        return Response({"status": "success", "data": data})


class AIProposalDecisionView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def post(self, request, session_id):
        session = AIAnalysisSession.objects.filter(id=session_id, patient=request.user).first()
        if not session:
            return Response({"status": "error", "message": "Session not found or not accessible."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AIProposalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]
        pid = serializer.validated_data["proposal_id"]

        proposal = session.proposals.filter(proposal_id=pid).first()
        if not proposal:
            return Response({"status": "error", "message": "Proposal not found."}, status=status.HTTP_404_NOT_FOUND)

        if proposal.status != AIProposedCase.Status.PENDING_PATIENT:
            return Response({"status": "error", "message": "Proposal already decided."}, status=status.HTTP_400_BAD_REQUEST)

        if decision == "reject":
            proposal.status = AIProposedCase.Status.REJECTED_BY_PATIENT
            proposal.save(update_fields=["status", "updated_at"])
            return AIProposalNextView().get(request, session_id)

        # accept
        try:
            with transaction.atomic():
                proposal.status = AIProposedCase.Status.APPROVED_BY_PATIENT
                proposal.save(update_fields=["status", "updated_at"])
                case = create_case_from_proposal(
                    patient=request.user,
                    university_id=session.university_id,
                    proposal=proposal,
                )
                proposal.status = AIProposedCase.Status.CONVERTED
                proposal.converted_case = case
                proposal.save(update_fields=["status", "converted_case", "updated_at"])
            return Response({"status": "success", "message": "Case created from proposal.", "data": {"case_id": str(case.id)}})
        except ValidationError as exc:
            return Response(
                {
                    "status": "error",
                    "message": "Invalid data",
                    "errors": getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("AI proposal acceptance failed", exc_info=exc)
            return Response(
                {"status": "error", "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.", "errors": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ============================================================
# Supervisor: review new cases
# ============================================================

class SupervisorNewCasesView(generics.ListAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = CaseSerializer

    def get_queryset(self):
        user = self.request.user
        if getattr(getattr(user, "role", None), "name", None) != Role.SUPERVISOR:
            return Case.objects.none()
        sup_univ = getattr(getattr(user, "supervisorprofile_profile", None), "university_id", None)
        if not sup_univ:
            return Case.objects.none()
        return (
            Case.objects
            .filter(status=Case.Status.NEW)
            .filter(
                models.Q(university_id=sup_univ)
                | models.Q(
                    university_id__isnull=True,
                    patient__patientprofile_profile__university_id=sup_univ,
                )
            )
            .distinct()
        )


class SupervisorCaseDecisionView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def post(self, request, case_id):
        user = request.user
        if getattr(getattr(user, "role", None), "name", None) != Role.SUPERVISOR:
            return Response({"status": "error", "message": "Only supervisors allowed."}, status=status.HTTP_403_FORBIDDEN)
        sup_univ = getattr(getattr(user, "supervisorprofile_profile", None), "university_id", None)
        if not sup_univ:
            return Response({"status": "error", "message": "Supervisor university not set."}, status=status.HTTP_403_FORBIDDEN)
        case = (
            Case.objects
            .filter(id=case_id, status=Case.Status.NEW)
            .filter(
                models.Q(university_id=sup_univ)
                | models.Q(
                    university_id__isnull=True,
                    patient__patientprofile_profile__university_id=sup_univ,
                )
            )
            .first()
        )
        if not case:
            return Response({"status": "error", "message": "Case not found or not eligible."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SupervisorCaseDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]

        if decision == "accept":
            if not case.university_id:
                case.university_id = sup_univ
            case.status = Case.Status.ACCEPTED
            case.is_public = True
        else:
            case.status = Case.Status.REJECTED
            case.is_public = False
        case.save(update_fields=["status", "is_public", "updated_at"])

        CaseHistory.objects.create(
            case=case,
            action=CaseHistory.Action.STATUS_CHANGED,
            description="Supervisor decision on new case: %s." % decision,
            performed_by=user,
        )

        return Response({"status": "success", "message": "Decision saved.", "data": {"status": case.status}})


# ============================================================
# Student: available cases & request assignment
# ============================================================

class StudentAvailableCasesView(generics.ListAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = CaseSerializer

    def get_queryset(self):
        user = self.request.user
        if getattr(getattr(user, "role", None), "name", None) != Role.STUDENT:
            return Case.objects.none()
        stu_univ = getattr(getattr(user, "studentprofile_profile", None), "university_id", None)
        return Case.objects.filter(status=Case.Status.ACCEPTED, university_id=stu_univ, student__isnull=True, is_public=True)


class StudentRequestAssignmentView(APIView):
    permission_classes = [IsAuthenticatedAndActive, CanRequestAssignment]

    def post(self, request, case_id):
        serializer = StudentAssignmentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            req = request_case_assignment(
                student=request.user,
                case_id=case_id,
                message=serializer.validated_data.get("message"),
            )
        except ValidationError as exc:
            return Response(
                {
                    "status": "error",
                    "message": "Invalid data",
                    "errors": getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"status": "success", "message": "Assignment requested.", "data": {"request_id": str(req.id)}})


# ============================================================
# Supervisor: assignment decisions
# ============================================================

class SupervisorAssignmentRequestsView(generics.ListAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = CaseAssignmentRequestSerializer

    def get_queryset(self):
        user = self.request.user
        if getattr(getattr(user, "role", None), "name", None) != Role.SUPERVISOR:
            return CaseAssignmentRequest.objects.none()
        sup_univ = getattr(getattr(user, "supervisorprofile_profile", None), "university_id", None)
        return CaseAssignmentRequest.objects.filter(
            status=CaseAssignmentRequest.Status.PENDING,
            case__status=Case.Status.NEEDS_ASSIGNMENT_APPROVAL,
            case__university_id=sup_univ,
        ).select_related("case", "student")


class SupervisorAssignmentDecisionView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    @transaction.atomic
    def post(self, request, case_id):
        user = request.user
        if getattr(getattr(user, "role", None), "name", None) != Role.SUPERVISOR:
            return Response({"status": "error", "message": "Only supervisors allowed."}, status=status.HTTP_403_FORBIDDEN)
        sup_univ = getattr(getattr(user, "supervisorprofile_profile", None), "university_id", None)
        case = Case.objects.select_for_update().filter(id=case_id, status=Case.Status.NEEDS_ASSIGNMENT_APPROVAL, university_id=sup_univ).first()
        if not case:
            return Response({"status": "error", "message": "Case not found or not pending assignment approval."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AssignmentDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]

        req = CaseAssignmentRequest.objects.filter(case=case, status=CaseAssignmentRequest.Status.PENDING).order_by("-created_at").first()
        if not req:
            return Response({"status": "error", "message": "No pending assignment request."}, status=status.HTTP_400_BAD_REQUEST)

        if decision == "approve":
            case.student = req.student
            case.status = Case.Status.ASSIGNED
            case.is_public = False
            req.status = CaseAssignmentRequest.Status.ACCEPTED
            CaseHistory.objects.create(
                case=case,
                action=CaseHistory.Action.ASSIGNED,
                description="Supervisor approved assignment request.",
                performed_by=user,
            )
        else:
            case.status = Case.Status.ACCEPTED
            case.is_public = True
            req.status = CaseAssignmentRequest.Status.REJECTED
            CaseHistory.objects.create(
                case=case,
                action=CaseHistory.Action.STATUS_CHANGED,
                description="Supervisor rejected assignment request.",
                performed_by=user,
            )

        case.save(update_fields=["student", "status", "is_public", "updated_at"])
        req.save(update_fields=["status", "updated_at"])

        return Response({"status": "success", "message": "Assignment decision saved.", "data": {"status": case.status, "student": str(case.student_id) if case.student_id else None}})
