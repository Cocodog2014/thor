from django.apps import AppConfig


class AccountStatementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'account_statement'
    verbose_name = 'Account Statement'
    
    def ready(self):
        """Initialize app when Django starts."""
        # Import any signals or initialization code here
        pass
