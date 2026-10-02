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
from drf_spectacular.utils import OpenApiResponse, extend_schema
from medismile.openapi import ErrorEnvelope, GenericSuccess, success_envelope
from medismile.utils.scoping import get_user_university_id

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
    AICriticalCaseCreateSerializer,
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
from .services import create_ai_critical_case, create_case, create_case_from_proposal, request_case_assignment
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
        try:
            user = self.request.user
            role_name = getattr(getattr(user, "role", None), "name", None)
            if not role_name:
                logger.warning("cases.list: user %s has no role; returning empty queryset", getattr(user, "id", None))
                return Case.objects.none()

            # Optional query param to scope cases by university (used by Admin / Tech Support)
            requested_university_id = self.request.query_params.get("university_id")

            if role_name == Role.TECH_SUPPORT:
                qs = Case.objects.all()
                if requested_university_id:
                    qs = qs.filter(university_id=requested_university_id)
                return qs

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
                admin_univ_id = getattr(admin_profile, "university_id", None)
                university_id = requested_university_id or admin_univ_id
                if not university_id:
                    # Missing profile/university should not crash; return no cases instead of 500/502.
                    logger.warning(
                        "cases.list: university admin missing profile/university (user=%s, profile=%s)",
                        getattr(user, "id", None),
                        bool(admin_profile),
                    )
                    return Case.objects.none()
                return Case.objects.filter(university_id=university_id)

            return Case.objects.none()
        except Exception:
            logger.exception("cases.list: unexpected failure (user=%s)", getattr(getattr(self, "request", None), "user", None))
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

    serializer_class = CaseAssignmentRequestDecisionSerializer
    permission_classes = [IsAuthenticatedAndActive]
    http_method_names = ["patch"]

    def get_queryset(self):
        # Scope to the supervisor's own university (and to cases they already
        # supervise, if any) so a supervisor elsewhere gets 404, not a takeover.
        user = self.request.user
        if getattr(getattr(user, "role", None), "name", None) != Role.SUPERVISOR:
            return CaseAssignmentRequest.objects.none()
        sup_univ = get_user_university_id(user)
        if not sup_univ:
            return CaseAssignmentRequest.objects.none()
        return (
            CaseAssignmentRequest.objects
            .select_related("case", "student")
            .filter(case__university_id=sup_univ)
            .filter(models.Q(case__supervisor__isnull=True) | models.Q(case__supervisor=user))
        )


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

        elif user.role.name == Role.UNIVERSITY_ADMIN:
            university_id = get_user_university_id(user)
            qs = qs.filter(case__university_id=university_id) if university_id else qs.none()

        elif user.role.name != Role.TECH_SUPPORT:
            qs = qs.none()

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

    def create(self, request, *args, **kwargs):
        return Response(
            {
                "detail": "This legacy endpoint is disabled. Route a server-generated diagnosis_id through /api/cases/ai/create/.",
            },
            status=status.HTTP_410_GONE,
        )


_CaseEnvelope = success_envelope("CaseEnvelope", CaseSerializer())


class AICriticalCaseCreateView(APIView):
    """
    POST /api/cases/ai/create/ — patient submits their AI analysis to a
    university. Promotes the case auto-created by /api/ai/diagnose/ (if still
    NEW and unscoped) or creates a new one. The case then appears in
    /api/cases/supervisor/new/ for that university's supervisors.
    """

    permission_classes = [IsAuthenticatedAndActive, CanCreateCase]

    @extend_schema(
        request=AICriticalCaseCreateSerializer,
        responses={
            200: OpenApiResponse(_CaseEnvelope, description="Existing auto-created case promoted."),
            201: OpenApiResponse(_CaseEnvelope, description="New case created."),
            400: ErrorEnvelope,
        },
        tags=["cases"],
    )
    def post(self, request):
        serializer = AICriticalCaseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            case, created = create_ai_critical_case(
                patient=request.user,
                university=data["university"],
                title=data.get("title") or "",
                description=data.get("description") or "",
                diagnosis_id=data["diagnosis_id"],
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
        return Response(
            {
                "status": "success",
                "message": "Case created." if created else "Case submitted to university.",
                "data": CaseSerializer(case, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AIProposalNextView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    @extend_schema(
        responses={200: success_envelope("AIProposalNextEnvelope", AIProposalNextSerializer(allow_null=True)), 404: ErrorEnvelope},
        tags=["cases"],
    )
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

    @extend_schema(
        request=AIProposalDecisionSerializer,
        responses={200: GenericSuccess, 400: ErrorEnvelope, 404: ErrorEnvelope},
        tags=["cases"],
    )
    def post(self, request, session_id):
        # Sessions produced by the retired client-ingest route have no
        # server-verifiable provenance. Never promote their payload into a
        # medical case; patients must route an AIDiagnosis by diagnosis_id.
        return Response(
            {"detail": "Legacy client AI proposals cannot be accepted. Request a server analysis first."},
            status=status.HTTP_410_GONE,
        )

        # Kept below temporarily as migration reference for historical data;
        # it is deliberately unreachable.
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
                {"status": "error", "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.", "errors": None},
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

    @extend_schema(
        request=SupervisorCaseDecisionSerializer,
        responses={200: GenericSuccess, 403: ErrorEnvelope, 404: ErrorEnvelope},
        tags=["cases"],
    )
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
        case.save(update_fields=["university", "status", "is_public", "updated_at"])

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
        stu_univ = get_user_university_id(user)
        if not stu_univ:
            return Case.objects.none()
        return Case.objects.filter(status=Case.Status.ACCEPTED, university_id=stu_univ, student__isnull=True, is_public=True)


class StudentRequestAssignmentView(APIView):
    permission_classes = [IsAuthenticatedAndActive, CanRequestAssignment]

    @extend_schema(
        request=StudentAssignmentRequestSerializer,
        responses={200: GenericSuccess, 400: ErrorEnvelope},
        tags=["cases"],
    )
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
        sup_univ = get_user_university_id(user)
        if not sup_univ:
            return CaseAssignmentRequest.objects.none()
        return CaseAssignmentRequest.objects.filter(
            status=CaseAssignmentRequest.Status.PENDING,
            case__status=Case.Status.NEEDS_ASSIGNMENT_APPROVAL,
            case__university_id=sup_univ,
        ).select_related("case", "student")


class SupervisorAssignmentDecisionView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    @extend_schema(
        request=AssignmentDecisionSerializer,
        responses={200: GenericSuccess, 400: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
        tags=["cases"],
    )
    @transaction.atomic
    def post(self, request, case_id):
        user = request.user
        if getattr(getattr(user, "role", None), "name", None) != Role.SUPERVISOR:
            return Response({"status": "error", "message": "Only supervisors allowed."}, status=status.HTTP_403_FORBIDDEN)
        sup_univ = get_user_university_id(user)
        if not sup_univ:
            return Response({"status": "error", "message": "Supervisor university not set."}, status=status.HTTP_403_FORBIDDEN)
        case = (
            Case.objects.select_for_update()
            .filter(id=case_id, status=Case.Status.NEEDS_ASSIGNMENT_APPROVAL, university_id=sup_univ)
            .filter(models.Q(supervisor__isnull=True) | models.Q(supervisor=user))
            .first()
        )
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
            # The approving supervisor supervises the treatment; without this the
            # case never shows up in supervisor-scoped lists, sessions or AI review.
            if not case.supervisor_id:
                case.supervisor = user
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

        case.save(update_fields=["student", "supervisor", "status", "is_public", "updated_at"])
        req.save(update_fields=["status", "updated_at"])

        return Response({"status": "success", "message": "Assignment decision saved.", "data": {"status": case.status, "student": str(case.student_id) if case.student_id else None}})
