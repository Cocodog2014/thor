"""
Management command to clean up fake consumer apps and show the new dropdown system.
"""

from django.core.management.base import BaseCommand
from SchwabLiveData.models import ConsumerApp
from SchwabLiveData.thor_apps import get_available_apps, is_valid_app


class Command(BaseCommand):
    help = 'Clean up fake consumer apps and show valid Thor applications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Remove invalid apps (like the fake "best" app)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Actually perform cleanup (not just dry run)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Thor Consumer App Validation (Dropdown Approach)')
        )
        self.stdout.write('')
        
        # Show available Thor apps
        self.show_valid_apps()
        
        # Check current consumer apps
        self.audit_current_apps()
        
        if options['cleanup']:
            self.cleanup_fake_apps(force=options['force'])

    def show_valid_apps(self):
        """Show the valid Thor applications available in the dropdown."""
        self.stdout.write("✅ Valid Thor Applications (available in dropdown):")
        
        available_apps = get_available_apps()
        for code, display_name in available_apps:
            self.stdout.write(f"  📱 {code} - {display_name}")
        
        self.stdout.write('')

    def audit_current_apps(self):
        """Audit currently registered consumer apps."""
        self.stdout.write("📊 Currently Registered Consumer Apps:")
        
        all_apps = ConsumerApp.objects.all()
        
        if not all_apps.exists():
            self.stdout.write("  (No consumer apps registered yet)")
            return
        
        valid_count = 0
        invalid_count = 0
        
        for app in all_apps:
            is_valid = is_valid_app(app.code)
            
            if is_valid:
                self.stdout.write(
                    self.style.SUCCESS(f"  ✅ {app.code} - {app.display_name} (VALID)")
                )
                valid_count += 1
            else:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ {app.code} - {app.display_name} (FAKE/INVALID)")
                )
                invalid_count += 1
                
                # Show feed assignments for fake apps
                assignments = app.assignments.all()
                if assignments:
                    self.stdout.write(f"     ⚠️  Has {assignments.count()} feed assignments!")
        
        self.stdout.write('')
        self.stdout.write(f"Summary: {valid_count} valid, {invalid_count} fake/invalid apps")
        
        if invalid_count > 0:
            self.stdout.write('')
            self.stdout.write("Run with --cleanup to remove fake apps")

    def cleanup_fake_apps(self, force=False):
        """Clean up fake consumer apps."""
        self.stdout.write("🧹 Cleaning up fake/invalid consumer apps...")
        
        fake_apps = ConsumerApp.objects.all()
        removed_count = 0
        
        for app in fake_apps:
            if not is_valid_app(app.code):
                action = f"Would remove fake app: {app.code}"
                
                if force:
                    # Remove feed assignments first
                    assignments_count = app.assignments.count()
                    app.assignments.all().delete()
                    
                    # Remove the app
                    app.delete()
                    action = f"✅ Removed fake app: {app.code} (and {assignments_count} assignments)"
                    removed_count += 1
                
                self.stdout.write(action)
        
        if not force and removed_count == 0:
            fake_count = sum(1 for app in ConsumerApp.objects.all() if not is_valid_app(app.code))
            if fake_count > 0:
                self.stdout.write('')
                self.stdout.write("To actually remove fake apps, run with --cleanup --force")
        elif force:
            self.stdout.write('')
            self.stdout.write(f"✅ Cleanup complete! Removed {removed_count} fake apps")
            self.stdout.write("Now only valid Thor applications can be registered through the admin dropdown.")