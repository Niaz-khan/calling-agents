"""Deployment readiness check.

Runs a battery of safe, read-only checks that a production deployment must
pass before serving traffic:

- Django configuration sanity (DEBUG/env/secret key)
- required environment variables
- database reachability + pending migrations
- static files configuration (collectstatic dry-run)
- production security posture

Exits non-zero when any critical check fails. Reports never print secrets.
"""

import sys

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Verify the deployment is configured safely and ready to serve traffic."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Treat warnings as failures (default for production).",
        )

    def handle(self, *args, **options):
        strict = options["strict"] or settings.ENVIRONMENT == "production"
        failures = self.run_checks(strict)
        if failures:
            self.stdout.write(
                self.style.ERROR(f"\nDeployment check FAILED: {failures} critical issue(s).")
            )
            sys.exit(1)
        self.stdout.write(
            self.style.SUCCESS("\nDeployment check passed. Ready to serve traffic.")
        )

    def run_checks(self, strict):
        failures = 0

        def report(passed, label, detail=""):
            if passed:
                line = f"[ok] {label}"
                style = self.style.SUCCESS
                adds = 0
            elif strict:
                line = f"[FAIL] {label}"
                style = self.style.ERROR
                adds = 1
            else:
                line = f"[WARN] {label}"
                style = self.style.WARNING
                adds = 0
            if detail:
                line += f" — {detail}"
            self.stdout.write(style(line))
            return adds

        # Configuration sanity
        debug_label = "DJANGO_DEBUG is off (correct)" if not settings.DEBUG else "DJANGO_DEBUG is on"
        failures += report(not settings.DEBUG, debug_label, "must be 0 in production")
        failures += report(
            settings.SECRET_KEY != "insecure-dev-key",
            "DJANGO_SECRET_KEY is not the development default",
        )
        failures += report(
            bool(settings.ALLOWED_HOSTS) and "*" not in settings.ALLOWED_HOSTS,
            "ALLOWED_HOSTS is configured without wildcards",
        )
        failures += report(
            bool(settings.CSRF_TRUSTED_ORIGINS) or not settings.ALLOWED_HOSTS,
            "CSRF trusted origins are configured",
        )
        failures += report(
            settings.SECURE_CONTENT_TYPE_NOSNIFF is True and settings.X_FRAME_OPTIONS,
            "Content-Type nosniff + X-Frame-Options are enabled",
        )

        # Required environment
        failures += report(
            bool(settings.DATABASES.get("default")),
            "DATABASE_URL is resolved",
        )
        if settings.REDIS_URL:
            report(True, "REDIS_URL is configured")
        else:
            failures += report(
                settings.ENVIRONMENT != "production",
                "REDIS_URL is set",
                "optional in development; expected in production",
            )

        # Database reachability + migrations
        db_ok = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            db_ok = True
        except Exception as exc:
            db_ok = False
            failures += report(False, "Database connection", str(exc))
            return failures
        report(True, "Database connection", "SELECT 1 ok")

        migrations_ok = True
        try:
            executor = MigrationExecutor(connection)
            pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
            migrations_ok = not pending
        except Exception as exc:
            migrations_ok = False
            detail = f"could not inspect migrations ({exc})"
        failures += report(
            migrations_ok,
            "Schema is up to date",
            "all migrations applied" if migrations_ok else f"{len(pending)} pending",
        )

        # Static files (collectstatic dry-run, no writes)
        try:
            call_command(
                "collectstatic",
                "--dry-run",
                "--noinput",
                "--no-post-process",
                verbosity=0,
                interactive=False,
            )
            failures += report(True, "Static files resolve", "collectstatic dry-run passed")
        except Exception as exc:
            failures += report(False, "Static files resolve", str(exc))

        return failures