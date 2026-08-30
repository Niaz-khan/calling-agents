from django.urls import path

from .views import AppointmentViewSet

urlpatterns = [
    path("appointments", AppointmentViewSet.as_view({"get": "list", "post": "create"})),
    path(
        "appointments/<int:pk>",
        AppointmentViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
]