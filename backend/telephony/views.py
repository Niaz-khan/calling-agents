from tenancy.drf import OrganizationModelViewSet

from .models import PhoneNumber
from .serializers import PhoneNumberSerializer


class PhoneNumberViewSet(OrganizationModelViewSet):
    queryset = PhoneNumber.objects.all()
    serializer_class = PhoneNumberSerializer
    not_found_detail = "Phone number not found"