"""Business-level helpers shared by analytics, public config and the dashboard.

Presence is intentionally NOT "the AI server is alive". A business is online
only when the organization is active AND the current moment falls inside its
configured weekly business hours (interpreted in the organization's own
timezone, never the server's local timezone).
"""

from datetime import datetime

from zoneinfo import ZoneInfo

# ISO weekday keys used by ``Organization.business_hours``: 1=Mon .. 7=Sun.
WEEKDAY_KEYS = {
    1: "monday",
    2: "tuesday",
    3: "wednesday",
    4: "thursday",
    5: "friday",
    6: "saturday",
    7: "sunday",
}
KEY_TO_ISO = {label: key for key, label in WEEKDAY_KEYS.items()}

DEFAULT_TIMEZONE = "UTC"


def organization_zone(organization):
    """Return the organization's ``ZoneInfo``, falling back to UTC."""
    try:
        return ZoneInfo(organization.timezone or DEFAULT_TIMEZONE)
    except Exception:
        return ZoneInfo(DEFAULT_TIMEZONE)


def is_business_open(organization, reference_dt=None):
    """Whether the moment (default: now in org timezone) falls in business hours.

    ``Organization.business_hours`` is keyed by ISO weekday (1..7), each value
    an object with ``start``/``end`` in ``%H:%M``. An empty schedule means the
    business is always open. Meaningful guidance for reference_dt: tests pass
    explicit datetimes to avoid timezone flakiness.
    """
    if organization is None or not organization.is_active:
        return False

    zone = organization_zone(organization)
    if reference_dt is None:
        moment = datetime.now(zone)
    elif reference_dt.tzinfo is None:
        moment = reference_dt.replace(tzinfo=zone)
    else:
        moment = reference_dt.astimezone(zone)

    hours = organization.business_hours or {}
    if not hours:
        return True

    entry = hours.get(str(moment.isoweekday()))
    if not entry:
        return False
    start = entry.get("start")
    end = entry.get("end")
    if not start or not end:
        return False
    current = moment.strftime("%H:%M")
    return start <= current < end


def open_ranges(organization):
    """Normalize ``business_hours`` into a displayable, constant list.

    Returns a list of ``{"iso": day_number, "label": day_name, "start", "end"}``
    for every day exactly as configured (missing days imply closed).
    """
    hours = organization.business_hours or {}
    rows = []
    for iso in range(1, 8):
        entry = hours.get(str(iso))
        rows.append(
            {
                "iso": iso,
                "label": WEEKDAY_KEYS[iso],
                "start": entry.get("start") if entry else None,
                "end": entry.get("end") if entry else None,
                "closed": not bool(entry and entry.get("start") and entry.get("end")),
            }
        )
    return rows


def normalize_business_hours(value):
    """Validate and normalize a submitted ``business_hours`` value.

    Accepts ``{iso_day: {"start": "HH:MM", "end": "HH:MM"}}`` for any subset of
    days 1..7 and returns a clean dict. Raises ``ValueError`` on malformed
    input so serializers can surface a predictable 400.
    """
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ValueError("business_hours must be a JSON object")

    def _validate_time(item):
        if not isinstance(item, str):
            raise ValueError("business hours must be strings like '09:00'")
        try:
            datetime.strptime(item, "%H:%M")
        except ValueError:
            raise ValueError("business hours must be 'HH:MM'")

    cleaned = {}
    for raw_key, entry in value.items():
        try:
            iso = int(raw_key)
        except (TypeError, ValueError):
            raise ValueError("business hours keys must be weekday numbers 1-7")
        if iso < 1 or iso > 7:
            raise ValueError("business hours keys must be weekday numbers 1-7")
        if not isinstance(entry, dict):
            raise ValueError("each business hours day must be an object")
        start = (entry.get("start") or "").strip()
        end = (entry.get("end") or "").strip()
        if not start and not end:
            continue
        _validate_time(start)
        _validate_time(end)
        cleaned[str(iso)] = {"start": start, "end": end}
    return cleaned


def validate_timezone(value):
    if not value:
        return DEFAULT_TIMEZONE
    try:
        ZoneInfo(value)
    except Exception:
        raise ValueError(f"Unknown timezone: {value}")
    return value