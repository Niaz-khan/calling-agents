from apps.tenancy.drf import OrganizationModelViewSet

from .models import Service
from .serializers import ServiceSerializer


class ServiceViewSet(OrganizationModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    not_found_detail = "Service not found"