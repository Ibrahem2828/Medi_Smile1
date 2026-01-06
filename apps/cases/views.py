# apps/cases/views.py
from django.db import models
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.permissions import IsAuthenticatedAndActive

from .models import Case, CaseAssignmentRequest, CaseSession, AIAnalysisSession, AIProposedCase
from .serializers import (
    CaseSerializer,
    CaseCreateSerializer,
    CaseUpdateSerializer,
    CaseStatusUpdateSerializer,
    CaseAssignSupervisorSerializer,
    CaseCreateFromAISerializer,
    CaseAssignmentRequestDecisionSerializer,
    CaseAssignmentRequestSerializer,
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
    CanCreateCase,
    CanViewCase,
    CanUpdateCase,
    CanManageCaseStatus,
    CanAssignSupervisor,
    CanRequestAssignment,
    CanCreateSession,
    CanReviewSession,
)
from .services import create_case_from_proposal
from django.core.exceptions import ValidationError
import logging
from django.db import transaction

logger = logging.getLogger(__name__)


# ============================================================
# Case List & Create
# ============================================================
class CaseListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticatedAndActive, CanCreateCase]

    def get_queryset(self):
        user = self.request.user

        if user.role.name == Role.TECH_SUPPORT:
            return Case.objects.all()

        if user.role.name == Role.PATIENT:
            return Case.objects.filter(patient=user)

        if user.role.name == Role.STUDENT:
            student_university_id = getattr(getattr(user, "studentprofile_profile", None), "university_id", None)
            return Case.objects.filter(
                models.Q(student=user) | models.Q(is_public=True, university_id=student_university_id)
            )

        if user.role.name == Role.SUPERVISOR:
            return Case.objects.filter(supervisor=user)

        if user.role.name == Role.UNIVERSITY_ADMIN:
            return Case.objects.filter(university=user.universityadminprofile_profile.university)

        return Case.objects.none()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CaseCreateSerializer
        return CaseSerializer

    def perform_create(self, serializer):
        serializer.save(context={"request": self.request})


# ============================================================
# Case Detail & Update
# ============================================================
class CaseDetailView(generics.RetrieveUpdateAPIView):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticatedAndActive, CanViewCase, CanUpdateCase]

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


class CaseCreateFromAIView(generics.CreateAPIView):
    """
    Patient accepts AI diagnosis and creates a critical case for university routing.
    """

    serializer_class = CaseCreateFromAISerializer
    permission_classes = [IsAuthenticatedAndActive]

    def perform_create(self, serializer):
        serializer.save(context={"request": self.request})


# ============================================================
# Assignment Requests
# ============================================================
class CaseAssignmentRequestCreateView(generics.CreateAPIView):
    serializer_class = CaseAssignmentRequestSerializer
    permission_classes = [IsAuthenticatedAndActive, CanRequestAssignment]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


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
        serializer.save(context={"request": self.request})


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
        serializer.save(context={"request": self.request})

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as exc:
            return Response({"status": "error", "message": "Invalid request", "errors": exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("AI proposal ingest failed", exc_info=exc)
            return Response(
                {"status": "error", "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.", "errors": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AIProposalNextView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request, session_id):
        session = AIAnalysisSession.objects.filter(id=session_id, patient=request.user).first()
        if not session:
            return Response({"status": "error", "message": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

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

        data = AIProposalNextSerializer(
            {
                "session_id": session.id,
                "proposal_id": proposal.proposal_id,
                "tooth_id": proposal.tooth_id,
                "fusion_decision": proposal.fusion_decision or {},
                "medical_report": proposal.medical_report or {},
                "metadata": proposal.metadata or {},
                "raw_proposal": proposal.raw_proposal or {},
            }
        ).data
        return Response({"status": "success", "data": data})


class AIProposalDecisionView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def post(self, request, session_id):
        session = AIAnalysisSession.objects.filter(id=session_id, patient=request.user).first()
        if not session:
            return Response({"status": "error", "message": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

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
            return Response({"status": "error", "message": "Invalid data", "errors": exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)
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
        return Case.objects.filter(status=Case.Status.NEW, university_id=sup_univ)


class SupervisorCaseDecisionView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def post(self, request, case_id):
        user = request.user
        if getattr(getattr(user, "role", None), "name", None) != Role.SUPERVISOR:
            return Response({"status": "error", "message": "Only supervisors allowed."}, status=status.HTTP_403_FORBIDDEN)
        sup_univ = getattr(getattr(user, "supervisorprofile_profile", None), "university_id", None)
        case = Case.objects.filter(id=case_id, status=Case.Status.NEW, university_id=sup_univ).first()
        if not case:
            return Response({"status": "error", "message": "Case not found or not eligible."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SupervisorCaseDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]

        if decision == "accept":
            case.status = Case.Status.ACCEPTED
            case.is_public = True
        else:
            case.status = Case.Status.REJECTED
            case.is_public = False
        case.save(update_fields=["status", "is_public", "updated_at"])

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
    permission_classes = [IsAuthenticatedAndActive]

    @transaction.atomic
    def post(self, request, case_id):
        user = request.user
        if getattr(getattr(user, "role", None), "name", None) != Role.STUDENT:
            return Response({"status": "error", "message": "Only students allowed."}, status=status.HTTP_403_FORBIDDEN)
        stu_univ = getattr(getattr(user, "studentprofile_profile", None), "university_id", None)
        case = Case.objects.select_for_update().filter(id=case_id, university_id=stu_univ).first()
        if not case or case.status != Case.Status.ACCEPTED:
            return Response({"status": "error", "message": "Case not available for assignment."}, status=status.HTTP_400_BAD_REQUEST)

        existing = CaseAssignmentRequest.objects.filter(case=case, student=user, status=CaseAssignmentRequest.Status.PENDING).first()
        if existing:
            return Response({"status": "error", "message": "Request already pending."}, status=status.HTTP_400_BAD_REQUEST)

        req = CaseAssignmentRequest.objects.create(case=case, student=user)
        req.apply_to_case()
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
        else:
            case.status = Case.Status.ACCEPTED
            case.is_public = True
            req.status = CaseAssignmentRequest.Status.REJECTED

        case.save(update_fields=["student", "status", "is_public", "updated_at"])
        req.save(update_fields=["status", "updated_at"])

        return Response({"status": "success", "message": "Assignment decision saved.", "data": {"status": case.status, "student": str(case.student_id) if case.student_id else None}})
