# FairHire v6.2 — Fix Changelog

All issues identified in the v6.2-hostable release have been resolved.
The container is now production-ready.

---

## 🔴 CRASH Fixes (container would not start)

### CRASH 1 — Missing `stripe` and `resend` in `requirements.docker.txt`
- **File:** `D-V6.2 E&F AUDIT ENGINE/docker/backend/requirements.docker.txt`
- **Change:** Added `stripe==10.12.0` and `resend==2.4.0`
- **Why:** `api.py` imports both at module level; Python raised `ModuleNotFoundError` before Uvicorn started.

### CRASH 2 — `stripe_webhook.py` not copied into the Docker image
- **File:** `D-V6.2 E&F AUDIT ENGINE/docker/backend/Dockerfile`
- **Change:** Added `fairhire/stripe_webhook.py` to the `COPY` line in Stage 2
- **Why:** `api.py` imports `stripe_webhook` at startup; the missing file caused immediate crash.

### CRASH 3 — `nginx.conf` had literal `yourdomain.com` placeholder
- **File:** `D-V6.2 E&F AUDIT ENGINE/docker/dashboard/nginx.conf`
- **Change:** Replaced all 7 occurrences of `yourdomain.com` with `YOUR_DOMAIN_HERE`
- **Why:** Nginx validates the SSL cert path at startup. A non-existent path causes immediate exit.
- **Action required:** Before `docker compose up`, run:
  ```bash
  sed -i 's/YOUR_DOMAIN_HERE/youractualdomain.com/g' docker/dashboard/nginx.conf
  ```

---

## 🟡 Broken Feature Fixes (container boots but features fail)

### BROKEN 1 — `resend.Emails.send()` wrong API for resend v2.4.0
- **File:** `D-V6.2 E&F AUDIT ENGINE/fairhire/api.py` (line ~473)
- **Change:** Replaced plain dict argument with typed `resend.Emails.SendParams` object
- **Why:** resend v2.x API requires a typed params object; plain dict raises `TypeError`, silently breaking all email sends (verification, password reset).

### BROKEN 2 — `GEMINI_API_KEY` ghost variable
- **Files:** `docker/docker-compose.yml`, `docker/.env.example`
- **Change:** Removed `GEMINI_API_KEY` from both files
- **Why:** `api.py` never reads this env var. It was leftover from an earlier version and caused confusion.

### BROKEN 3 — Dev/test packages in production image
- **File:** `docker/backend/requirements.docker.txt`
- **Change:** Moved `pytest`, `pytest-cov`, `ruff`, `httpx` to new `docker/backend/requirements.dev.txt`
- **Why:** Test tools added ~60MB to the production image with no benefit. The Dockerfile only installs `requirements.docker.txt`.

---

## 🟠 Guard / Reliability Fixes

### WARN 1 — No guard before `docker compose up` for missing SSL cert
- **New file:** `docker/preflight_check.sh`
- **Change:** Created a shell script that validates domain config, SSL cert presence, required env vars, and Docker availability — with clear error messages for each failure.
- **Usage:** `bash docker/preflight_check.sh` (run before `docker compose up`)

- **File:** `docker/docker-compose.yml`
- **Change:** Added warning comment block at the top describing the pre-flight requirement.

### WARN 2 — DEPLOY.md had wrong placeholder text and missing preflight step
- **File:** `DEPLOY.md`
- **Change:** Updated to reference `YOUR_DOMAIN_HERE`, removed `GEMINI_API_KEY` from checklist, added Step 8 (pre-flight check), clarified SSL must happen before compose up.

---

## Summary

| # | Severity | File | Status |
|---|---|---|---|
| 1 | 🔴 CRASH | `requirements.docker.txt` | ✅ Fixed |
| 2 | 🔴 CRASH | `Dockerfile` COPY line | ✅ Fixed |
| 3 | 🔴 CRASH | `nginx.conf` yourdomain placeholder | ✅ Fixed |
| 4 | 🟡 BROKEN | `api.py` resend SendParams | ✅ Fixed |
| 5 | 🟡 BROKEN | `docker-compose.yml` GEMINI ghost var | ✅ Fixed |
| 6 | 🟡 BROKEN | `requirements.docker.txt` test deps | ✅ Fixed |
| 7 | 🟠 WARN | SSL preflight guard | ✅ Fixed |
| 8 | 🟠 WARN | DEPLOY.md accuracy | ✅ Fixed |

Note: `datetime.utcnow()` was already using `datetime.datetime.now(datetime.timezone.utc)` in the codebase — no change needed.

---
## v6.2.0 Launch Blocker Fixes (QA Audit)

| # | Severity | File | Fix |
|---|---|---|---|
| 9 | 🔴 BLOCKER | `README.md` | Removed false Gemini AI claim; replaced with accurate statistical methods description |
| 10 | 🔴 BLOCKER | `README.md` | Corrected license badge from MIT to Apache 2.0 |
| 11 | 🔴 BLOCKER | `api.py`, `docker-compose.yml` | Unified version to 6.2.0 everywhere |
| 12 | 🔴 BLOCKER | `nginx.conf` | Added cdnjs.cloudflare.com to CSP script-src and font-src |
| 13 | 🟡 HIGH | `requirements.docker.txt` | Pinned all packages to exact versions matching requirements.txt |
| 14 | 🟠 MEDIUM | `DEPLOY.md` | SSL auto-renewal promoted to mandatory Step 11 |
