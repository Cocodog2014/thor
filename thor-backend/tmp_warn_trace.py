import os
import sys
import warnings
import traceback
from django.core.management import execute_from_command_line

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thor_project.settings")
sys.path.insert(0, os.path.dirname(__file__))

def warn_with_trace(message, category, filename, lineno, file=None, line=None):
    stack = ''.join(traceback.format_stack())
    sys.stderr.write(f"\nWARNING TRACE [{category.__name__}]: {message}\n{stack}\n")

warnings.showwarning = warn_with_trace
warnings.simplefilter('default')

execute_from_command_line(['manage.py','market_open_capture','--country','Japan','--force'])
