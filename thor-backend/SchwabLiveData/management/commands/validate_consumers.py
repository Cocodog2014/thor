"""
Management command to detect and handle fake consumer app registrations.
"""

from django.core.management.base import BaseCommand
from SchwabLiveData.models import ConsumerApp
from SchwabLiveData.simple_validation import audit_fake_apps, cleanup_fake_apps, test_app_connectivity


class Command(BaseCommand):
    help = 'Detect fake consumer apps and validate real ones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--consumer',
            type=str,
            help='Check specific consumer app by code',
        )
        parser.add_argument(
            '--audit',
            action='store_true',
            help='Audit all apps for fake registrations',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up fake apps (dry run by default)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Actually perform cleanup (not just dry run)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Thor Consumer App Security Check')
        )
        
        if options['consumer']:
            self.check_single_consumer(options['consumer'])
        elif options['audit']:
            self.audit_all_apps()
        elif options['cleanup']:
            self.cleanup_apps(force=options['force'])
        else:
            self.quick_audit()

    def check_single_consumer(self, consumer_code):
        """Check a specific consumer app."""
        self.stdout.write(f"🎯 Checking consumer: {consumer_code}")
        
        try:
            app = ConsumerApp.objects.get(code__iexact=consumer_code)
        except ConsumerApp.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"❌ Consumer '{consumer_code}' not found")
            )
            return

        self.stdout.write(f"📱 App: {app.display_name}")
        self.stdout.write(f"🔑 API Key: {app.api_key or 'None'}")
        self.stdout.write(f"✅ Validated: {app.is_validated}")
        self.stdout.write(f"🔗 Callback URL: {app.callback_url or 'None'}")
        self.stdout.write(f"🛡️  Capabilities: {app.authorized_capabilities}")
        self.stdout.write(f"⚠️  Failures: {app.validation_failures}")
        self.stdout.write(f"📊 Status: {app.security_status}")
        
        if app.callback_url:
            self.stdout.write("🔗 Testing connectivity...")
            if test_app_connectivity(app):
                self.stdout.write(self.style.SUCCESS("✅ Connectivity test passed"))
            else:
                self.stdout.write(self.style.ERROR("❌ Connectivity test failed"))

    def audit_all_apps(self):
        """Audit all consumer apps."""
        self.stdout.write("� Auditing all consumer apps...\n")
        
        results = audit_fake_apps()
        
        self.stdout.write(f"Total apps: {results['total_apps']}")
        self.stdout.write(f"Validated apps: {results['validated_apps']}")
        self.stdout.write(f"Fake apps: {results['fake_apps']}")
        self.stdout.write(f"Failed apps: {results['failed_apps']}")
        
        if results['fake_apps'] > 0:
            self.stdout.write("\n🚨 FAKE APPS DETECTED:")
            for fake_app in results['fake_app_list']:
                status_icon = "�" if fake_app['is_active'] else "⚫"
                feeds_info = "📡" if fake_app['has_feed_assignments'] else "🚫"
                self.stdout.write(
                    f"  {status_icon} {fake_app['code']} - {fake_app['security_status']} {feeds_info}"
                )

    def quick_audit(self):
        """Quick security overview."""
        results = audit_fake_apps()
        
        if results['fake_apps'] > 0:
            self.stdout.write(
                self.style.ERROR(f"🚨 {results['fake_apps']} FAKE APPS DETECTED!")
            )
            self.stdout.write("Run with --audit to see details")
            self.stdout.write("Run with --cleanup to fix")
        else:
            self.stdout.write(
                self.style.SUCCESS("✅ No fake apps detected")
            )

    def cleanup_apps(self, force=False):
        """Clean up fake apps."""
        self.stdout.write("🧹 Cleaning up fake apps...")
        
        results = cleanup_fake_apps(dry_run=not force)
        
        if results['actions']:
            for action in results['actions']:
                if 'Would' in action:
                    self.stdout.write(self.style.WARNING(f"  ⏸️  {action}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"  {action}"))
        else:
            self.stdout.write("  ✅ No cleanup needed")
        
        if not force and results['actions']:
            self.stdout.write("\nTo actually perform cleanup, run with --force")