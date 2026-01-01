# Futures Total Management

This folder is the study-owned home for management-related documentation.

Important:
- Django discovers commands only under `ThorTrading.management.commands`.
- The modules there remain as ultra-thin shims.
- Canonical `Command` classes live under `ThorTrading.studies.futures_total.management.commands`.
- The actual command implementations live under `ThorTrading.studies.futures_total.command_logic`.

## Commands

Run via `python manage.py <command>` as usual.

Canonical command modules: `ThorTrading/studies/futures_total/management/commands/`
