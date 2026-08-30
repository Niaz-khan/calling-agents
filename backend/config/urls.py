from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("accounts.urls")),
    path("", include("agents.urls")),
    path("", include("crm.urls")),
    path("", include("telephony.urls")),
    path("", include("conversations.urls")),
    path("", include("core.urls")),
]