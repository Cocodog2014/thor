import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from GlobalMarkets.models import Market

print('=== CONTROL MARKETS ===')
control = Market.objects.filter(is_control_market=True).order_by('country')
print(f'Total control markets: {control.count()}/9')
print()

for m in control:
    print(f'{m.country:20} | Weight: {float(m.weight)*100:5.1f}%')
