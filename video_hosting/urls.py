# video_hosting_project/urls.py

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('videohosting/', include('videos_host.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)