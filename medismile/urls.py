from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('apps.accounts.urls')),
    path('api/v1/universities/', include('apps.universities.urls')),
    path('api/v1/cases/', include('apps.cases.urls')),
    path('api/v1/ai/', include('apps.ai.urls')),
    path('api/v1/appointments/', include('apps.appointments.urls')),
    path('api/v1/evaluations/', include('apps.evaluations.urls')),
    path('api/v1/messaging/', include('apps.messaging.urls')),
    path('api/v1/community/', include('apps.community.urls')),
    path('api/v1/attachments/', include('apps.attachments.urls')),
    path('api/v1/audit/', include('apps.audit.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)