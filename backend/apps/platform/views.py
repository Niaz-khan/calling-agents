"""Platform-admin API: cross-organization management + analytics.

Every view is gated by a platform role permission (see ``permissions.py``).
Business users are never granted these routes: their org-scoped viewsets keep
enforcing tenant isolation on the normal app APIs.
"""

from django.db.models import Count, OuterRef, Q, Subquery
from django.http import Http404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.models import User
from apps.agents.models import Agent, AgentDeployment
from apps.appointments.models import Appointment
from apps.conversations.models import Conversation
from apps.crm.models import Customer
from apps.knowledge.models import KnowledgeBase
from apps.services.models import Service
from apps.telephony.models import PhoneNumber
from apps.tenancy.models import Organization

from .permissions import IsPlatformAdmin, IsSuperAdmin
from .serializers import (
    PlatformAgentSerializer,
    PlatformAppointmentSerializer,
    PlatformCallSerializer,
    PlatformCustomerSerializer,
    PlatformDeploymentSerializer,
    PlatformKnowledgeSerializer,
    PlatformOrganizationSerializer,
    PlatformPhoneNumberSerializer,
    PlatformRoleChangeSerializer,
    PlatformServiceSerializer,
    PlatformUserSerializer,
)
from .services import (
    dashboard_metrics,
    organization_summary,
    platform_analytics,
    recent_activity,
)

ADMIN = [IsPlatformAdmin]
NOT_FOUND = "Resource not found"


def _not_found():
    raise NotFound(NOT_FOUND)


def _search(qs, fields, q):
    if not q:
        return qs
    query = Q()
    for field in fields:
        query |= Q(**{f"{field}__icontains": q})
    if not query:
        return qs
    return qs.filter(query)


class PlatformDashboardView(APIView):
    permission_classes = ADMIN

    def get(self, request):
        data = dashboard_metrics()
        data["recent_activity"] = recent_activity()
        return Response(data)


def _phone_call_counts():
    return (
        Conversation.objects.filter(organization=OuterRef("pk"), phone_call__isnull=False)
        .order_by()
        .values("organization_id")
        .annotate(n=Count("id"))
        .values("n")
    )


class OrganizationViewSet(ModelViewSet):
    """Platform CRUD for organizations. No delete -- only activate/deactivate."""

    permission_classes = ADMIN
    serializer_class = PlatformOrganizationSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Organization.objects.annotate(
            members_count=Count("members", distinct=True),
            agents_count=Count("agents", distinct=True),
            deployments_count=Count("deployments", distinct=True),
            phone_numbers_count=Count("phone_numbers", distinct=True),
            customers_count=Count("customers", distinct=True),
            appointments_count=Count("appointments", distinct=True),
            knowledge_bases_count=Count("knowledge_bases", distinct=True),
            calls_count=Subquery(_phone_call_counts()),
        )
        q = self.request.query_params.get("q")
        if q:
            qs = _search(qs, ["name", "business_name"], q)
        return qs


class OrganizationDetailView(APIView):
    permission_classes = ADMIN

    def get(self, request, organization_id):
        org = Organization.objects.filter(id=organization_id).first()
        if org is None:
            _not_found()
        return Response(
            {
                "organization": PlatformOrganizationSerializer(org).data,
                "summary": organization_summary(org),
            }
        )


class _OrganizationResourceView(APIView):
    permission_classes = ADMIN
    serializer_class = None
    queryset = None
    order_by = "-created_at"

    def get(self, request, organization_id):
        if not Organization.objects.filter(id=organization_id).exists():
            _not_found()
        rows = self.queryset.filter(organization_id=organization_id).order_by(self.order_by)
        return Response(self.serializer_class(rows, many=True).data)


class OrganizationUsersView(_OrganizationResourceView):
    serializer_class = PlatformUserSerializer
    queryset = User.objects.all()

    def get(self, request, organization_id):
        if not Organization.objects.filter(id=organization_id).exists():
            _not_found()
        members = User.objects.filter(memberships__organization_id=organization_id).distinct()
        return Response(PlatformUserSerializer(members, many=True).data)


class OrganizationAgentsView(_OrganizationResourceView):
    serializer_class = PlatformAgentSerializer
    queryset = Agent.objects.select_related("organization").annotate(
        deployments_count=Count("deployments", distinct=True),
        conversations_count=Count("conversations", distinct=True),
    )


class OrganizationDeploymentsView(_OrganizationResourceView):
    serializer_class = PlatformDeploymentSerializer
    queryset = AgentDeployment.objects.select_related("organization", "agent").annotate(
        conversations_count=Count("conversations", distinct=True)
    )


class OrganizationCallsView(_OrganizationResourceView):
    serializer_class = PlatformCallSerializer
    queryset = (
        Conversation.objects.filter(phone_call__isnull=False)
        .select_related("organization", "agent", "phone_call")
    )


class OrganizationAppointmentsView(_OrganizationResourceView):
    serializer_class = PlatformAppointmentSerializer
    queryset = Appointment.objects.select_related("organization", "agent", "service")


class OrganizationCustomersView(_OrganizationResourceView):
    serializer_class = PlatformCustomerSerializer
    queryset = Customer.objects.select_related("organization").annotate(
        conversations_count=Count("conversations", distinct=True)
    )


class OrganizationPhoneNumbersView(_OrganizationResourceView):
    serializer_class = PlatformPhoneNumberSerializer
    queryset = PhoneNumber.objects.select_related("organization", "agent")


class OrganizationKnowledgeView(_OrganizationResourceView):
    serializer_class = PlatformKnowledgeSerializer
    queryset = KnowledgeBase.objects.select_related("organization", "agent").annotate(
        documents_count=Count("documents", distinct=True)
    )


class OrganizationServicesView(_OrganizationResourceView):
    serializer_class = PlatformServiceSerializer
    queryset = Service.objects.select_related("organization")


class PlatformUserViewSet(ModelViewSet):
    permission_classes = ADMIN
    serializer_class = PlatformUserSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = User.objects.all().order_by("-date_joined")
        q = self.request.query_params.get("q")
        if q:
            qs = _search(qs, ["email", "full_name"], q)
        role = self.request.query_params.get("platform_role")
        if role:
            qs = qs.filter(platform_role=role)
        return qs


class UserPlatformRoleView(APIView):
    """Super-admin only: grant/revoke platform roles or activate/deactivate."""

    permission_classes = [IsSuperAdmin]

    def patch(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if user is None:
            _not_found()
        serializer = PlatformRoleChangeSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "platform_role" in data:
            user.set_platform_role(data["platform_role"])
        if "is_active" in data:
            user.is_active = data["is_active"]
            user.save(update_fields=["is_active"])
        return Response(PlatformUserSerializer(user).data)


class PlatformAgentViewSet(ModelViewSet):
    permission_classes = ADMIN
    serializer_class = PlatformAgentSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = Agent.objects.select_related("organization").annotate(
            deployments_count=Count("deployments", distinct=True),
            conversations_count=Count("conversations", distinct=True),
        )
        organization_id = self.request.query_params.get("organization_id")
        if organization_id:
            qs = qs.filter(organization_id=organization_id)
        is_active = self.request.query_params.get("is_active")
        if is_active in ("true", "false"):
            qs = qs.filter(is_active=is_active == "true")
        q = self.request.query_params.get("q")
        if q:
            qs = _search(qs, ["name"], q)
        return qs.order_by("-created_at")


class PlatformDeploymentViewSet(ModelViewSet):
    permission_classes = ADMIN
    serializer_class = PlatformDeploymentSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = AgentDeployment.objects.select_related("organization", "agent").annotate(
            conversations_count=Count("conversations", distinct=True)
        )
        organization_id = self.request.query_params.get("organization_id")
        if organization_id:
            qs = qs.filter(organization_id=organization_id)
        channel = self.request.query_params.get("channel")
        if channel:
            qs = qs.filter(channel=channel)
        enabled = self.request.query_params.get("enabled")
        if enabled in ("true", "false"):
            qs = qs.filter(enabled=enabled == "true")
        return qs.order_by("-created_at")


class PlatformCallViewSet(ModelViewSet):
    permission_classes = ADMIN
    serializer_class = PlatformCallSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = (
            Conversation.objects.filter(phone_call__isnull=False)
            .select_related("organization", "agent", "phone_call")
            .order_by("-started_at")
        )
        organization_id = self.request.query_params.get("organization_id")
        if organization_id:
            qs = qs.filter(organization_id=organization_id)
        channel = self.request.query_params.get("channel")
        if channel:
            qs = qs.filter(channel=channel)
        return qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = PlatformCallSerializer(instance, context={"include_transcript": True})
        return Response(serializer.data)


class PlatformCustomerViewSet(ModelViewSet):
    permission_classes = ADMIN
    serializer_class = PlatformCustomerSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = Customer.objects.select_related("organization").annotate(
            conversations_count=Count("conversations", distinct=True)
        )
        organization_id = self.request.query_params.get("organization_id")
        if organization_id:
            qs = qs.filter(organization_id=organization_id)
        q = self.request.query_params.get("q")
        if q:
            qs = _search(qs, ["name", "phone_number", "email"], q)
        return qs.order_by("-created_at")


class PlatformAppointmentViewSet(ModelViewSet):
    permission_classes = ADMIN
    serializer_class = PlatformAppointmentSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = Appointment.objects.select_related("organization", "agent", "service")
        organization_id = self.request.query_params.get("organization_id")
        if organization_id:
            qs = qs.filter(organization_id=organization_id)
        res = self.request.query_params.get("status")
        if res:
            qs = qs.filter(status=res)
        return qs.order_by("-start_time")


class PlatformPhoneNumberViewSet(ModelViewSet):
    permission_classes = ADMIN
    serializer_class = PlatformPhoneNumberSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = PhoneNumber.objects.select_related("organization", "agent")
        organization_id = self.request.query_params.get("organization_id")
        if organization_id:
            qs = qs.filter(organization_id=organization_id)
        is_active = self.request.query_params.get("is_active")
        if is_active in ("true", "false"):
            qs = qs.filter(is_active=is_active == "true")
        q = self.request.query_params.get("q")
        if q:
            qs = _search(qs, ["phone_number", "provider"], q)
        return qs.order_by("-created_at")


class PlatformKnowledgeViewSet(ModelViewSet):
    permission_classes = ADMIN
    serializer_class = PlatformKnowledgeSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = KnowledgeBase.objects.select_related("organization", "agent").annotate(
            documents_count=Count("documents", distinct=True)
        )
        organization_id = self.request.query_params.get("organization_id")
        if organization_id:
            qs = qs.filter(organization_id=organization_id)
        q = self.request.query_params.get("q")
        if q:
            qs = _search(qs, ["name"], q)
        return qs.order_by("-created_at")


class PlatformServiceViewSet(ModelViewSet):
    permission_classes = ADMIN
    serializer_class = PlatformServiceSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = Service.objects.select_related("organization")
        organization_id = self.request.query_params.get("organization_id")
        if organization_id:
            qs = qs.filter(organization_id=organization_id)
        active = self.request.query_params.get("active")
        if active in ("true", "false"):
            qs = qs.filter(active=active == "true")
        q = self.request.query_params.get("q")
        if q:
            qs = _search(qs, ["name"], q)
        return qs.order_by("-created_at")


class PlatformAnalyticsView(APIView):
    permission_classes = ADMIN

    def get(self, request):
        try:
            days = int(request.query_params.get("days", 30))
        except (TypeError, ValueError):
            days = 30
        days = max(7, min(days, 180))
        return Response(platform_analytics(days))