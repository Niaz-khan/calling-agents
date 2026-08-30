from tenancy.drf import OrganizationModelViewSet

from .models import Agent
from .serializers import AgentSerializer


class AgentViewSet(OrganizationModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    not_found_detail = "Agent not found"