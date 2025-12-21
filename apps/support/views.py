from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from .models import SupportTicket, SupportTicketResponse
from .serializers import (
    SupportTicketCreateSerializer,
    SupportTicketListSerializer,
    SupportTicketDetailSerializer,
    SupportTicketUpdateSerializer,
    SupportTicketResponseCreateSerializer,
    SupportTicketResponseSerializer,
)
from apps.accounts.permissions import IsTechSupport
from medismile.utils.auth import resolve_request_user


# ============================================================
# Unified API Response
# ============================================================

class APIResponse:
    @staticmethod
    def success(message, data=None, status_code=status.HTTP_200_OK):
        return Response(
            {
                "status": "success",
                "message": message,
                "data": data,
            },
            status=status_code,
        )

    @staticmethod
    def error(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response(
            {
                "status": "error",
                "message": message,
                "errors": errors,
            },
            status=status_code,
        )


# ============================================================
# Support Ticket – List & Create
# ============================================================

class SupportTicketListView(generics.ListCreateAPIView):
    """
    - Any authenticated user: create ticket
    - Tech support: see all tickets
    - Normal users: see own tickets only
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SupportTicketCreateSerializer
        return SupportTicketListSerializer

    def get_queryset(self):
        user = resolve_request_user(self.request)

        queryset = (
            SupportTicket.objects
            .select_related("created_by", "assigned_to")
            .annotate(responses_count=Count("responses"))
        )

        if user.role != "tech_support":
            queryset = queryset.filter(created_by=user)

        # Optional filters
        status_filter = self.request.query_params.get("status")
        priority_filter = self.request.query_params.get("priority")
        category_filter = self.request.query_params.get("category")

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        if category_filter:
            queryset = queryset.filter(category=category_filter)

        return queryset.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(
            _("Support tickets retrieved successfully."),
            serializer.data,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save()

        return APIResponse.success(
            _("Support ticket created successfully."),
            SupportTicketDetailSerializer(ticket).data,
            status.HTTP_201_CREATED,
        )


# ============================================================
# Support Ticket – Detail / Update
# ============================================================

class SupportTicketDetailView(generics.RetrieveUpdateAPIView):
    """
    - Owner: read-only
    - Tech support: update
    """

    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "ticket_id"

    def get_queryset(self):
        user = resolve_request_user(self.request)

        queryset = (
            SupportTicket.objects
            .select_related("created_by", "assigned_to")
            .prefetch_related("responses__author")
        )

        if user.role != "tech_support":
            queryset = queryset.filter(created_by=user)

        return queryset

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return SupportTicketUpdateSerializer
        return SupportTicketDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        ticket = self.get_object()
        serializer = self.get_serializer(ticket)
        return APIResponse.success(
            _("Support ticket retrieved successfully."),
            serializer.data,
        )

    def update(self, request, *args, **kwargs):
        user = resolve_request_user(request)
        if user.role != "tech_support":
            return APIResponse.error(
                _("You are not allowed to update this ticket."),
                status_code=status.HTTP_403_FORBIDDEN,
            )

        ticket = self.get_object()
        serializer = self.get_serializer(ticket, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save()

        return APIResponse.success(
            _("Support ticket updated successfully."),
            SupportTicketDetailSerializer(ticket).data,
        )


# ============================================================
# Support Ticket Responses
# ============================================================

class SupportTicketResponseListView(generics.ListCreateAPIView):
    """
    List & create responses for a support ticket.
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SupportTicketResponseCreateSerializer
        return SupportTicketResponseSerializer

    def get_ticket(self):
        return get_object_or_404(
            SupportTicket,
            id=self.kwargs["ticket_id"],
        )

    def get_queryset(self):
        ticket = self.get_ticket()
        user = resolve_request_user(self.request)

        queryset = SupportTicketResponse.objects.filter(ticket=ticket).select_related("author")

        # Hide internal notes from non-tech users
        if user.role != "tech_support":
            queryset = queryset.filter(is_internal=False)

        # Prevent access to чужие tickets
        if user.role != "tech_support" and ticket.created_by != user:
            return SupportTicketResponse.objects.none()

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["ticket"] = self.get_ticket()
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(
            _("Ticket responses retrieved successfully."),
            serializer.data,
        )

    def create(self, request, *args, **kwargs):
        ticket = self.get_ticket()
        user = resolve_request_user(request)

        if user.role != "tech_support" and ticket.created_by != user:
            return APIResponse.error(
                _("You are not allowed to respond to this ticket."),
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.save()

        return APIResponse.success(
            _("Response sent successfully."),
            SupportTicketResponseSerializer(response).data,
            status.HTTP_201_CREATED,
        )


# ============================================================
# Support Ticket Statistics (Tech Support)
# ============================================================

class SupportTicketStatsView(APIView):
    """
    Statistics dashboard for tech support.
    """

    permission_classes = [IsAuthenticated, IsTechSupport]

    def get(self, request):
        stats = {
            "total": SupportTicket.objects.count(),
            "open": SupportTicket.objects.filter(status=SupportTicket.Status.OPEN).count(),
            "in_progress": SupportTicket.objects.filter(status=SupportTicket.Status.IN_PROGRESS).count(),
            "resolved": SupportTicket.objects.filter(status=SupportTicket.Status.RESOLVED).count(),
            "closed": SupportTicket.objects.filter(status=SupportTicket.Status.CLOSED).count(),
            "urgent": SupportTicket.objects.filter(
                priority=SupportTicket.Priority.URGENT,
                status__in=[
                    SupportTicket.Status.OPEN,
                    SupportTicket.Status.IN_PROGRESS,
                ],
            ).count(),
        }

        return APIResponse.success(
            _("Support ticket statistics retrieved successfully."),
            stats,
        )
