# apps/support/urls.py
from django.urls import path

from .views import (
    SupportTicketListView,
    SupportTicketDetailView,
    SupportTicketResponseListView,
    SupportTicketStatsView,
    SupportTicketCloseView,
)

app_name = "support"

urlpatterns = [
    # Tickets
    path("tickets/", SupportTicketListView.as_view(), name="ticket-list"),
    path("tickets/<uuid:ticket_id>/", SupportTicketDetailView.as_view(), name="ticket-detail"),
    path("tickets/<uuid:ticket_id>/close/", SupportTicketCloseView.as_view(), name="ticket-close"),

    # Responses
    path("tickets/<uuid:ticket_id>/responses/", SupportTicketResponseListView.as_view(), name="ticket-response-list"),

    # Analytics (Tech Support)
    path("analytics/overview/", SupportTicketStatsView.as_view(), name="ticket-stats"),
]
