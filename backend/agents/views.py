from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ai.agent import run_agent
from ai.provider import LLMError
from tenancy.drf import OrganizationModelViewSet

from .models import Agent
from .serializers import AgentSerializer


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=1, max_length=5000)


class AgentViewSet(OrganizationModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    not_found_detail = "Agent not found"

    @action(detail=True, methods=["POST"], url_path="chat")
    def chat(self, request, pk=None):
        agent = self.get_object()
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = [
            {"role": "user", "content": serializer.validated_data["message"]}
        ]

        try:
            result = run_agent(
                system_prompt=agent.system_prompt,
                conversation=conversation,
                organization=self.get_organization(),
                agent_id=agent.id,
            )
        except LLMError:
            return Response(
                {"detail": "AI service is currently unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"agent_id": agent.id, "message": result.response})
