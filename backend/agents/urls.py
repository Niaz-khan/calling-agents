from django.urls import path

from .public import PublicChatView, widget_config, widget_demo, widget_js
from .views import AgentViewSet, DeploymentViewSet

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
    path(
        "deployments",
        DeploymentViewSet.as_view({"get": "list", "post": "create"}),
    ),
    path(
        "deployments/<int:pk>",
        DeploymentViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path("public/chat/<str:identifier>", PublicChatView.as_view()),
    path("public/config/<str:identifier>", widget_config),
    path("widget.js", widget_js),
    path("widget", widget_demo),
]