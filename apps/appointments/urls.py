from django.urls import path
from . import views

urlpatterns = [
    path('', views.AppointmentListView.as_view(), name='appointment-list'),
    path('<uuid:pk>/', views.AppointmentDetailView.as_view(), name='appointment-detail'),
    path('<uuid:appointment_id>/confirm/', views.confirm_appointment, name='confirm-appointment'),
    path('<uuid:appointment_id>/start/', views.start_appointment, name='start-appointment'),
    path('<uuid:appointment_id>/complete/', views.complete_appointment, name='complete-appointment'),
    path('<uuid:appointment_id>/cancel/', views.cancel_appointment, name='cancel-appointment'),
    path('<uuid:appointment_id>/no-show/', views.mark_no_show, name='mark-no-show'),
]