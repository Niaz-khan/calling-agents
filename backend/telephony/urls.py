from django.urls import path

from .views import PhoneNumberViewSet

urlpatterns = [
    path("phone-numbers", PhoneNumberViewSet.as_view({"get": "list", "post": "create"})),
    path(
        "phone-numbers/<int:pk>",
        PhoneNumberViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
]