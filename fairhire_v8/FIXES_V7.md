# FairHire v6.2 → v6.3 — Fix Changelog

All issues identified in the v6.2-github readiness audit have been resolved.

---

## 🔴 Critical Fixes

### CRIT 1 — No error monitoring (Sentry integration added)
- **Files:** `fairhire/api.py`, `docker/backend/requirements.docker.txt`,
  `docker/docker-compose.yml`, `docker/.env.example`
- **Change:** Integrated `sentry-sdk[fastapi]==2.3.1` with optional opt-in via
  `SENTRY_DSN` environment variable. Initialises on startup with
  `traces_sample_rate=0.1` and `send_default_pii=False`.
- **Why:** Production exceptions were completely invisible without this.
  The app now reports every unhandled exception to Sentry in real time.
  Set `SENTRY_DSN` in `.env`; leave blank to disable (a log warning appears).

### CRIT 2 — No CSRF protection on state-mutating endpoints
- **File:** `fairhire/api.py`
- **Change:** Implemented the **double-submit cookie pattern**:
  - `_issue_csrf_cookie()` sets a readable (non-HttpOnly) `fh_csrf` cookie
    on login and every token refresh.
  - `_require_csrf()` validates that the `X-CSRF-Token` request header
    matches the cookie value using `hmac.compare_digest` (timing-safe).
  - Guards applied to: `/api/audit`, `/api/report`, `/api/logout`,
    `/api/create-checkout-session`.
  - Bearer-token requests (API clients) are automatically exempt.
- **Why:** HttpOnly cookies alone are insufficient — cross-origin POST
  requests can still carry cookies. Double-submit defeats this without
  requiring server-side session state.
- **Frontend action required:** See "Frontend CSRF integration" in DEPLOY.md.

### CRIT 3 — `__pycache__` committed to repository
- **Change:** Removed `mainfile/fairhire/__pycache__/` directory entirely.
  Added a comment in `.gitignore` with the `git rm --cached` command
  so future contributors know how to clean up if it reappears.
- **Why:** Compiled `.pyc` bytecode in version control bloats the repo,
  causes false diffs, and can expose implementation details.

---

## 🟡 Moderate Fixes

### MOD 1 — Migration files had spaces/parens in filenames
- **Files:** `migrations/migrate (1).py` → `migrations/migrate.py`
           `migrations/README (1).md`  → `migrations/README.md`
- **Why:** Parentheses and spaces in filenames cause quoting failures in bash,
  Makefiles, and some CI runners. Safe slug names required for scripts.

### MOD 2 — `sentry-sdk` added to production requirements
- **File:** `docker/backend/requirements.docker.txt`
- **Change:** Added `sentry-sdk[fastapi]==2.3.1` with pinned version.
- **Why:** The Sentry integration requires the package to be present in the
  Docker image. Pinned for reproducible builds.

---

## 🟠 Minor / Documentation Fixes

### MIN 1 — DEPLOY.md updated
- **Change:** Added Step 7 (Sentry setup), updated Step numbers accordingly,
  added "Frontend CSRF integration" section with code example,
  added two new rows to the Troubleshooting table for CSRF errors.

### MIN 2 — `.env.example` updated
- **Change:** Added `SENTRY_DSN=` with comment linking to sentry.io docs.

### MIN 3 — `preflight_check.sh` updated
- **Change:** Added optional-var check for `SENTRY_DSN` — prints a warning
  (not an error) if it is unset, so deployers are reminded without blocking.

### MIN 4 — `docker-compose.yml` updated
- **Change:** Added `SENTRY_DSN=${SENTRY_DSN:-}` to backend environment block
  so the variable is passed through from `.env` to the container.

---

## Summary

| # | Severity | Change | Status |
|---|---|---|---|
| 1 | 🔴 Critical | Sentry error monitoring integrated | ✅ Fixed |
| 2 | 🔴 Critical | CSRF double-submit cookie protection | ✅ Fixed |
| 3 | 🔴 Critical | `__pycache__` removed from repo | ✅ Fixed |
| 4 | 🟡 Moderate | Migration filenames with spaces renamed | ✅ Fixed |
| 5 | 🟡 Moderate | sentry-sdk pinned in requirements.docker.txt | ✅ Fixed |
| 6 | 🟠 Minor | DEPLOY.md Sentry + CSRF documentation | ✅ Fixed |
| 7 | 🟠 Minor | .env.example SENTRY_DSN added | ✅ Fixed |
| 8 | 🟠 Minor | preflight_check.sh Sentry optional check | ✅ Fixed |
| 9 | 🟠 Minor | docker-compose.yml SENTRY_DSN passthrough | ✅ Fixed |

---

## Remaining known gaps (future work)

- **No E2E tests** — add Playwright smoke tests for critical paths
- **No load tests** — add a k6 profile for the `/api/audit` endpoint
- **No image registry push in CI** — add GHCR push step for traceable releases
- **No database backup runbook** — document Supabase PITR restore procedure
- **No HA / failover** — single-node deployment; Kubernetes manifests not included
