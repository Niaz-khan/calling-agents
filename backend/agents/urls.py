from django.urls import path

from .views import AgentViewSet

urlpatterns = [
    path("agents", AgentViewSet.as_view({"get": "list", "post": "create"})),
    path(
        "agents/<int:pk>",
        AgentViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path("agents/<int:pk>/chat", AgentViewSet.as_view({"post": "chat"})),
]