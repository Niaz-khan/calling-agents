from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from ai.provider import LLMError
from conversations.models import (
    Conversation,
    ConversationChannel,
    ConversationStatus,
    PhoneCall,
    PhoneCallStatus,
)
from crm.models import Customer
from telephony.models import PhoneNumber
from telephony.services import ProviderCallError, place_outbound_call
from tenancy.access import get_request_organization
from tenancy.drf import OrganizationModelViewSet

from .call_intelligence import classify_call_outcome, finalize_call
from .serializers import (
    CallDetailSerializer,
    CallListSerializer,
    CallSerializer,
    MessageDetailSerializer,
)
from .services import run_agent_turn


class CallCreateSerializer(serializers.Serializer):
    caller_number = serializers.CharField(min_length=1, max_length=50)
    direction = serializers.ChoiceField(
        choices=["inbound", "outbound"], default="inbound"
    )


class MessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=1, max_length=5000)


class OutboundCallSerializer(serializers.Serializer):
    agent_id = serializers.IntegerField()
    from_number_id = serializers.IntegerField()
    to = serializers.CharField(min_length=1, max_length=50)


class OutboundCallView(APIView):
    """Place a real outbound phone call through the configured provider."""

    def post(self, request):
        organization = get_request_organization(request)
        if organization is None:
            raise NotFound("Organization not found")

        serializer = OutboundCallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        agent = Agent.objects.filter(
            id=data["agent_id"], organization=organization, is_active=True
        ).first()
        if agent is None:
            raise NotFound("Agent not found")

        from_number = PhoneNumber.objects.filter(
            id=data["from_number_id"], organization=organization, is_active=True
        ).first()
        if from_number is None:
            raise NotFound("Phone number not found")

        if not from_number.outbound_enabled:
            return Response(
                {"detail": "This phone number does not allow outbound calls"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            conversation = place_outbound_call(
                organization, agent, from_number, data["to"]
            )
        except ProviderCallError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY
            )

        return Response(
            CallDetailSerializer(conversation, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CallViewSet(OrganizationModelViewSet):
    queryset = Conversation.objects.all()
    not_found_detail = "Call not found"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(phone_call__isnull=False)
            .select_related("agent", "phone_call", "customer")
            .prefetch_related("messages")
        )

    def get_serializer_class(self):
        return CallListSerializer if self.action == "list" else CallDetailSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        agent_id = request.query_params.get("agent_id")
        if agent_id:
            queryset = queryset.filter(agent_id=agent_id)
        serializer = CallListSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(CallDetailSerializer(instance, context=self.get_serializer_context()).data)

    def create(self, request, *args, **kwargs):
        organization = self.get_organization()
        agent_id = request.query_params.get("agent_id")
        agent = (
            Agent.objects.filter(
                id=agent_id, organization=organization, is_active=True
            ).first()
            if agent_id
            else None
        )
        if agent is None:
            raise NotFound("Agent not found")

        serializer = CallCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        customer, _ = Customer.objects.get_or_create(
            organization=organization, phone_number=data["caller_number"]
        )

        conversation = Conversation.objects.create(
            organization=organization,
            agent=agent,
            customer=customer,
            channel=ConversationChannel.PHONE,
        )
        PhoneCall.objects.create(
            conversation=conversation,
            direction=data["direction"].upper(),
            caller_number=data["caller_number"],
            provider_status=PhoneCallStatus.IN_PROGRESS,
        )

        return Response(
            CallDetailSerializer(conversation, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["GET", "POST"])
    def messages(self, request, pk=None):
        conversation = self.get_object()

        if request.method == "POST":
            if conversation.status != ConversationStatus.OPEN:
                return Response(
                    {"detail": "Call is not active"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = MessageCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            try:
                result = run_agent_turn(
                    conversation, conversation.agent, serializer.validated_data["message"]
                )
            except LLMError:
                return Response(
                    {"detail": "AI service is currently unavailable"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return Response(
                {
                    "call_id": conversation.id,
                    "role": "assistant",
                    "message": result.response,
                }
            )

        return Response(
            MessageDetailSerializer(conversation.messages.all(), many=True).data
        )

    @action(detail=True, methods=["POST"])
    def end(self, request, pk=None):
        conversation = self.get_object()
        phone_call = conversation.phone_call
        conversation.close()
        try:
            finalize_call(conversation)
        except LLMError:
            if conversation.outcome is None:
                conversation.outcome = classify_call_outcome(conversation)
        conversation.save(update_fields=["status", "ended_at", "outcome"])
        if phone_call is not None and phone_call.provider_status not in (
            PhoneCallStatus.TRANSFERRED,
            PhoneCallStatus.COMPLETED,
            PhoneCallStatus.FAILED,
        ):
            phone_call.provider_status = PhoneCallStatus.COMPLETED
            phone_call.save(update_fields=["provider_status"])
        return Response(CallSerializer(conversation).data)