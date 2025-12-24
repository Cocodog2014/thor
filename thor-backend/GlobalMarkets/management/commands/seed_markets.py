from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Deprecated: control-market seeding removed. Configure markets via admin."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            "Seed command removed: manage markets via admin; no control weights/flags remain."
        ))
