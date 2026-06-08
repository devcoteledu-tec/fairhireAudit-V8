#!/usr/bin/env bash
# =============================================================================
# FairHire Pre-flight Check
# Run this BEFORE "docker compose up" to catch common misconfigurations.
# Usage: bash docker/preflight_check.sh
# =============================================================================

set -euo pipefail
ERRORS=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ok()   { echo -e "${GREEN}  ✓${NC} $1"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $1"; }
fail() { echo -e "${RED}  ✗${NC} $1"; ERRORS=$((ERRORS + 1)); }

echo ""
echo "=================================================="
echo "  FairHire Pre-flight Check"
echo "=================================================="
echo ""

# --- 1. .env file exists ---
if [[ -f "docker/.env" ]]; then
  ok ".env file found at docker/.env"
else
  fail ".env file not found. Copy docker/.env.example to docker/.env and fill in all values."
fi

# --- 2. Domain configured in nginx.conf ---
if grep -q "YOUR_DOMAIN_HERE" docker/dashboard/nginx.conf; then
  fail "nginx.conf still contains 'YOUR_DOMAIN_HERE'. Replace all 7 occurrences with your domain. Run:"
  echo "        sed -i 's/YOUR_DOMAIN_HERE/youractualdomain.com/g' docker/dashboard/nginx.conf"
  echo "        Then verify: grep 'YOUR_DOMAIN_HERE' docker/dashboard/nginx.conf  # should return nothing"
else
  CONFIGURED_DOMAIN=$(grep -oP 'ssl_certificate\s+/etc/letsencrypt/live/\K[^/]+' docker/dashboard/nginx.conf | head -1 || true)
  ok "nginx.conf domain is configured: ${CONFIGURED_DOMAIN}"
fi

# --- 3. SSL certificate exists ---
# Extract domain from nginx.conf
DOMAIN=$(grep -oP "ssl_certificate\s+/etc/letsencrypt/live/\K[^/]+" docker/dashboard/nginx.conf | head -1 || true)
if [[ -z "$DOMAIN" ]]; then
  warn "Could not parse domain from nginx.conf ssl_certificate line — skipping SSL cert check."
elif [[ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]]; then
  ok "SSL certificate found for ${DOMAIN}"
else
  fail "SSL certificate NOT found at /etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
  echo "        Run this BEFORE docker compose up:"
  echo "        sudo certbot certonly --standalone -d ${DOMAIN} -d www.${DOMAIN}"
fi

# --- 4. Required env vars set ---
if [[ -f "docker/.env" ]]; then
  REQUIRED_VARS=(
    DATABASE_URL
    JWT_SECRET
    STRIPE_SECRET_KEY
    STRIPE_WEBHOOK_SECRET
    STRIPE_PRO_PRICE_ID
    RESEND_API_KEY
    EMAIL_FROM
    APP_DOMAIN
    ALLOWED_ORIGINS
  )
  OPTIONAL_VARS=(SENTRY_DSN COOKIE_SAMESITE COOKIE_DOMAIN)
  for VAR in "${OPTIONAL_VARS[@]}"; do
    VAL="${!VAR:-}"
    if [[ -z "$VAL" ]]; then
      warn "Optional var ${VAR} is not set (error monitoring will be disabled — recommended for production)"
    else
      ok "Env var ${VAR} is set"
    fi
  done
  source docker/.env 2>/dev/null || true
  for VAR in "${REQUIRED_VARS[@]}"; do
    VAL="${!VAR:-}"
    if [[ -z "$VAL" || "$VAL" == *"your-"* || "$VAL" == *"change-me"* ]]; then
      fail "Env var ${VAR} is not set or still has placeholder value."
    else
      ok "Env var ${VAR} is set"
    fi
  done
fi

# --- 5. Docker & docker compose available ---
if command -v docker &>/dev/null; then
  ok "docker is available"
else
  fail "docker not found. Please install Docker."
fi
if docker compose version &>/dev/null; then
  ok "docker compose (v2) is available"
elif docker-compose version &>/dev/null; then
  warn "docker-compose (v1) found. Consider upgrading to Docker Compose v2."
else
  fail "Neither 'docker compose' nor 'docker-compose' found."
fi

# --- Summary ---
echo ""
echo "=================================================="
if [[ $ERRORS -eq 0 ]]; then
  echo -e "${GREEN}  All checks passed. Ready to run: docker compose up -d${NC}"
else
  echo -e "${RED}  ${ERRORS} issue(s) found. Fix the above before running docker compose up.${NC}"
fi
echo "=================================================="
echo ""

exit $ERRORS
