from django.urls import path

from .views import PhoneNumberViewSet
from .webhooks import (
    TwilioGatherWebhookView,
    TwilioInboundWebhookView,
    TwilioStatusWebhookView,
)

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
    path("telephony/webhook/inbound", TwilioInboundWebhookView.as_view()),
    path("telephony/webhook/status", TwilioStatusWebhookView.as_view()),
    path("telephony/webhook/gather", TwilioGatherWebhookView.as_view()),
]