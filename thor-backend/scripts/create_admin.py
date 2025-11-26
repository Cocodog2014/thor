"""Create admin superuser"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create admin user
admin, created = User.objects.get_or_create(
    email='admin@360edu.org',
    defaults={
        'first_name': 'Admin',
        'last_name': 'User',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
    }
)

if created:
    admin.set_password('Coco1464#')
    admin.save()
    print(f"✅ Created new admin user: {admin.email}")
else:
    admin.set_password('Coco1464#')
    admin.is_staff = True
    admin.is_superuser = True
    admin.is_active = True
    admin.save()
    print(f"✅ Updated existing admin user: {admin.email}")

print(f"\nLogin credentials:")
print(f"  Email: admin@360edu.org")
print(f"  Password: Coco1464#")
print(f"  URL: http://localhost:8000/admin/")
