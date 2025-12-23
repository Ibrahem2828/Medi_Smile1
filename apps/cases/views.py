from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from rest_framework import generics, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.permissions import IsStudent, IsSupervisor
from medismile.utils.auth import resolve_request_user
from medismile.utils.pagination import StandardResultsSetPagination

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

# selectors
from .selectors.case_queries import (
    get_cases_for_user,
    get_assignment_requests_for_user,
    get_sessions_for_case,
)

# services
from .services.assignment import (
    request_case_assignment as service_request_assignment,
    decide_assignment_request,
)
from .services.session_logic import (
    create_session,
    review_session,
)
from .services.case_lifecycle import change_case_status


# ============================================================
# Unified API Response Helpers
# ============================================================

def api_success(message, data=None, status_code=status.HTTP_200_OK):
    return Response(
        {"status": "success", "message": message, "data": data},
        status=status_code,
    )


def api_error(message, status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {"status": "error", "message": message},
        status=status_code,
    )


# ============================================================
# Cases
# ============================================================

class CaseListView(generics.ListCreateAPIView):
    """
    List cases (role-based visibility)
    Create case:
    - Patient: for himself only
    - Others: allowed only if serializer permits (admin scenarios)
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = resolve_request_user(self.request)
        return get_cases_for_user(user)

    def get_serializer_class(self):
        return CaseCreateSerializer if self.request.method == "POST" else CaseSerializer

    def perform_create(self, serializer):
        serializer.save()


class CaseDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve / update a case within role scope.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = resolve_request_user(self.request)
        return get_cases_for_user(user)

    def get_serializer_class(self):
        return CaseUpdateSerializer if self.request.method in ["PUT", "PATCH"] else CaseSerializer

    @transaction.atomic
    def perform_update(self, serializer):
        user = resolve_request_user(self.request)
        case = self.get_object()
        old_status = case.status

        updated_case = serializer.save()

        if old_status != updated_case.status:
            change_case_status(
                case=updated_case,
                new_status=updated_case.status,
                actor=user,
            )


# ============================================================
# Assignment Requests
# ============================================================

class CaseAssignmentRequestListView(generics.ListCreateAPIView):
    """
    - Student: list/create own assignment requests
    - Supervisor: list requests for supervised cases
    - Admin / IT: list all
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CaseAssignmentRequestSerializer

    def get_queryset(self):
        user = resolve_request_user(self.request)
        return get_assignment_requests_for_user(user)

    @transaction.atomic
    def perform_create(self, serializer):
        user = resolve_request_user(self.request)

        if user.role != "student":
            raise serializers.ValidationError(_("Only students can request assignments."))

        case = serializer.validated_data.get("case")
        message = serializer.validated_data.get("message", "")

        service_request_assignment(
            case=case,
            student=user,
            message=message,
        )


class CaseAssignmentRequestDetailView(generics.RetrieveUpdateAPIView):
    """
    Supervisor accepts / rejects assignment request.
    """

    permission_classes = [IsAuthenticated, IsSupervisor]
    serializer_class = CaseAssignmentRequestSerializer
    queryset = CaseAssignmentRequest.objects.select_related("case", "student")

    @transaction.atomic
    def perform_update(self, serializer):
        supervisor = resolve_request_user(self.request)
        assignment = self.get_object()

        new_status = serializer.validated_data.get("status")
        response = serializer.validated_data.get("supervisor_response", "")

        if new_status not in [
            CaseAssignmentRequest.Status.ACCEPTED,
            CaseAssignmentRequest.Status.REJECTED,
        ]:
            raise serializers.ValidationError(_("Invalid status change."))

        decide_assignment_request(
            assignment=assignment,
            supervisor=supervisor,
            accept=new_status == CaseAssignmentRequest.Status.ACCEPTED,
            response=response,
        )


# ============================================================
# Treatment Sessions
# ============================================================

class CaseSessionListCreateView(generics.ListCreateAPIView):
    """
    Sessions per case:
    - Student: list & create
    - Supervisor: list
    - Patient: read-only
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = resolve_request_user(self.request)
        case = get_object_or_404(Case, id=self.kwargs["case_id"])
        return get_sessions_for_case(case, user=user)

    def get_serializer_class(self):
        return CaseSessionCreateSerializer if self.request.method == "POST" else CaseSessionSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        user = resolve_request_user(self.request)
        case = serializer.validated_data["case"]
        notes = serializer.validated_data["notes"]

        session = create_session(
            case=case,
            student=user,
            notes=notes,
        )

        # 🔗 Hook: notify supervisor (real-time supervision)
        # apps.notifications / apps.messaging will listen to this event
        # Example (future):
        # notify_supervisor_new_session(session)

        return session


class CaseSessionReviewView(generics.UpdateAPIView):
    """
    Supervisor reviews a treatment session.
    """

    permission_classes = [IsAuthenticated, IsSupervisor]
    serializer_class = CaseSessionReviewSerializer
    queryset = CaseSession.objects.select_related("case", "student", "supervisor")

    @transaction.atomic
    def perform_update(self, serializer):
        supervisor = resolve_request_user(self.request)
        session = self.get_object()

        approve = serializer.validated_data["status"] == CaseSession.Status.APPROVED
        feedback = serializer.validated_data.get("supervisor_feedback", "")

        review_session(
            session=session,
            supervisor=supervisor,
            approve=approve,
            feedback=feedback,
        )

        # 🔗 Hook: notify student of review decision
        # notify_student_session_review(session)


# ============================================================
# Legacy API (Backward Compatibility)
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
@transaction.atomic
def request_case_assignment(request, case_id):
    """
    Legacy endpoint for assignment request.
    """

    student = resolve_request_user(request)
    case = get_object_or_404(Case, id=case_id)
    message = request.data.get("message", "")

    assignment = service_request_assignment(
        case=case,
        student=student,
        message=message,
    )

    serializer = CaseAssignmentRequestSerializer(assignment)
    return api_success(
        _("Assignment request created."),
        serializer.data,
        status.HTTP_201_CREATED,
    )
