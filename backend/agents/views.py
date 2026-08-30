from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from ai.agent import run_agent
from ai.provider import LLMError
from tenancy.drf import OrganizationModelViewSet

from .models import Agent, AgentDeployment
from .serializers import (
    AgentDeploymentSerializer,
    AgentSerializer,
)


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


class DeploymentViewSet(OrganizationModelViewSet):
    queryset = AgentDeployment.objects.all()
    serializer_class = AgentDeploymentSerializer
    not_found_detail = "Deployment not found"

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        agent_id = request.query_params.get("agent_id")
        if agent_id:
            queryset = queryset.filter(agent_id=agent_id)
        return Response(AgentDeploymentSerializer(queryset, many=True).data)

    def _resolve_agent(self, organization, agent_id):
        return Agent.objects.filter(
            id=agent_id, organization=organization, is_active=True
        ).first()

    def perform_create(self, serializer):
        organization = self.get_organization()
        agent = self._resolve_agent(organization, serializer.validated_data["agent_id"])
        if agent is None:
            raise ValidationError({"agent_id": "Agent not found"})
        serializer.save(organization=organization, agent=agent)

    def perform_update(self, serializer):
        organization = self.get_organization()
        agent_id = serializer.validated_data.get("agent_id")
        if agent_id is not None and self._resolve_agent(organization, agent_id) is None:
            raise ValidationError({"agent_id": "Agent not found"})
        serializer.save()
