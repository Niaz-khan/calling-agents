"""DRF helpers shared by every org-scoped API resource."""

from django.http import Http404
from rest_framework.exceptions import APIException, NotFound
from rest_framework.viewsets import ModelViewSet

from .access import get_request_organization


class Conflict(APIException):
    """HTTP 409, mirroring the legacy ``409 Conflict`` contract details."""

    status_code = 409
    default_detail = "Conflict"
    default_code = "conflict"


class OrganizationScopedMixin:
    """Resolve the request organization and 404 outside the tenant boundary."""

    not_found_detail = "Resource not found"

    def get_organization(self):
        organization = get_request_organization(self.request)
        if organization is None:
            raise NotFound("Organization not found")
        return organization

    def get_queryset(self):
        return self.queryset.model.objects.filter(organization=self.get_organization())

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise NotFound(self.not_found_detail)

    def perform_create(self, serializer):
        serializer.save(organization=self.get_organization())


class OrganizationModelViewSet(OrganizationScopedMixin, ModelViewSet):
    """ModelViewSet constrained to the request organization, unpaginated."""

    pagination_class = None