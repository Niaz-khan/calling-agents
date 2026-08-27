from django.contrib import admin
from django.urls import include, path

from core import views as core_views

urlpatterns = [
    path("", core_views.root),
    path("health", core_views.health),
    path("db-health", core_views.db_health),
    path("auth/", include("accounts.urls")),
    path("", include("agents.urls")),
    path("", include("crm.urls")),
    path("", include("conversations.urls")),
    path("", include("appointments.urls")),
    path("", include("telephony.urls")),
    path("", include("knowledge.urls")),
    path("", include("analytics.urls")),
    path("admin/", admin.site.urls),
]
