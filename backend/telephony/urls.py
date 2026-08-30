from django.urls import path

from .views import PhoneNumberViewSet, TelephonyStatusView
from .webhooks import (
    TelnyxInboundWebhookView,
    TwilioGatherWebhookView,
    TwilioInboundWebhookView,
    TwilioOutboundWebhookView,
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
    path("telephony/status", TelephonyStatusView.as_view()),
    path("telephony/webhook/inbound", TwilioInboundWebhookView.as_view()),
    path("telephony/webhook/outbound", TwilioOutboundWebhookView.as_view()),
    path("telephony/webhook/status", TwilioStatusWebhookView.as_view()),
    path("telephony/webhook/gather", TwilioGatherWebhookView.as_view()),
    path("telephony/webhook/telnyx", TelnyxInboundWebhookView.as_view()),
]