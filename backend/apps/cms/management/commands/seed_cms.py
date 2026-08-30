from django.core.management.base import BaseCommand

from apps.cms.seed import seed


class Command(BaseCommand):
    help = "Seed default CMS content (idempotent; existing rows are preserved)"

    def handle(self, *args, **options):
        seed()
        self.stdout.write(self.style.SUCCESS("CMS content seeded."))