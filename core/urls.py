# FILE: myfita/apps/backend/core/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# --- ADDED: API Documentation imports ---
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
# -----------------------------------------

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("users.api.urls")),
    
    # --- ADDED: New API routes ---
    # Programs
    path("api/programs/", include("programs.api.urls")),
    
    # Program Delivery (PDF generation)
    path("api/delivery/", include("program_delivery.api.urls")),
    
    # Billing & Payments
    path("api/billing/", include("billing.api.urls")),
    
    # Matching (AI coach-athlete matching)
    path("api/matching/", include("matching.api.urls")),
    
    # Search & Discovery
    path("api/search/", include("search.api.urls")),
    
    # API Documentation (Swagger/ReDoc)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    
    # Health checks
    path("health/", include("core.health_urls")),
    # ------------------------------
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)