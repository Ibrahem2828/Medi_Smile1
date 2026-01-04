# apps/cases/views.py
from django.db import models
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.permissions import IsAuthenticatedAndActive

from .models import Case, CaseAssignmentRequest, CaseSession
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
