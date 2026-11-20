from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core import views as core_views

urlpatterns = [
    path("", core_views.home, name="home"),
    path("health/live", core_views.live, name="health-live"),
    path("health/ready", core_views.ready, name="health-ready"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
    path("notes/", include("apps.notes.urls_html")),
    path("api/v1/", include("apps.notes.urls_api")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
]
