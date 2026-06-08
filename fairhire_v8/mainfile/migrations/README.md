# FairHire — Database Migrations

## Two paths, one destination

| Situation | What to run |
|---|---|
| **Fresh install** (empty database) | Run `schema_full.sql` once in your Supabase SQL editor |
| **Existing database** (already has data) | Run `python migrate.py` — it applies only the pending migrations |

---

## Fresh install

```bash
# In Supabase SQL editor, paste and run:
schema_full.sql
```

This creates all tables, indexes, seed data, and marks all migrations
as applied so `migrate.py` knows to skip them.

---

## Existing database — running migrations

```bash
# Copy your .env to the migrations folder or export DATABASE_URL
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# See what's pending
python migrate.py --status

# Apply all pending migrations
python migrate.py

# Dry run — see what would run without touching the database
python migrate.py --dry-run

# Apply only up to a specific version
python migrate.py --version 0003
```

---

## Adding a new migration

1. Create a new file: `NNNN_short_description.sql`
   - Use the next number in sequence (e.g. `0005_add_audit_index.sql`)
   - The 4-digit prefix is what controls run order

2. Write idempotent-safe SQL. Since each migration runs inside a transaction
   that rolls back on failure, do **not** use `IF NOT EXISTS` — if a migration
   partially ran and was rolled back, it will be retried cleanly.

3. End the file with the tracking insert:
   ```sql
   INSERT INTO schema_migrations (version, description)
   VALUES ('0005', 'Short description of what changed');
   ```

4. Update `schema_full.sql` to include your changes (for future fresh installs).

5. Run `python migrate.py --dry-run` to confirm it appears as pending,
   then `python migrate.py` to apply it.

---

## Migration files

| File | What it does |
|---|---|
| `0001_initial_schema.sql` | users, uploads, audits tables and indexes |
| `0002_v6_audit_columns.sql` | gender_stats, module_results, systemic_bias, region, caste/skin fields |
| `0003_email_verification.sql` | users.email_verified, tokens table |
| `0004_stripe_billing.sql` | Stripe columns on users, plan_limits table |

---

## How rollback works

Each migration runs inside a single transaction. If any statement fails,
the entire migration is rolled back automatically and `migrate.py` exits
with a non-zero code. The `schema_migrations` row is **not** inserted,
so re-running `migrate.py` after you fix the SQL will retry it cleanly.

For rolling back an already-applied migration (rare), write a new
`NNNN_revert_*.sql` file that undoes the change. Never delete or edit
an applied migration file.
