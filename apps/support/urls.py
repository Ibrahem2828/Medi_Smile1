from django.urls import path
from .views import (
    SupportTicketListView,
    SupportTicketDetailView,
    SupportTicketResponseListView,
    SupportTicketStatsView
)

app_name = 'support'

urlpatterns = [
    # Support Tickets
    path('tickets/', SupportTicketListView.as_view(), name='ticket-list'),
    path('tickets/<uuid:ticket_id>/', SupportTicketDetailView.as_view(), name='ticket-detail'),
    path('tickets/<uuid:ticket_id>/responses/', SupportTicketResponseListView.as_view(), name='ticket-responses'),
    
    # Statistics (tech support only)
    path('stats/', SupportTicketStatsView.as_view(), name='ticket-stats'),
]

