import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute('DROP TABLE IF EXISTS "ActAndPos_accountdailysnapshot" CASCADE')
cursor.execute('DROP TABLE IF EXISTS "ActAndPos_position" CASCADE')
cursor.execute('DROP TABLE IF EXISTS "ActAndPos_order" CASCADE')
cursor.execute('DROP TABLE IF EXISTS "ActAndPos_account" CASCADE')
print('✓ Legacy tables dropped')
