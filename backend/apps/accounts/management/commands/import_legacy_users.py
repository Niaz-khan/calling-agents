"""Import legacy FastAPI users into the Django tenant model.

Reads the legacy SQLAlchemy-owned ``users`` table (still in PostgreSQL) and
materializes the migration decision:

* every user moves into ONE organization (single tenant for the MVP);
* ``admin@example.com`` becomes OWNER, everyone else STAFF;
* argon2id password hashes are preserved via Django's ``argon2$`` prefix
  (stripping the leading ``$`` the pwdlib format carries);
* any non-argon2 value is treated as a dev plaintext password and hashed.

Idempotent: existing emails are skipped and only missing memberships are
created. The legacy table is read-only and never modified.
"""

import os

import psycopg
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.tenancy.models import Organization, OrganizationMember


def _legacy_users():
    url = os.environ["DATABASE_URL"].replace("+psycopg://", "://", 1)
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, full_name, hashed_password, created_at FROM users ORDER BY id"
            )
            return cur.fetchall()


class Command(BaseCommand):
    help = "Import legacy FastAPI users into the Django tenant model (one org)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org", default="Default Organization", help="Organization name"
        )

    def handle(self, *args, **opts):
        org_name = opts["org"]
        created = updated = 0
        with transaction.atomic():
            org, _ = Organization.objects.get_or_create(name=org_name)
            for _, email, full_name, hashed_password, _ in _legacy_users():
                email = (email or "").strip().lower()
                user, was_created = User.objects.get_or_create(
                    email=email, defaults={"full_name": full_name or ""}
                )
                if not user.password:
                    if hashed_password.startswith("$argon"):
                        user.password = f"argon2${hashed_password[1:]}"
                    elif hashed_password:
                        user.set_password(hashed_password)
                    user.is_active = True
                    user.save(update_fields=["password", "is_active"])
                elif user.full_name != full_name and full_name:
                    user.full_name = full_name
                    user.save(update_fields=["full_name"])
                if user.default_organization_id != org.id:
                    user.default_organization = org
                    user.save(update_fields=["default_organization"])
                role = (
                    OrganizationMember.Role.OWNER
                    if email == "admin@example.com"
                    else OrganizationMember.Role.STAFF
                )
                OrganizationMember.objects.get_or_create(
                    organization=org, user=user, defaults={"role": role}
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Import done: {created} users created, {updated} existing, "
                f"organization={org.id!r} ({org.name!r}), members={org.members.count()}"
            )
        )