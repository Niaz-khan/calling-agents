import pytest

from apps.cms.models import FAQ, FeatureSection, LandingPage, SiteSettings

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Public read-only API
# ---------------------------------------------------------------------------


def test_public_site_config_returns_branding(api_client):
    resp = api_client.get("/public/site-config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["site_name"] == "AI Call Agent"
    assert data["primary_color"]
    assert "meta_title" in data
    assert "social_links" in data


def test_public_landing_page_returns_sections(api_client):
    resp = api_client.get("/public/landing-page")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hero_title"]
    assert "sections" in data
    keys = [section["key"] for section in data["sections"]]
    assert "hero" in keys
    assert "features" in keys
    assert keys == [s["key"] for s in data["sections"]]  # preserves order
    assert data["hero_primary_cta"]


def test_public_collections_only_return_enabled(platformadmin, api_client):
    _, client = platformadmin
    client.post("/platform/cms/faqs", {"question": "Secret question", "answer": "Secret", "enabled": False})
    client.post("/platform/cms/faqs", {"question": "Visible question", "answer": "Visible", "enabled": True})
    client.post("/platform/cms/publish")
    resp = api_client.get("/public/faqs")
    assert resp.status_code == 200
    questions = [faq["question"] for faq in resp.json()]
    assert "Visible question" in questions
    assert "Secret question" not in questions


def test_public_pricing_returns_enabled_plans(api_client):
    resp = api_client.get("/public/pricing")
    assert resp.status_code == 200
    plans = resp.json()
    assert plans
    assert all(plan["enabled"] for plan in plans)


def test_unpublished_landing_page_not_exposed(api_client):
    page = LandingPage.objects.load()
    page.is_published = False
    page.save()
    assert api_client.get("/public/landing-page").status_code == 404


def test_unpublished_site_config_not_exposed(api_client):
    settings = SiteSettings.objects.load()
    settings.is_published = False
    settings.save()
    assert api_client.get("/public/site-config").status_code == 404


def test_public_endpoints_have_no_write_actions(api_client):
    for url in ("/public/site-config", "/public/features", "/public/faqs"):
        assert api_client.post(url, {}).status_code == 405
        assert api_client.patch(url, {}).status_code == 405
        assert api_client.delete(url).status_code == 405


# ---------------------------------------------------------------------------
# CMS mutation authorization
# ---------------------------------------------------------------------------


def test_anonymous_cannot_mutate_cms(api_client):
    assert api_client.get("/platform/cms/features").status_code == 401
    assert api_client.post("/platform/cms/features", {}).status_code == 401


def test_business_user_cannot_access_cms_admin(tenant):
    _, org, client = tenant
    assert client.get("/platform/cms/features").status_code == 403
    assert client.post("/platform/cms/features", {}).status_code == 403
    assert client.put("/platform/cms/landing", {}).status_code == 403


def test_platform_admin_can_crud_ordered_content(platformadmin):
    _, client = platformadmin
    created = client.post(
        "/platform/cms/features",
        {"title": "New feature", "description": "desc", "icon": "phone", "order": 0},
    )
    assert created.status_code == 201
    feature_id = created.json()["id"]

    listed = client.get("/platform/cms/features")
    assert listed.status_code == 200
    assert any(item["id"] == feature_id for item in listed.json())

    patched = client.patch(
        f"/platform/cms/features/{feature_id}", {"title": "Renamed feature"}
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Renamed feature"

    assert (
        client.get(f"/platform/cms/features/{feature_id}").json()["title"]
        == "Renamed feature"
    )
    assert client.delete(f"/platform/cms/features/{feature_id}").status_code == 204


def test_content_admin_can_manage_cms(contentadmin):
    _, client = contentadmin
    created = client.post(
        "/platform/cms/faqs",
        {"question": "A new question?", "answer": "A new answer."},
    )
    assert created.status_code == 201
    assert client.delete(f"/platform/cms/faqs/{created.json()['id']}").status_code == 204


def test_content_admin_cannot_access_platform_resources(contentadmin):
    _, client = contentadmin
    assert client.get("/platform/dashboard").status_code == 403
    assert client.get("/platform/organizations").status_code == 403


def test_landing_page_update_and_publish(platformadmin):
    _, client = platformadmin
    updated = client.put("/platform/cms/landing", {"hero_title": "CMStest headline"})
    assert updated.status_code == 200
    assert updated.json()["hero_title"] == "CMStest headline"

    pub = client.post("/platform/cms/landing/publish", {"is_published": False})
    assert pub.status_code == 200
    assert pub.json()["is_published"] is False
    assert client.get("/public/landing-page").status_code == 404

    pub = client.post("/platform/cms/landing/publish", {"is_published": True})
    assert pub.status_code == 200
    assert client.get("/public/landing-page").status_code == 200


def test_site_settings_branding_requires_publish(platformadmin, api_client):
    _, client = platformadmin
    resp = client.put(
        "/platform/cms/site-settings",
        {"site_name": "Nova AI", "primary_color": "#112233"},
    )
    assert resp.status_code == 200
    assert resp.json()["site_name"] == "Nova AI"
    # Draft edit must not leak to the public site before publishing.
    assert api_client.get("/public/site-config").json()["site_name"] != "Nova AI"
    client.post("/platform/cms/publish")
    assert api_client.get("/public/site-config").json()["site_name"] == "Nova AI"
    assert api_client.get("/public/site-config").json()["primary_color"] == "#112233"


def test_feature_ordering_is_stable(platformadmin, api_client):
    _, client = platformadmin
    client.post("/platform/cms/features", {"title": "A", "order": 2})
    client.post("/platform/cms/features", {"title": "B", "order": 1})
    client.post("/platform/cms/publish")
    resp = api_client.get("/public/features").json()
    seen = [item["title"] for item in resp if item["title"] in ("A", "B")]
    assert seen == ["B", "A"]


def test_feature_section_markdown_plain_text_is_safe(platformadmin):
    """CMS fields are plain text — no HTML/script storage path is allowed."""
    _, client = platformadmin
    created = client.post(
        "/platform/cms/features",
        {"title": "<script>alert(1)</script>", "description": "b <i>bold</i>"},
    )
    # Django model CharField never evaluates markup; it round-trips as text and
    # the frontend renders it with React (escaping by default).
    assert created.status_code == 201
    data = created.json()
    assert data["title"] == "<script>alert(1)</script>"


# ---------------------------------------------------------------------------
# Draft / published separation
# ---------------------------------------------------------------------------


def test_draft_edits_are_invisible_publicly(platformadmin, api_client):
    _, client = platformadmin
    client.put("/platform/cms/landing", {"hero_title": "Draft headline"})
    client.put("/platform/cms/site-settings", {"site_name": "Draft brand"})
    assert client.get("/platform/cms/landing").json()["hero_title"] == "Draft headline"
    assert api_client.get("/public/landing-page").json()["hero_title"] != "Draft headline"
    assert api_client.get("/public/site-config").json()["site_name"] != "Draft brand"


def test_publish_promotes_draft(platformadmin, api_client):
    _, client = platformadmin
    client.put("/platform/cms/landing", {"hero_title": "Published headline"})
    resp = client.post("/platform/cms/publish")
    assert resp.status_code == 201
    body = resp.json()
    assert body["is_published"] is True
    assert body["version"] == 2
    assert "summary" in body
    assert api_client.get("/public/landing-page").json()["hero_title"] == "Published headline"
    assert api_client.get("/public/site-config").status_code == 200


def test_edits_after_publish_do_not_change_public(platformadmin, api_client):
    _, client = platformadmin
    client.put("/platform/cms/landing", {"hero_title": "First"})
    client.post("/platform/cms/publish")
    client.put("/platform/cms/landing", {"hero_title": "Second (draft only)"})
    assert api_client.get("/public/landing-page").json()["hero_title"] == "First"
    assert client.get("/platform/cms/landing").json()["hero_title"] == "Second (draft only)"


def test_api_section_roundtrips_and_publishes(platformadmin, api_client):
    _, client = platformadmin
    client.put(
        "/platform/cms/landing",
        {"api_section_title": "API title", "api_section_text": "API text body", "api_section_cta": "Try it"},
    )
    draft = client.get("/platform/cms/landing").json()
    assert draft["api_section_title"] == "API title"
    assert draft["api_section_text"] == "API text body"
    # Draft is not visible publicly until published.
    assert api_client.get("/public/landing-page").json().get("api_section_title") != "API title"
    client.post("/platform/cms/publish")
    public = api_client.get("/public/landing-page").json()
    assert public["api_section_title"] == "API title"
    assert public["api_section_text"] == "API text body"
    assert public["api_section_cta"] == "Try it"


def test_public_sections_include_api_channel(api_client):
    resp = api_client.get("/public/landing-page")
    assert resp.status_code == 200
    keys = [s["key"] for s in resp.json()["sections"]]
    assert "api" in keys
    assert "phone" in keys
    assert "use_cases" in keys


def test_collection_drafts_are_invisible_until_publish(platformadmin, api_client):
    _, client = platformadmin
    client.post("/platform/cms/features", {"title": "Secret feature", "order": 9})
    assert all(row["title"] != "Secret feature" for row in api_client.get("/public/features").json())
    client.post("/platform/cms/publish")
    assert any(row["title"] == "Secret feature" for row in api_client.get("/public/features").json())


def test_unpublish_hides_public_site(platformadmin, api_client):
    _, client = platformadmin
    assert api_client.get("/public/landing-page").status_code == 200
    resp = client.post("/platform/cms/unpublish")
    assert resp.status_code == 200
    assert resp.json()["is_published"] is False
    assert api_client.get("/public/landing-page").status_code == 404
    assert api_client.get("/public/site-config").status_code == 404
    assert client.get("/platform/cms/landing").json()["is_published"] is False


def test_old_publish_endpoint_backward_compatible(platformadmin, api_client):
    _, client = platformadmin
    resp = client.post("/platform/cms/landing/publish", {"is_published": False})
    assert resp.status_code == 200
    assert resp.json()["is_published"] is False
    assert api_client.get("/public/landing-page").status_code == 404
    resp = client.post("/platform/cms/landing/publish", {"is_published": True})
    assert resp.status_code == 200
    assert resp.json()["is_published"] is True
    assert api_client.get("/public/landing-page").status_code == 200


# ---------------------------------------------------------------------------
# Publishing permissions
# ---------------------------------------------------------------------------


def test_publish_requires_platform_admin(platformadmin, contentadmin, tenant, api_client):
    _, plat = platformadmin
    _, content = contentadmin
    _, _, business = tenant
    assert plat.post("/platform/cms/publish").status_code == 201
    assert content.post("/platform/cms/publish").status_code == 403
    assert content.post("/platform/cms/unpublish").status_code == 403
    assert business.post("/platform/cms/publish").status_code == 403
    assert business.post("/platform/cms/restore/1").status_code == 403
    assert api_client.post("/platform/cms/publish").status_code == 401
    assert api_client.post("/platform/cms/unpublish").status_code == 401


def test_publish_preview_summarizes_changes(platformadmin):
    _, client = platformadmin
    client.put("/platform/cms/landing", {"hero_title": "Preview me"})
    client.post("/platform/cms/features", {"title": "X", "order": 1})
    resp = client.get("/platform/cms/publish/preview")
    assert resp.status_code == 200
    lines = resp.json()["summary"]
    assert "Hero changed" in lines
    assert any("feature" in line for line in lines)


def test_publish_preview_requires_platform_admin(contentadmin):
    _, client = contentadmin
    assert client.get("/platform/cms/publish/preview").status_code == 403


def test_superadmin_can_publish_and_restore(superadmin):
    _, client = superadmin
    resp = client.post("/platform/cms/publish")
    assert resp.status_code == 201
    resp = client.post("/platform/cms/unpublish")
    assert resp.status_code == 200
    assert client.post("/platform/cms/restore/1").status_code == 200


# ---------------------------------------------------------------------------
# Version history
# ---------------------------------------------------------------------------


def test_versions_are_created_and_numbered(platformadmin):
    _, client = platformadmin
    client.post("/platform/cms/publish")
    client.post("/platform/cms/publish")
    resp = client.get("/platform/cms/versions").json()
    assert [v["number"] for v in resp] == [3, 2, 1]
    assert [v["is_current"] for v in resp] == [True, False, False]
    assert resp[0]["published_by"] == "plat@example.com"
    assert resp[0]["summary"]


def test_restore_creates_draft_not_republish(platformadmin, api_client):
    _, client = platformadmin
    baseline = api_client.get("/public/landing-page").json()["hero_title"]
    client.put("/platform/cms/landing", {"hero_title": "V2 headline"})
    client.post("/platform/cms/publish")
    assert api_client.get("/public/landing-page").json()["hero_title"] == "V2 headline"

    client.put("/platform/cms/landing", {"hero_title": "Latest draft"})
    assert client.get("/platform/cms/landing").json()["hero_title"] == "Latest draft"

    resp = client.post("/platform/cms/restore/1")
    assert resp.status_code == 200
    assert resp.json()["restored"] is True
    # Draft now reflects the restored version…
    assert client.get("/platform/cms/landing").json()["hero_title"] == baseline
    # …but the public site still shows the last published version.
    assert api_client.get("/public/landing-page").json()["hero_title"] == "V2 headline"


def test_restore_requires_platform_admin(contentadmin):
    _, client = contentadmin
    assert client.post("/platform/cms/restore/1").status_code == 403
    assert client.get("/platform/cms/versions").status_code == 200


# ---------------------------------------------------------------------------
# Activity feed
# ---------------------------------------------------------------------------


def test_activity_logs_cms_actions(platformadmin, contentadmin):
    _, plat = platformadmin
    _, content = contentadmin
    content.put("/platform/cms/landing", {"hero_title": "Content edit"})
    plat.put("/platform/cms/site-settings", {"site_name": "Brand edit"})
    plat.post("/platform/cms/features", {"title": "F", "order": 1})
    plat.post("/platform/cms/publish")
    plat.post("/platform/cms/unpublish")
    plat.post("/platform/cms/restore/1")

    acts = plat.get("/platform/cms/activity").json()
    actions = [a["action"] for a in acts]
    assert "Published" in actions
    assert "Unpublished" in actions
    assert "Draft saved" in actions
    assert "Created" in actions
    assert "Version restored" in actions
    actors = {a["actor"] for a in acts if a["actor"]}
    assert "plat@example.com" in actors
    assert "content@example.com" in actors