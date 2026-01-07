from django.contrib import admin
from django.urls import include, path

from config.settings import DEBUG

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("movies.api.urls")),
]

# Additional URLs for debug mode
if DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularRedocView,
        SpectacularSwaggerView,
    )

    urlpatterns = [
        *urlpatterns,
        *debug_toolbar_urls(),
        path("api-auth/", include("rest_framework.urls")),
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            "api/schema/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
    ]
