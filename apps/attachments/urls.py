from django.urls import path
from . import views

urlpatterns = [
    path('', views.AttachmentListView.as_view(), name='attachment-list'),
    path('<uuid:pk>/', views.AttachmentDetailView.as_view(), name='attachment-detail'),
    path('<uuid:attachment_id>/download/', views.download_attachment, name='download-attachment'),
    path('<uuid:attachment_id>/preview/', views.preview_attachment, name='preview-attachment'),
]