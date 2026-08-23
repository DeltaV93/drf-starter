#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'template.settings')

    # Opt-in remote debugging. Set DEBUGPY=1 to have the process wait for a
    # debugger to attach on DEBUGPY_PORT (default 5678). Off by default so
    # `manage.py runserver` never blocks on a debugger that isn't there.
    if os.environ.get('DEBUGPY') == '1' and 'runserver' in sys.argv:
        # Only attach in the reloader's child process, otherwise the port is
        # claimed twice.
        if os.environ.get('RUN_MAIN') == 'true':
            import debugpy

            port = int(os.environ.get('DEBUGPY_PORT', '5678'))
            debugpy.listen(('0.0.0.0', port))
            print(f'debugpy listening on port {port}; waiting for client...')
            debugpy.wait_for_client()

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            'available on your PYTHONPATH environment variable? Did you '
            'forget to activate a virtual environment?'
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
