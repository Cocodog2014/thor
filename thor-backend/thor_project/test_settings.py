"""Test settings overriding migrations for faster isolated metric tests."""
from .settings import *  # noqa

# Disable migrations for targeted apps (use syncdb-style table creation).
MIGRATION_MODULES = {
    'FutureTrading': None,
}

# Use faster password hasher, if not already.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
