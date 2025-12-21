from django.urls import path
from .views import (
    SupportTicketListView,
    SupportTicketDetailView,
    SupportTicketResponseListView,
    SupportTicketStatsView,
)

app_name = "support"

urlpatterns = [

    # =========================================================
    # Support Tickets (Core)
    # =========================================================

    # List tickets / Create new ticket
    path(
        "tickets/",
        SupportTicketListView.as_view(),
        name="ticket-list",
    ),

    # Retrieve / Update ticket (tech support only for update)
    path(
        "tickets/<uuid:ticket_id>/",
        SupportTicketDetailView.as_view(),
        name="ticket-detail",
    ),

    # =========================================================
    # Ticket Responses (Conversation)
    # =========================================================

    # List responses / Add response to ticket
    path(
        "tickets/<uuid:ticket_id>/responses/",
        SupportTicketResponseListView.as_view(),
        name="ticket-response-list",
    ),

    # =========================================================
    # Analytics & Dashboard (Tech Support)
    # =========================================================

    path(
        "analytics/overview/",
        SupportTicketStatsView.as_view(),
        name="ticket-stats",
    ),
]
