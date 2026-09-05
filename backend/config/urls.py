from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.tenancy.urls")),
    path("", include("apps.agents.urls")),
    path("", include("apps.crm.urls")),
    path("", include("apps.appointments.urls")),
    path("", include("apps.services.urls")),
    path("", include("apps.telephony.urls")),
    path("", include("apps.conversations.urls")),
    path("", include("apps.knowledge.urls")),
    path("", include("apps.analytics.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.cms.urls")),
    path("", include("apps.platform.urls")),
]