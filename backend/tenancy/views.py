from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.access import get_request_organization

from .serializers import BusinessConfigSerializer


class BusinessConfigView(APIView):
    """GET/PATCH the authenticated organization's business configuration."""

    def get_object(self):
        organization = get_request_organization(self.request)
        if organization is None:
            return Response({"detail": "Organization not found"}, status=404)
        return organization

    def get(self, request):
        organization = self.get_object()
        return Response(BusinessConfigSerializer(organization).data)

    def patch(self, request):
        organization = self.get_object()
        serializer = BusinessConfigSerializer(
            organization, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
