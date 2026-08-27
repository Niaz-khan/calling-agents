from datetime import datetime

from django.utils import timezone as dj_timezone

from tenancy.drf import OrganizationModelViewSet

from .models import Appointment
from .serializers import AppointmentSerializer


def _parse_bound(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dj_timezone.utc)
    return parsed


class AppointmentViewSet(OrganizationModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    not_found_detail = "Appointment not found"

    def get_queryset(self):
        queryset = super().get_queryset().order_by("start_time")
        params = self.request.query_params
        agent_id = params.get("agent_id")
        status_filter = params.get("status_filter")
        date_from = _parse_bound(params.get("date_from"))
        date_to = _parse_bound(params.get("date_to"))
        if agent_id:
            queryset = queryset.filter(agent_id=agent_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        if date_from is not None:
            queryset = queryset.filter(start_time__gte=date_from)
        if date_to is not None:
            queryset = queryset.filter(start_time__lte=date_to)
        return queryset