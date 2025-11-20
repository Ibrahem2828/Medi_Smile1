from django.urls import path
from . import views

urlpatterns = [
    path('', views.ContentListView.as_view(), name='content-list'),
    path('<uuid:pk>/', views.ContentDetailView.as_view(), name='content-detail'),
    path('<uuid:content_id>/comments/', views.ContentCommentListView.as_view(), name='content-comment-list'),
    path('<uuid:content_id>/like/', views.like_content, name='like-content'),
    path('trending/', views.trending_content, name='trending-content'),
]