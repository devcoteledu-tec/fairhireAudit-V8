# FairHire — Complete Hosting Guide

This guide gets FairHire running on a fresh Ubuntu 22.04 VPS in under 30 minutes.
Estimated time: ~20 minutes of setup + ~10 minutes of build time.

---

## Prerequisites

- A VPS with Ubuntu 22.04 (2 vCPU / 2 GB RAM minimum recommended)
- A domain name with an A record pointing to your VPS IP
- A [Supabase](https://supabase.com) project (free tier works)
- A [Stripe](https://stripe.com) account (test mode is fine to start)
- A [Resend](https://resend.com) account with a verified sender domain

---

## Step 1 — Install Docker on the VPS

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version   # confirm it installed
```

---

## Step 2 — Upload the project

From your local machine:

```bash
scp FairHire-fixed.zip user@your-vps-ip:~
ssh user@your-vps-ip
unzip FairHire-fixed.zip
cd fairhire_v8_fixed/mainfile/docker
```

---

## Step 3 — Set up the database

1. Open your [Supabase project](https://supabase.com/dashboard)
2. Go to **SQL Editor**
3. Open `migrations/schema_full.sql` from this project
4. Paste the entire contents into the SQL editor and click **Run**
5. Copy your connection string from **Project Settings → Database → Connection string → URI**

---

## Step 4 — Configure your environment

```bash
cd docker
cp .env.example .env
nano .env   # or use vim / any editor
```

Fill in every value in `.env`. Refer to the comments in `.env.example` for
where to find each value. Do not leave any placeholder values in place.

**Required values checklist:**
- [ ] `DATABASE_URL` — Supabase connection string
- [ ] `JWT_SECRET` — random 32+ char string (`python3 -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] `APP_DOMAIN` — e.g. `https://yourdomain.com`
- [ ] `ALLOWED_ORIGINS` — e.g. `https://yourdomain.com,https://www.yourdomain.com`
- [ ] `RESEND_API_KEY` — from Resend dashboard
- [ ] `EMAIL_FROM` — verified sender address on Resend
- [ ] `STRIPE_SECRET_KEY` — from Stripe dashboard
- [ ] `STRIPE_WEBHOOK_SECRET` — from Stripe webhook endpoint (see Step 6)
- [ ] `STRIPE_PRO_PRICE_ID` — Price ID of your Pro product in Stripe
- [ ] `SENTRY_DSN` — (optional but recommended) from [sentry.io](https://sentry.io) → New Project → Python

---

## Cross-domain deployments (frontend and backend on different subdomains)

If you deploy the frontend and backend on separate subdomains (e.g. `app.fairhire.io` for
the React dashboard and `api.fairhire.io` for the FastAPI backend), you must configure
cookies and CORS to work across origins. Without this, every authenticated request will
fail with a 401 and no obvious error message.

**Required `.env` changes:**

- Set `COOKIE_SAMESITE=none` — allows the browser to send cookies on cross-origin requests.
- Set `COOKIE_SECURE=true` — required by all browsers when `SameSite=None`; cookies are
  only sent over HTTPS. The application also enforces this at startup and will refuse to
  start if `COOKIE_SAMESITE=none` is set without `COOKIE_SECURE=true`.
- Set `COOKIE_DOMAIN=.yourdomain.com` (note the leading dot) so cookies are shared across
  all subdomains (e.g. both `app.fairhire.io` and `api.fairhire.io`).
- Add **both** the frontend and API origins to `ALLOWED_ORIGINS`, for example:
  `ALLOWED_ORIGINS=https://app.fairhire.io,https://api.fairhire.io`

**Stripe webhook URL** does not change — Stripe sends webhooks directly to the backend;
the cross-domain cookie configuration does not affect it. Keep the webhook URL pointing at
`https://api.yourdomain.com/api/stripe/webhook` as configured in Step 8.

> ⚠️ **Warning:** Setting `COOKIE_SAMESITE=none` without `COOKIE_SECURE=true` is silently
> blocked by all modern browsers (Chrome, Firefox, Safari) and is also rejected at
> application startup. Both settings must be present together for cross-domain cookies to work.

---

## Step 5 — Configure your domain in nginx.conf

Replace every occurrence of `YOUR_DOMAIN_HERE` with your actual domain. There are **7 places**:

```bash
# From the project root (D-V6.2 E&F AUDIT ENGINE directory):
sed -i 's/YOUR_DOMAIN_HERE/youractualdomain.com/g' docker/dashboard/nginx.conf
# Example:
# sed -i 's/YOUR_DOMAIN_HERE/fairhire.io/g' docker/dashboard/nginx.conf
```

Verify:
```bash
grep "YOUR_DOMAIN_HERE" docker/dashboard/nginx.conf   # should return nothing
```

---

## Step 6 — Obtain SSL certificate ⚠️ MUST DO BEFORE STEP 8

> **Critical:** The Nginx container mounts `/etc/letsencrypt` at startup. If the cert
> does not exist when Docker starts, the container crashes immediately with
> `cannot load certificate`. Get the cert **before** running docker compose up.

```bash
# Install certbot on the host (not in Docker)
sudo apt-get install -y certbot

# Stop anything using port 80 first (nothing should be running yet)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Confirm certs exist:
sudo ls /etc/letsencrypt/live/yourdomain.com/
# You should see: fullchain.pem  privkey.pem
```

---

## Step 7 — Set up Sentry error monitoring (recommended)

Sentry gives you real-time visibility into unhandled exceptions in production.
Without it, backend errors are invisible unless you tail the Docker logs manually.

1. Create a free account at [sentry.io](https://sentry.io)
2. Create a new project → select **Python**
3. Copy the **DSN** from the project settings
4. Paste it into `docker/.env` as `SENTRY_DSN=https://...@sentry.io/...`

> You can skip this step and add it later. A startup warning will appear in logs
> if `SENTRY_DSN` is not set, but the app will run normally.

---

## Step 8 — Set up Stripe

1. In the [Stripe dashboard](https://dashboard.stripe.com/products):
   - Create a product called **FairHire Pro**
   - Add a recurring monthly price (e.g. ₹999/month or your preferred amount)
   - Copy the **Price ID** (starts with `price_`) → paste into `.env` as `STRIPE_PRO_PRICE_ID`

2. In Stripe **Developers → Webhooks**:
   - Click **Add endpoint**
   - URL: `https://yourdomain.com/api/stripe/webhook`
   - Subscribe to these events:
     - `checkout.session.completed`
     - `customer.subscription.deleted`
     - `invoice.payment_failed`
   - After saving, click the endpoint and copy the **Signing secret** (starts with `whsec_`)
   - Paste it into `.env` as `STRIPE_WEBHOOK_SECRET`

---

## Step 9 — Run pre-flight check ✅

Before launching, run the built-in pre-flight validator. It checks your domain,
SSL cert, .env values, and Docker availability — and gives a clear error if
anything is missing:

```bash
# From the D-V6.2 E&F AUDIT ENGINE directory:
bash docker/preflight_check.sh
```

All checks must pass before proceeding. Fix any reported issues, then re-run.

---

## Step 10 — Build and launch

```bash
# From the docker/ directory:
cd docker
docker compose --env-file .env up --build -d

# Watch the logs:
docker compose logs -f

# Check health:
curl http://localhost:8080/api/health
```

The dashboard container only starts after the backend passes its healthcheck,
so allow ~30 seconds for everything to come online.

---

## Step 11 — Verify everything works

| Check | Expected result |
|---|---|
| `https://yourdomain.com` | React dashboard loads |
| `https://yourdomain.com/api/health` | `{"status":"ok", ...}` |
| Register an account | Verification email arrives from Resend |
| Upload a CSV | Audit runs and report appears |
| Click Upgrade | Stripe Checkout opens |

---

## Step 12 — Set up SSL auto-renewal (required)

Let's Encrypt certificates expire every 90 days. Run the following to add a
renewal cron job. Replace `/home/$USER/fairhire_v8_fixed/mainfile/docker` with
the absolute path to your `docker/` directory if it differs.

```bash
DOCKER_DIR="/home/$USER/fairhire_v8_fixed/mainfile/docker"

(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && docker compose -f ${DOCKER_DIR}/docker-compose.yml restart dashboard") | crontab -
```

Verify it was added:

```bash
crontab -l
```

To test that the path is correct before relying on the cron job:

```bash
docker compose -f /home/$USER/fairhire_v8_fixed/mainfile/docker/docker-compose.yml ps
```

If that command lists the running containers, the cron path is valid.

---

## Ongoing maintenance

### View logs
```bash
docker compose -f docker/docker-compose.yml logs -f backend
docker compose -f docker/docker-compose.yml logs -f dashboard
```

### Restart after a config change
```bash
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml --env-file docker/.env up --build -d
```

### Update the app
```bash
# Upload new zip, extract, rebuild:
docker compose down
docker compose --env-file .env up --build -d
```

---

## Frontend CSRF integration

FairHire uses the **double-submit cookie** CSRF pattern. The backend sets a
readable (non-HttpOnly) cookie called `fh_csrf` on login and token refresh.
Your frontend JavaScript must copy this value into an `X-CSRF-Token` header
on every `POST` request that uses cookie auth:

```javascript
// authUtils.js — add this helper
export function getCsrfToken() {
  return document.cookie
    .split("; ")
    .find(row => row.startsWith("fh_csrf="))
    ?.split("=")[1] ?? "";
}

// Use in every authenticated POST call:
await fetch("/api/audit", {
  method: "POST",
  headers: { "X-CSRF-Token": getCsrfToken() },
  body: formData,
  credentials: "include",
});
```

Requests using the `Authorization: Bearer <token>` header are exempt
(API clients that don't use cookies are not vulnerable to CSRF).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Dashboard container exits immediately | SSL cert missing — run Step 6 first. Run `bash docker/preflight_check.sh` to diagnose. |
| `502 Bad Gateway` | Backend not healthy yet — wait 30s, check `docker logs fairhire-backend` |
| Emails not sending | Check `RESEND_API_KEY` and `EMAIL_FROM` are set and domain is verified on Resend |
| Stripe webhooks failing | Confirm `STRIPE_WEBHOOK_SECRET` matches the signing secret in Stripe dashboard |
| CORS errors in browser | Ensure `ALLOWED_ORIGINS` matches your exact domain (no trailing slash) |
| `403 CSRF token missing` | Frontend must send `X-CSRF-Token` header — see CSRF section above |
| `403 CSRF token invalid` | Cookie and header token mismatch — ensure `credentials: "include"` on fetch calls |
| `RuntimeError: DATABASE_URL is not set` | `.env` file not found or `DATABASE_URL` is blank |
| Pre-flight check fails | Fix each listed issue before running `docker compose up` |
