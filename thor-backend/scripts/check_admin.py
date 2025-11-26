"""Check Django admin user"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Check for admin@360edu.org
admin1 = User.objects.filter(email='admin@360edu.org').first()
print(f"\nChecking admin@360edu.org:")
print(f"  Exists: {admin1 is not None}")
if admin1:
    print(f"  Username: {admin1.username}")
    print(f"  Email: {admin1.email}")
    print(f"  Is staff: {admin1.is_staff}")
    print(f"  Is superuser: {admin1.is_superuser}")
    print(f"  Is active: {admin1.is_active}")

# Check for any superuser
print(f"\nAll superusers:")
for user in User.objects.filter(is_superuser=True):
    print(f"  Username: {user.username}, Email: {user.email}, Active: {user.is_active}")
