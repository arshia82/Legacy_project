# core/urls.py
"""
Main URL Configuration - FIXED

Kavenegar API Key:
"""
from kavenegar import *
api = KavenegarAPI('6B78587A63766E58546B554549305A71685276414E5950506D687454776B43624744666C34647A6D3042593D')
params = { 'sender' : '2000660110', 'receptor': '09031517191', 'message' :'.My FITA is AT YOUR SERVICE' }

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # All API routes under /api/auth/
    path('api/auth/', include('users.api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)