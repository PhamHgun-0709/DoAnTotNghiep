#!/usr/bin/env python
"""
Database Migration Helper Script

This script provides utilities for managing database migrations with Alembic.
It can be run standalone or called from the API startup process.

Usage:
    python scripts/migrate.py upgrade head  # Apply all migrations
    python scripts/migrate.py current       # Show current revision
    python scripts/migrate.py history       # Show migration history
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "api"))

from alembic.config import Config
from alembic import command
from app.models.db import resolve_database_url


def get_alembic_config():
    """Get Alembic configuration."""
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", resolve_database_url())
    return config


def upgrade(target='head'):
    """Apply migrations up to target revision."""
    config = get_alembic_config()
    print(f"🔄 Upgrading database to {target}...")
    try:
        command.upgrade(config, target)
        print(f"✅ Database upgraded successfully to {target}")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def downgrade(target):
    """Downgrade migrations to target revision."""
    config = get_alembic_config()
    print(f"🔄 Downgrading database to {target}...")
    try:
        command.downgrade(config, target)
        print(f"✅ Database downgraded successfully to {target}")
        return True
    except Exception as e:
        print(f"❌ Downgrade failed: {e}")
        return False


def current():
    """Show current database revision."""
    config = get_alembic_config()
    try:
        command.current(config)
    except Exception as e:
        print(f"Error: {e}")


def history():
    """Show migration history."""
    config = get_alembic_config()
    try:
        command.history(config)
    except Exception as e:
        print(f"Error: {e}")


def heads():
    """Show current branch heads."""
    config = get_alembic_config()
    try:
        command.heads(config)
    except Exception as e:
        print(f"Error: {e}")


def branches():
    """Show available branches."""
    config = get_alembic_config()
    try:
        command.branches(config)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python migrate.py [command] [options]")
        print("\nCommands:")
        print("  upgrade [target]  - Apply migrations (default: head)")
        print("  downgrade [target]- Revert to target revision")
        print("  current           - Show current revision")
        print("  history           - Show migration history")
        print("  heads             - Show branch heads")
        print("  branches          - Show available branches")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'upgrade':
        target = sys.argv[2] if len(sys.argv) > 2 else 'head'
        success = upgrade(target)
        sys.exit(0 if success else 1)
    elif command == 'downgrade':
        if len(sys.argv) < 3:
            print("Error: downgrade requires target revision")
            sys.exit(1)
        success = downgrade(sys.argv[2])
        sys.exit(0 if success else 1)
    elif command == 'current':
        current()
    elif command == 'history':
        history()
    elif command == 'heads':
        heads()
    elif command == 'branches':
        branches()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
