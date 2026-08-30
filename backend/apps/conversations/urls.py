from django.urls import path

from .views import CallViewSet, OutboundCallView

urlpatterns = [
    path("calls", CallViewSet.as_view({"get": "list", "post": "create"})),
    path("calls/outbound", OutboundCallView.as_view()),
    path("calls/<int:pk>", CallViewSet.as_view({"get": "retrieve"})),
    path(
        "calls/<int:pk>/messages",
        CallViewSet.as_view({"get": "messages", "post": "messages"}),
    ),
    path("calls/<int:pk>/end", CallViewSet.as_view({"post": "end"})),
]