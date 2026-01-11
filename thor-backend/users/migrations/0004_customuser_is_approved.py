from django.db import migrations, models


def approve_existing_users(apps, schema_editor):
    CustomUser = apps.get_model('users', 'CustomUser')
    # Preserve existing deployments: mark current users as approved.
    CustomUser.objects.all().update(is_approved=True)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_owner_role_sets_superuser'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='is_approved',
            field=models.BooleanField(default=False, help_text='Whether this user is approved by an admin to use the app'),
        ),
        migrations.RunPython(approve_existing_users, migrations.RunPython.noop),
    ]
