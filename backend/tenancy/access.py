from .models import Organization


def visible_organizations(user):
    """Organizations the user is an active member of."""
    return Organization.objects.filter(is_active=True, members__user=user)


def visible_organization_ids(user) -> set[int]:
    return set(visible_organizations(user).values_list("id", flat=True))


def resolve_organization(user, organization_id=None):
    """Resolve the organization a request operates on.

    Honors an explicit organization id (returns ``None`` when the user is not
    a member — the cross-tenant 404 boundary), then the user's default
    organization, then the first membership.
    """
    qs = visible_organizations(user)
    if organization_id is not None:
        return qs.filter(id=organization_id).first()
    if user.default_organization_id:
        default = qs.filter(id=user.default_organization_id).first()
        if default:
            return default
    return qs.first()


def get_request_organization(request):
    """Resolve the organization for a request, honoring ``X-Organization-ID``."""
    organization_id = request.META.get("HTTP_X_ORGANIZATION_ID")
    if organization_id is not None:
        try:
            organization_id = int(organization_id)
        except (TypeError, ValueError):
            return None
    return resolve_organization(request.user, organization_id)