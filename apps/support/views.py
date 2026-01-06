# apps/support/views.py
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from rest_framework import generics, status
from rest_framework import serializers as drf_serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import logging

from apps.accounts.models import Role
from apps.accounts.permissions import IsTechSupport  # موجود عندك مسبقاً
from medismile.utils.auth import resolve_request_user

from .models import SupportTicket, SupportTicketResponse
from .serializers import (
    SupportTicketCreateSerializer,
    SupportTicketListSerializer,
    SupportTicketDetailSerializer,
    SupportTicketUpdateSerializer,
    SupportTicketResponseCreateSerializer,
    SupportTicketResponseSerializer,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# Unified API Response
# ------------------------------------------------------------

class APIResponse:
    @staticmethod
    def success(message, data=None, status_code=status.HTTP_200_OK):
        return Response({"status": "success", "message": message, "data": data}, status=status_code)

    @staticmethod
    def error(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({"status": "error", "message": message, "errors": errors}, status=status_code)


# ------------------------------------------------------------
# Pagination
# ------------------------------------------------------------

class SupportPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# ------------------------------------------------------------
# University scope helpers (membership-based)
# ------------------------------------------------------------

def _get_user_university_ids(user) -> set:
    """
    Collect university ids from the user's profile(s).
    Works for student/supervisor/university admin profiles and M2M fallback.
    """
    ids = set()

    profile_map = (
        "studentprofile_profile",
        "supervisorprofile_profile",
        "universityadminprofile_profile",
    )
    for attr in profile_map:
        try:
            profile = getattr(user, attr, None)
        except Exception:
            profile = None
        uni_id = getattr(profile, "university_id", None)
        if uni_id:
            ids.add(uni_id)

    rel = getattr(user, "universities", None)
    if rel is not None and hasattr(rel, "all"):
        ids |= set(rel.values_list("id", flat=True))

    return ids


def _ticket_queryset_for_user(user):
    qs = (
        SupportTicket.objects
        .select_related("created_by", "assigned_to")
        .annotate(responses_count=Count("responses"))
    )

    role_name = getattr(getattr(user, "role", None), "name", None)

    # IT/Tech support: all
    if role_name == Role.TECH_SUPPORT:
        return qs

    # University admin: tickets in his university scope (created_by's university via profile)
    if role_name == Role.UNIVERSITY_ADMIN:
        uni_ids = _get_user_university_ids(user)

        qs = qs.filter(
            Q(created_by__studentprofile_profile__university_id__in=uni_ids)
            | Q(created_by__supervisorprofile_profile__university_id__in=uni_ids)
            | Q(created_by__universityadminprofile_profile__university_id__in=uni_ids)
            | Q(created_by__universities__id__in=uni_ids)
        ).distinct()
        return qs

    # Others: only own tickets
    return qs.filter(created_by=user)


# ------------------------------------------------------------
# Tickets: List + Create
# ------------------------------------------------------------

class SupportTicketListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = SupportPagination

    def get_serializer_class(self):
        return SupportTicketCreateSerializer if self.request.method == "POST" else SupportTicketListSerializer

    def get_queryset(self):
        user = resolve_request_user(self.request)
        qs = _ticket_queryset_for_user(user)

        # Filters
        status_filter = self.request.query_params.get("status")
        priority_filter = self.request.query_params.get("priority")
        category_filter = self.request.query_params.get("category")
        related_app = self.request.query_params.get("related_app")

        if status_filter:
            qs = qs.filter(status=status_filter)
        if priority_filter:
            qs = qs.filter(priority=priority_filter)
        if category_filter:
            qs = qs.filter(category=category_filter)
        if related_app:
            qs = qs.filter(related_app=related_app)

        return qs.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        try:
            page = self.paginate_queryset(self.get_queryset())
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"status": "success", "message": _("Tickets retrieved."), "data": serializer.data}
            )
        except drf_serializers.ValidationError as exc:
            return APIResponse.error(_("Invalid request."), errors=exc.detail, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Failed to list support tickets", exc_info=exc)
            return APIResponse.error(_("حدث خطأ غير متوقع. يرجى المحاولة لاحقًا."))

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            ticket = serializer.save()

            return APIResponse.success(
                _("Support ticket created successfully."),
                SupportTicketDetailSerializer(ticket).data,
                status.HTTP_201_CREATED,
            )
        except drf_serializers.ValidationError as exc:
            return APIResponse.error(_("Invalid request."), errors=exc.detail, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Failed to create support ticket", exc_info=exc)
            return APIResponse.error(_("حدث خطأ غير متوقع. يرجى المحاولة لاحقًا."))


# ------------------------------------------------------------
# Ticket: Retrieve + Update
# ------------------------------------------------------------

class SupportTicketDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "ticket_id"

    def get_queryset(self):
        user = resolve_request_user(self.request)
        qs = (
            _ticket_queryset_for_user(user)
            .prefetch_related("responses__author")
        )
        return qs

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return SupportTicketUpdateSerializer
        return SupportTicketDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            ticket = self.get_object()
            return APIResponse.success(_("Ticket retrieved."), self.get_serializer(ticket).data)
        except drf_serializers.ValidationError as exc:
            return APIResponse.error(_("Invalid request."), errors=exc.detail, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Failed to retrieve support ticket", exc_info=exc)
            return APIResponse.error(_("حدث خطأ غير متوقع. يرجى المحاولة لاحقًا."))

    def update(self, request, *args, **kwargs):
        try:
            user = resolve_request_user(request)
            role_name = getattr(getattr(user, "role", None), "name", None)

            if role_name not in {Role.TECH_SUPPORT, Role.UNIVERSITY_ADMIN}:
                return APIResponse.error(_("You are not allowed to update this ticket."), status_code=status.HTTP_403_FORBIDDEN)

            ticket = self.get_object()
            serializer = self.get_serializer(ticket, data=request.data, partial=True, context={"request": request})
            serializer.is_valid(raise_exception=True)
            ticket = serializer.save()

            return APIResponse.success(_("Ticket updated successfully."), SupportTicketDetailSerializer(ticket).data)
        except drf_serializers.ValidationError as exc:
            return APIResponse.error(_("Invalid request."), errors=exc.detail, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Failed to update support ticket", exc_info=exc)
            return APIResponse.error(_("حدث خطأ غير متوقع. يرجى المحاولة لاحقًا."))


# ------------------------------------------------------------
# Ticket Close (creator or admin/tech)
# ------------------------------------------------------------

class SupportTicketCloseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        try:
            user = resolve_request_user(request)
            role_name = getattr(getattr(user, "role", None), "name", None)
            ticket = get_object_or_404(_ticket_queryset_for_user(user), id=ticket_id)

            if role_name not in {Role.TECH_SUPPORT, Role.UNIVERSITY_ADMIN} and ticket.created_by_id != user.id:
                return APIResponse.error(_("You are not allowed to close this ticket."), status_code=status.HTTP_403_FORBIDDEN)

            ticket.status = SupportTicket.Status.CLOSED
            ticket.closed_at = timezone.now()
            ticket.save(update_fields=["status", "closed_at", "updated_at"])

            return APIResponse.success(_("Ticket closed successfully."), SupportTicketDetailSerializer(ticket).data)
        except drf_serializers.ValidationError as exc:
            return APIResponse.error(_("Invalid request."), errors=exc.detail, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Failed to close support ticket", exc_info=exc)
            return APIResponse.error(_("حدث خطأ غير متوقع. يرجى المحاولة لاحقًا."))


# ------------------------------------------------------------
# Ticket Responses: List + Create
# ------------------------------------------------------------

class SupportTicketResponseListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = SupportPagination

    def get_serializer_class(self):
        return SupportTicketResponseCreateSerializer if self.request.method == "POST" else SupportTicketResponseSerializer

    def get_ticket(self):
        # use scoped ticket queryset
        user = resolve_request_user(self.request)
        qs = _ticket_queryset_for_user(user)
        return get_object_or_404(qs, id=self.kwargs["ticket_id"])

    def get_queryset(self):
        user = resolve_request_user(self.request)
        ticket = self.get_ticket()

        qs = SupportTicketResponse.objects.filter(ticket=ticket).select_related("author")

        # internal notes only for tech support
        if getattr(getattr(user, "role", None), "name", None) != Role.TECH_SUPPORT:
            qs = qs.filter(is_internal=False)

        return qs.order_by("created_at")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["ticket"] = self.get_ticket()
        return ctx

    def list(self, request, *args, **kwargs):
        try:
            page = self.paginate_queryset(self.get_queryset())
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"status": "success", "message": _("Responses retrieved."), "data": serializer.data})
        except drf_serializers.ValidationError as exc:
            return APIResponse.error(_("Invalid request."), errors=exc.detail, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Failed to list support ticket responses", exc_info=exc)
            return APIResponse.error(_("حدث خطأ غير متوقع. يرجى المحاولة لاحقًا."))

    def create(self, request, *args, **kwargs):
        try:
            ticket = self.get_ticket()
            user = resolve_request_user(request)
            role_name = getattr(getattr(user, "role", None), "name", None)

            # Only: ticket owner OR university admin (same scope) OR tech support
            if role_name not in {Role.TECH_SUPPORT, Role.UNIVERSITY_ADMIN} and ticket.created_by_id != user.id:
                return APIResponse.error(_("You are not allowed to respond to this ticket."), status_code=status.HTTP_403_FORBIDDEN)

            serializer = self.get_serializer(data=request.data, context={"request": request, "ticket": ticket})
            serializer.is_valid(raise_exception=True)
            response_obj = serializer.save()

            # Ensure non-tech cannot create internal notes (already validated)
            return APIResponse.success(_("Response sent successfully."), SupportTicketResponseSerializer(response_obj).data, status.HTTP_201_CREATED)
        except drf_serializers.ValidationError as exc:
            return APIResponse.error(_("Invalid request."), errors=exc.detail, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Failed to create support ticket response", exc_info=exc)
            return APIResponse.error(_("حدث خطأ غير متوقع. يرجى المحاولة لاحقًا."))


# ------------------------------------------------------------
# Analytics: Tech Support only
# ------------------------------------------------------------

class SupportTicketStatsView(APIView):
    permission_classes = [IsAuthenticated, IsTechSupport]

    def get(self, request):
        try:
            stats = {
                "total": SupportTicket.objects.count(),
                "open": SupportTicket.objects.filter(status=SupportTicket.Status.OPEN).count(),
                "in_progress": SupportTicket.objects.filter(status=SupportTicket.Status.IN_PROGRESS).count(),
                "resolved": SupportTicket.objects.filter(status=SupportTicket.Status.RESOLVED).count(),
                "closed": SupportTicket.objects.filter(status=SupportTicket.Status.CLOSED).count(),
                "urgent_open": SupportTicket.objects.filter(
                    priority=SupportTicket.Priority.URGENT,
                    status__in=[SupportTicket.Status.OPEN, SupportTicket.Status.IN_PROGRESS],
                ).count(),
            }
            return APIResponse.success(_("Support ticket statistics retrieved successfully."), stats)
        except drf_serializers.ValidationError as exc:
            return APIResponse.error(_("Invalid request."), errors=exc.detail, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Failed to fetch support ticket statistics", exc_info=exc)
            return APIResponse.error(_("حدث خطأ غير متوقع. يرجى المحاولة لاحقًا."))
