# apps/cases/views.py
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
    CaseAssignmentRequestSerializer,
    CaseSessionSerializer,
    CaseSessionCreateSerializer,
    CaseSessionReviewSerializer,
)
from .permissions import (
    CanCreateCase,
    CanViewCase,
    CanUpdateCase,
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
            return Case.objects.filter(student=user)

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


# ============================================================
# Assignment Requests
# ============================================================
class CaseAssignmentRequestCreateView(generics.CreateAPIView):
    serializer_class = CaseAssignmentRequestSerializer
    permission_classes = [IsAuthenticatedAndActive, CanRequestAssignment]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


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
