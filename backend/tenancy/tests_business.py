from datetime import datetime, timezone

import pytest

from tenancy.models import Organization

from .services import is_business_open, normalize_business_hours, open_ranges

pytestmark = pytest.mark.django_db


class TestBusinessConfigAPI:
    def test_business_config_requires_auth(self, api_client):
        assert api_client.get("/business-config").status_code == 401
        assert api_client.patch("/business-config", {}).status_code == 401

    def test_get_returns_defaults(self, tenant):
        _, org, client = tenant
        data = client.get("/business-config").json()
        assert data["organization_id"] == org.id
        assert data["name"] == "Acme"
        assert data["business_name"] is None
        assert data["timezone"] == "UTC"
        assert data["business_hours"] == {}
        assert data["website_url"] is None

    def test_patch_updates_business_config(self, tenant):
        _, org, client = tenant
        response = client.patch(
            "/business-config",
            {
                "business_name": "Acme Dental",
                "timezone": "Asia/Karachi",
                "business_hours": {
                    "1": {"start": "09:00", "end": "17:00"},
                    "6": {"start": "09:00", "end": "13:00"},
                },
                "contact_phone": "+15551234567",
                "website_url": "https://acme.example.com",
            },
        )
        assert response.status_code == 200
        org.refresh_from_db()
        assert org.business_name == "Acme Dental"
        assert org.timezone == "Asia/Karachi"
        assert org.business_hours["1"] == {"start": "09:00", "end": "17:00"}
        assert org.contact_phone == "+15551234567"
        assert org.website_url == "https://acme.example.com"

        data = response.json()
        assert data["business_name"] == "Acme Dental"
        assert data["timezone"] == "Asia/Karachi"
        assert data["business_hours"]["1"] == {"start": "09:00", "end": "17:00"}

    def test_business_config_is_org_scoped(self, tenant, stranger):
        _, _, client = tenant
        _, _, other = stranger
        client.patch(
            "/business-config", {"business_name": "Acme Inc"}
        )
        mine = client.get("/business-config").json()
        theirs = other.get("/business-config").json()
        assert mine["business_name"] == "Acme Inc"
        assert theirs["name"] == "Rival"
        assert theirs["business_name"] is None

    def test_invalid_timezone_rejected(self, tenant):
        _, _, client = tenant
        assert (
            client.patch("/business-config", {"timezone": "Nowhere/Zone"}).status_code
            == 400
        )

    def test_invalid_business_hours_rejected(self, tenant):
        _, _, client = tenant
        assert (
            client.patch(
                "/business-config",
                {"business_hours": {"0": {"start": "09:00", "end": "17:00"}}},
            ).status_code
            == 400
        )
        assert (
            client.patch(
                "/business-config",
                {"business_hours": {"1": {"start": "9am", "end": "17:00"}}},
            ).status_code
            == 400
        )


class TestBusinessHours:
    def test_empty_hours_always_open(self):
        org = Organization(name="X", is_active=True, timezone="UTC", business_hours={})
        assert (
            is_business_open(org, reference_dt=datetime(2026, 3, 2, 23, 0, tzinfo=timezone.utc))
            is True
        )
        assert (
            is_business_open(org, reference_dt=datetime(2026, 3, 2, 1, 0, tzinfo=timezone.utc))
            is True
        )

    def test_open_during_hours(self):
        org = Organization(
            name="X",
            is_active=True,
            timezone="UTC",
            business_hours={"1": {"start": "09:00", "end": "17:00"}},
        )
        assert (
            is_business_open(org, reference_dt=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc))
            is True
        )
        assert (
            is_business_open(org, reference_dt=datetime(2026, 3, 2, 18, 0, tzinfo=timezone.utc))
            is False
        )

    def test_closed_day_closed(self):
        org = Organization(
            name="X",
            is_active=True,
            timezone="UTC",
            business_hours={"1": {"start": "09:00", "end": "17:00"}},
        )
        # 2026-03-01 is a Sunday (closed)
        assert (
            is_business_open(org, reference_dt=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc))
            is False
        )
        # Monday is open
        assert (
            is_business_open(org, reference_dt=datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc))
            is True
        )

    def test_timezone_interpretation(self):
        # Asia/Karachi is fixed UTC+5. 09:00 Karachi == 04:00 UTC.
        org = Organization(
            name="X",
            is_active=True,
            timezone="Asia/Karachi",
            business_hours={"1": {"start": "09:00", "end": "17:00"}},
        )
        assert (
            is_business_open(org, reference_dt=datetime(2026, 3, 2, 4, 0, tzinfo=timezone.utc))
            is True
        )
        assert (
            is_business_open(org, reference_dt=datetime(2026, 3, 2, 3, 0, tzinfo=timezone.utc))
            is False
        )

    def test_boundaries_inclusive_start_exclusive_end(self):
        org = Organization(
            name="X",
            is_active=True,
            timezone="UTC",
            business_hours={"1": {"start": "09:00", "end": "17:00"}},
        )
        assert (
            is_business_open(org, reference_dt=datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc))
            is True
        )
        assert (
            is_business_open(org, reference_dt=datetime(2026, 3, 2, 17, 0, tzinfo=timezone.utc))
            is False
        )

    def test_inactive_org_closed(self):
        org = Organization(
            name="X", is_active=False, timezone="UTC", business_hours={}
        )
        assert (
            is_business_open(org, reference_dt=datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc))
            is False
        )

    def test_normalize_business_hours(self):
        cleaned = normalize_business_hours(
            {"1": {"start": "09:00", "end": "17:00"}, "7": {"start": "", "end": ""}}
        )
        assert cleaned == {"1": {"start": "09:00", "end": "17:00"}}
        assert normalize_business_hours(None) == {}
        assert normalize_business_hours({}) == {}
        with pytest.raises(ValueError):
            normalize_business_hours({"8": {"start": "09:00", "end": "17:00"}})
        with pytest.raises(ValueError):
            normalize_business_hours({"1": {"start": "09:00"}})

    def test_open_ranges_present_all_days(self):
        org = Organization(
            name="X",
            timezone="UTC",
            business_hours={"1": {"start": "09:00", "end": "17:00"}},
        )
        rows = open_ranges(org)
        assert len(rows) == 7
        by_iso = {row["iso"]: row for row in rows}
        assert by_iso[1]["start"] == "09:00"
        assert by_iso[1]["closed"] is False
        assert by_iso[2]["closed"] is True
        assert by_iso[7]["label"] == "sunday"