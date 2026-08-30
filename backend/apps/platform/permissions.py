"""Platform-admin permission classes.

Role hierarchy:
    SUPER_ADMIN      -- everything, including managing platform staff
    PLATFORM_ADMIN   -- organizations/users/agents/deployments/calls/customers/
                        appointments/analytics/platform settings
    SUPPORT_ADMIN    -- prepared for future back-office support work
    CONTENT_ADMIN    -- CMS/branding/SEO only

Django ``is_superuser`` always bypasses role checks, so the conventional
``createsuperuser`` bootstrap keeps full access without extra setup.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.models import User


def _has_role(user, roles):
    return bool(user and user.is_authenticated) and (
        user.is_superuser or user.platform_role in roles
    )


class IsPlatformUser(BasePermission):
    """Any platform role (or superuser) -- gates the /admin SPA itself."""

    message = "Platform administrator access required"

    def has_permission(self, request, view):
        return _has_role(request.user, User.PlatformRole.values)


class IsPlatformAdmin(BasePermission):
    """Owner/operator access: organizations, users, resources, analytics, settings."""

    message = "Platform administrator access required"

    def has_permission(self, request, view):
        return _has_role(request.user, [User.PlatformRole.SUPER_ADMIN, User.PlatformRole.PLATFORM_ADMIN])


class IsSuperAdmin(BasePermission):
    """Only for operations that govern the platform itself (e.g. promoting staff)."""

    message = "Super admin access required"

    def has_permission(self, request, view):
        return _has_role(request.user, [User.PlatformRole.SUPER_ADMIN])


class IsContentAdmin(BasePermission):
    """CMS/branding/SEO content editing (platform-level, never business users)."""

    message = "CMS administrator access required"

    def has_permission(self, request, view):
        return _has_role(
            request.user,
            [
                User.PlatformRole.SUPER_ADMIN,
                User.PlatformRole.PLATFORM_ADMIN,
                User.PlatformRole.CONTENT_ADMIN,
            ],
        )