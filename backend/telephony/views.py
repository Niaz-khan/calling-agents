from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.access import get_request_organization
from tenancy.drf import OrganizationModelViewSet

from .models import PhoneNumber
from .serializers import PhoneNumberSerializer
from .services import telephony_connection_status


class PhoneNumberViewSet(OrganizationModelViewSet):
    queryset = PhoneNumber.objects.all()
    serializer_class = PhoneNumberSerializer
    not_found_detail = "Phone number not found"


class TelephonyStatusView(APIView):
    """Report whether the configured telephony provider is usable."""

    def get(self, request):
        organization = get_request_organization(request)
        if organization is None:
            raise NotFound("Organization not found")
        return Response(telephony_connection_status())