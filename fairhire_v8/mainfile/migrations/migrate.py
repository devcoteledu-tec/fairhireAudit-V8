#!/usr/bin/env python3
"""
migrate.py — FairHire database migration runner
================================================
Applies pending SQL migrations in version order.
Already-applied migrations are skipped (tracked in schema_migrations table).

Usage
─────
    python migrate.py                  # apply all pending migrations
    python migrate.py --dry-run        # print what would run, touch nothing
    python migrate.py --status         # show applied vs pending
    python migrate.py --version 0003   # apply up to and including 0003 only

Environment
───────────
    DATABASE_URL must be set (same .env used by api.py)

Migration files
───────────────
    Place .sql files in the same directory as this script.
    Naming convention:  NNNN_description.sql  (e.g. 0005_add_audit_index.sql)
    Files are applied in lexicographic order — the 4-digit prefix enforces this.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

MIGRATIONS_DIR = Path(__file__).parent
DATABASE_URL   = os.getenv("DATABASE_URL", "")

BOLD  = "\033[1m"
GREEN = "\033[32m"
AMBER = "\033[33m"
RED   = "\033[31m"
RESET = "\033[0m"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _connect() -> psycopg2.extensions.connection:
    if not DATABASE_URL:
        print(f"{RED}ERROR: DATABASE_URL is not set.{RESET}")
        sys.exit(1)
    try:
        return psycopg2.connect(DATABASE_URL)
    except psycopg2.OperationalError as exc:
        print(f"{RED}ERROR: Could not connect to database.\n{exc}{RESET}")
        sys.exit(1)


def _ensure_migrations_table(conn: psycopg2.extensions.connection) -> None:
    """Create schema_migrations if it does not exist yet (idempotent)."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version     TEXT        PRIMARY KEY,
                description TEXT        NOT NULL,
                applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
    conn.commit()


def _applied_versions(conn: psycopg2.extensions.connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM schema_migrations ORDER BY version")
        return {row[0] for row in cur.fetchall()}


def _all_migration_files() -> list[Path]:
    files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"))
    return files


def _version_from_path(path: Path) -> str:
    return path.stem[:4]


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_status(conn: psycopg2.extensions.connection) -> None:
    applied = _applied_versions(conn)
    files   = _all_migration_files()

    if not files:
        print("No migration files found.")
        return

    print(f"\n{'Version':<10} {'Status':<12} File")
    print("─" * 60)
    for f in files:
        ver    = _version_from_path(f)
        status = f"{GREEN}applied{RESET}" if ver in applied else f"{AMBER}pending{RESET}"
        print(f"{ver:<10} {status:<20} {f.name}")
    print()


def cmd_migrate(
    conn: psycopg2.extensions.connection,
    dry_run: bool = False,
    up_to: str | None = None,
) -> None:
    applied = _applied_versions(conn)
    files   = _all_migration_files()
    pending = [
        f for f in files
        if _version_from_path(f) not in applied
        and (up_to is None or _version_from_path(f) <= up_to)
    ]

    if not pending:
        print(f"{GREEN}✓ Database is up to date. No migrations to apply.{RESET}")
        return

    print(f"\n{BOLD}{'DRY RUN — ' if dry_run else ''}Migrations to apply:{RESET}")
    for f in pending:
        print(f"  → {f.name}")
    print()

    if dry_run:
        print(f"{AMBER}Dry run complete. Nothing was applied.{RESET}")
        return

    for f in pending:
        ver = _version_from_path(f)
        sql = f.read_text(encoding="utf-8")
        print(f"Applying {BOLD}{f.name}{RESET} ...", end=" ", flush=True)
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                # Insert tracking row if the migration SQL didn't already do it
                # (our migrations INSERT themselves, but this is a safety net)
                cur.execute(
                    """
                    INSERT INTO schema_migrations (version, description)
                    VALUES (%s, %s)
                    ON CONFLICT (version) DO NOTHING
                    """,
                    (ver, f.stem[5:].replace("_", " ")),
                )
            conn.commit()
            print(f"{GREEN}✓{RESET}")
        except Exception as exc:
            conn.rollback()
            print(f"{RED}FAILED{RESET}")
            print(f"\n{RED}ERROR in {f.name}:\n{exc}{RESET}")
            print("\nTransaction rolled back. Fix the migration and re-run.")
            sys.exit(1)

    print(f"\n{GREEN}✓ All migrations applied successfully.{RESET}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="FairHire migration runner")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Print pending migrations without applying them")
    parser.add_argument("--status",   action="store_true",
                        help="Show applied and pending migrations then exit")
    parser.add_argument("--version",  metavar="NNNN",
                        help="Apply migrations up to and including this version")
    args = parser.parse_args()

    conn = _connect()
    _ensure_migrations_table(conn)

    if args.status:
        cmd_status(conn)
    else:
        cmd_migrate(conn, dry_run=args.dry_run, up_to=args.version)

    conn.close()


if __name__ == "__main__":
    main()
