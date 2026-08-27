from django.urls import path

from .views import CustomerViewSet

urlpatterns = [
    path("customers", CustomerViewSet.as_view({"get": "list", "post": "create"})),
    path(
        "customers/<int:pk>",
        CustomerViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
]