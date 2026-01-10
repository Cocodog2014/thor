import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Reset a user's password non-interactively using env vars."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=os.getenv("THOR_ADMIN_USERNAME") or os.getenv("ADMIN_USERNAME"),
            help="Username/email of the user to reset (or set THOR_ADMIN_USERNAME / ADMIN_USERNAME).",
        )

    def handle(self, *args, **options):
        username = options.get("username")
        new_password = os.getenv("THOR_ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")

        if not username:
            raise CommandError(
                "Missing username. Provide --username or set THOR_ADMIN_USERNAME/ADMIN_USERNAME."
            )
        if not new_password:
            raise CommandError(
                "Missing password. Set THOR_ADMIN_PASSWORD or ADMIN_PASSWORD in the container environment."
            )

        User = get_user_model()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Some custom user models use email as the login field.
            email_field = getattr(User, "EMAIL_FIELD", "email")
            try:
                user = User.objects.get(**{email_field: username})
            except Exception as exc:
                raise CommandError(f"User not found for '{username}'.") from exc

        user.set_password(new_password)
        user.is_active = True
        user.save(update_fields=["password", "is_active"])

        self.stdout.write(self.style.SUCCESS(f"Password reset for '{username}'."))
