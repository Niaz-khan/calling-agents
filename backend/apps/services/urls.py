from django.urls import path

from .views import ServiceViewSet

urlpatterns = [
    path("services", ServiceViewSet.as_view({"get": "list", "post": "create"})),
    path(
        "services/<int:pk>",
        ServiceViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
]