from django.urls import path

from .views import (
    OrganizationAgentsView,
    OrganizationAppointmentsView,
    OrganizationCallsView,
    OrganizationCustomersView,
    OrganizationDetailView,
    OrganizationDeploymentsView,
    OrganizationKnowledgeView,
    OrganizationPhoneNumbersView,
    OrganizationServicesView,
    OrganizationUsersView,
    OrganizationViewSet,
    PlatformAgentViewSet,
    PlatformAnalyticsView,
    PlatformAppointmentViewSet,
    PlatformCallViewSet,
    PlatformCustomerViewSet,
    PlatformDashboardView,
    PlatformDeploymentViewSet,
    PlatformKnowledgeViewSet,
    PlatformPhoneNumberViewSet,
    PlatformServiceViewSet,
    PlatformUserViewSet,
    UserPlatformRoleView,
)

urlpatterns = [
    path("platform/dashboard", PlatformDashboardView.as_view()),
    path("platform/analytics", PlatformAnalyticsView.as_view()),
    path(
        "platform/organizations",
        OrganizationViewSet.as_view({"get": "list", "post": "create"}),
    ),
    path(
        "platform/organizations/<int:pk>",
        OrganizationViewSet.as_view({"get": "retrieve", "patch": "partial_update"}),
    ),
    path(
        "platform/organizations/<int:organization_id>/detail",
        OrganizationDetailView.as_view(),
    ),
    path(
        "platform/organizations/<int:organization_id>/users",
        OrganizationUsersView.as_view(),
    ),
    path(
        "platform/organizations/<int:organization_id>/agents",
        OrganizationAgentsView.as_view(),
    ),
    path(
        "platform/organizations/<int:organization_id>/deployments",
        OrganizationDeploymentsView.as_view(),
    ),
    path(
        "platform/organizations/<int:organization_id>/calls",
        OrganizationCallsView.as_view(),
    ),
    path(
        "platform/organizations/<int:organization_id>/appointments",
        OrganizationAppointmentsView.as_view(),
    ),
    path(
        "platform/organizations/<int:organization_id>/customers",
        OrganizationCustomersView.as_view(),
    ),
    path(
        "platform/organizations/<int:organization_id>/phone-numbers",
        OrganizationPhoneNumbersView.as_view(),
    ),
    path(
        "platform/organizations/<int:organization_id>/knowledge",
        OrganizationKnowledgeView.as_view(),
    ),
    path(
        "platform/organizations/<int:organization_id>/services",
        OrganizationServicesView.as_view(),
    ),
    path("platform/users", PlatformUserViewSet.as_view({"get": "list"})),
    path(
        "platform/users/<int:pk>",
        PlatformUserViewSet.as_view({"get": "retrieve"}),
    ),
    path("platform/users/<int:user_id>/role", UserPlatformRoleView.as_view()),
    path("platform/agents", PlatformAgentViewSet.as_view({"get": "list"})),
    path(
        "platform/agents/<int:pk>",
        PlatformAgentViewSet.as_view({"get": "retrieve"}),
    ),
    path(
        "platform/deployments",
        PlatformDeploymentViewSet.as_view({"get": "list"}),
    ),
    path(
        "platform/deployments/<int:pk>",
        PlatformDeploymentViewSet.as_view({"get": "retrieve"}),
    ),
    path("platform/calls", PlatformCallViewSet.as_view({"get": "list"})),
    path(
        "platform/calls/<int:pk>",
        PlatformCallViewSet.as_view({"get": "retrieve"}),
    ),
    path("platform/customers", PlatformCustomerViewSet.as_view({"get": "list"})),
    path(
        "platform/customers/<int:pk>",
        PlatformCustomerViewSet.as_view({"get": "retrieve"}),
    ),
    path(
        "platform/appointments",
        PlatformAppointmentViewSet.as_view({"get": "list"}),
    ),
    path(
        "platform/appointments/<int:pk>",
        PlatformAppointmentViewSet.as_view({"get": "retrieve"}),
    ),
    path(
        "platform/phone-numbers",
        PlatformPhoneNumberViewSet.as_view({"get": "list"}),
    ),
    path(
        "platform/phone-numbers/<int:pk>",
        PlatformPhoneNumberViewSet.as_view({"get": "retrieve"}),
    ),
    path(
        "platform/knowledge",
        PlatformKnowledgeViewSet.as_view({"get": "list"}),
    ),
    path(
        "platform/knowledge/<int:pk>",
        PlatformKnowledgeViewSet.as_view({"get": "retrieve"}),
    ),
    path(
        "platform/services",
        PlatformServiceViewSet.as_view({"get": "list"}),
    ),
    path(
        "platform/services/<int:pk>",
        PlatformServiceViewSet.as_view({"get": "retrieve"}),
    ),
]