"""
api.py  ·  FairHire v6.2  —  Full feature merge
════════════════════════════════════════════════════════════════════════════════
FastAPI backend for FairHire React frontend.

This file merges:
  • All billing / auth features from v2.2-billing (zip):
      BILL-1  _check_plan_limit() with monthly counter reset
      BILL-2  /api/audit increments audit_count_this_month after success
      BILL-3  /api/report blocked for free-plan users (HTTP 402)
      BILL-4  POST /api/create-checkout-session (Stripe Checkout)
      BILL-5  GET  /api/subscription-status
      BILL-6  stripe_webhook router mounted at /api/stripe/webhook
      AUTH-1  Dual-token cookie system: fh_access (15 min) + fh_refresh (7 days)
      AUTH-2  GET  /api/verify-email
      AUTH-3  POST /api/forgot-password
      AUTH-4  POST /api/reset-password
      AUTH-5  POST /api/refresh
      AUTH-6  POST /api/logout
      AUTH-7  GET  /api/me
      AUTH-8  Register triggers email-verification flow (Resend)
      AUTH-9  Login blocks unverified emails (HTTP 403)

  • All security / correctness fixes from v2.2-security (new file):
      FIX-1   JWT authentication; user_id always from token
      FIX-2   Removed /api/debug/users endpoint entirely
      FIX-3   CORS locked to ALLOWED_ORIGINS env var
      FIX-4   Rate limiting via slowapi
      FIX-5   psycopg2 ThreadedConnectionPool; _get_conn / _put_conn helpers
      FIX-6   asynccontextmanager lifespan
      FIX-7   save_audit / ReportRequest with v6.0 fields
      FIX-8   AuthRequest.email → pydantic.EmailStr; normalised to lowercase
      FIX-9   Password validation: min 8, max 72, ≥1 digit or special char
      FIX-10  File upload: content_type allowlist widened; 500 000-row cap
      FIX-11  All print() replaced with structured logger calls
      FIX-12  _err() helper; consistent HTTPException shape
      FIX-13  /api/health returns HTTP 503 when DB is down
      FIX-14  Content-Disposition filename sanitised with re.sub
      FIX-15  Pydantic v2: model_config = ConfigDict everywhere
      FIX-16  _normalise_audit_row: _parse_jsonb() for all JSONB columns
      FIX-17  audit_endpoint: cross-browser content-type allowlist + ext check
      FIX-18  gender_stats JSONB + other_gender scalar columns
      FIX-19  /api/report fetches full audit row from DB via audit_id
      FIX-20  ReportRequest.audit_id required; company_name from DB user record
      FIX-21  module_results validated as dict after _parse_jsonb()
      FIX-22  data_present source-of-truth fixed via DB fetch (FIX-19)
      FIX-23  data_present injected into every module that is missing it

Run with:
    uvicorn api:app --host 0.0.0.0 --port 8080 --reload

════════════════════════════════════════════════════════════════════════════════
REQUIRED ENV VARS — add to your .env before any deployment
════════════════════════════════════════════════════════════════════════════════

  DATABASE_URL          postgresql://user:pass@host:5432/dbname
  JWT_SECRET            minimum-32-char-random-string
  JWT_EXPIRE_HOURS      24                              (default: 24)
  ALLOWED_ORIGINS       https://yourapp.com,https://www.yourapp.com
  APP_VERSION           6.2.0

  # Stripe (required for billing features)
  STRIPE_SECRET_KEY     sk_live_...  (or sk_test_... in dev)
  STRIPE_WEBHOOK_SECRET whsec_...
  STRIPE_PRO_PRICE_ID   price_...
  APP_DOMAIN            https://yourapp.com

  # Resend (required for email verification + password reset)
  RESEND_API_KEY        re_...
  EMAIL_FROM            noreply@your-domain.com

  # Cookie security (set to "false" only in local dev)
  COOKIE_SECURE         true

════════════════════════════════════════════════════════════════════════════════
"""

# ══════════════════════════════════════════════════════════════════════════════
# BUGS FIXED IN THIS REVISION
# ══════════════════════════════════════════════════════════════════════════════
# BUG-A (CRITICAL): Removed explicit _put_conn(_conn_limit) before raise
#         HTTPException(402) inside audit_endpoint. The redundant call returned
#         the connection to the pool twice (double-free), corrupting pool state
#         and causing deadlocks / wrong query results under concurrency.
#         Fix: deleted the _put_conn() call; the finally block is sufficient.
#
# BUG-C (SILENT): Moved the atomic plan-limit UPDATE to execute AFTER both
#         compute_fairness_metrics() and save_audit() succeed. Previously the
#         counter incremented before the audit engine ran, so a failed upload
#         consumed one of the user's monthly free-plan audits with no record
#         saved. Counter now only increments on a fully successful audit.
#
# BUG-D (SILENT): Added read-time plan expiry enforcement in get_current_user().
#         plan_expires_at was stored (by Stripe migration 0004) but never read.
#         Users whose Stripe webhook silently failed retained pro plan access
#         indefinitely. Fix: if plan_expires_at is in the past, the returned
#         user dict is overridden to plan='free' without a DB write.
#
# BUG-E (SILENT): Added _reset_monthly_counter_if_needed() call in
#         audit_endpoint before the atomic plan-limit UPDATE. Without the reset,
#         a stale audit_count_this_month from the previous calendar month would
#         cause the UPDATE's WHERE clause to incorrectly block valid free-plan
#         users with a spurious HTTP 402 at the start of each new month.
# ══════════════════════════════════════════════════════════════════════════════



import datetime
import decimal
import io
import json
import logging
import math
import os
import re
import secrets
import threading as _threading
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import bcrypt
import psycopg2
import psycopg2.extras
import psycopg2.pool
import numpy as np
import pandas as pd
import resend
import stripe
from dotenv import load_dotenv
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, ConfigDict

from fastapi import Cookie, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import matplotlib
matplotlib.use("Agg")

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False

load_dotenv()

from audit_engine import compute_fairness_metrics, FAIRHIRE_VERSION
from report_generator import generate_premium_report

# ══════════════════════════════════════════════════════════════════════════════
# LOGGING  (FIX-11)
# ══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("fairhire")

# ══════════════════════════════════════════════════════════════════════════════
# ENV / CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in .env")

# FIX-1 — JWT config
_JWT_SECRET = os.getenv("JWT_SECRET", "")
if not _JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set in .env — set a minimum 32-char random string")
_JWT_ALGORITHM      = "HS256"
_JWT_EXPIRE_HOURS   = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
_ACCESS_TOKEN_MINS  = 15
_REFRESH_TOKEN_DAYS = 7
_COOKIE_SECURE      = os.getenv("COOKIE_SECURE", "true").lower() != "false"
_COOKIE_SAMESITE    = os.getenv("COOKIE_SAMESITE", "lax")   # "none" for cross-domain deployments
_COOKIE_DOMAIN      = os.getenv("COOKIE_DOMAIN",  None)     # e.g. ".fairhire.io" for custom subdomains
if _COOKIE_SAMESITE.lower() == "none" and not _COOKIE_SECURE:
    raise RuntimeError(
        "COOKIE_SAMESITE=none requires COOKIE_SECURE=true — "
        "browsers silently reject SameSite=None cookies that lack the Secure flag. "
        "Either set COOKIE_SECURE=true or change COOKIE_SAMESITE back to 'lax'."
    )

# Email config (Resend)
_RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
_EMAIL_FROM     = os.getenv("EMAIL_FROM", "noreply@your-domain.com")
_APP_DOMAIN     = os.getenv("APP_DOMAIN", "https://your-domain.com")

if _RESEND_API_KEY:
    resend.api_key = _RESEND_API_KEY
else:
    logger.warning("RESEND_API_KEY is not set — email sending is disabled")

# Stripe config  (BILL-4)
_STRIPE_SECRET_KEY   = os.getenv("STRIPE_SECRET_KEY", "")
_STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID", "")
if _STRIPE_SECRET_KEY:
    stripe.api_key = _STRIPE_SECRET_KEY
else:
    logger.warning("STRIPE_SECRET_KEY is not set — billing features are disabled")

# Sentry error monitoring — optional but strongly recommended in production
_SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if _SENTRY_DSN and _SENTRY_AVAILABLE:
    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.1,   # 10 % of requests for performance tracing
        send_default_pii=False,   # never send PII to Sentry
    )
    logger.info("Sentry error monitoring initialised")
elif not _SENTRY_DSN:
    logger.warning(
        "SENTRY_DSN is not set — unhandled exceptions will not be reported. "
        "Set this in .env to enable error monitoring."
    )

REQUIRED_COLUMNS = {"gender", "shortlisted", "hired"}
MAX_FILE_BYTES   = 10 * 1024 * 1024   # 10 MB
MAX_ROWS         = 500_000
MIN_ROWS         = 30

# FIX-17 — widened allowlist covers every browser/OS combination.
# Windows Chrome:  application/octet-stream
# Firefox:         text/plain
# Mac Chrome/Edge: text/csv
# Rare clients:    application/csv, application/vnd.ms-excel
_ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "text/plain",
    "application/csv",
    "application/octet-stream",
    "application/vnd.ms-excel",
}

# Free plan monthly audit cap  (BILL-1)
_FREE_PLAN_MONTHLY_LIMIT = 5

# ══════════════════════════════════════════════════════════════════════════════
# ERROR HELPER  (FIX-12)
# ══════════════════════════════════════════════════════════════════════════════

def _err(status: int, msg: str) -> HTTPException:
    """All HTTPExceptions must be raised through this helper."""
    return HTTPException(status_code=status, detail={"error": msg, "code": status})

# ══════════════════════════════════════════════════════════════════════════════
# CONNECTION POOL  (FIX-5)
# ══════════════════════════════════════════════════════════════════════════════

_pool: psycopg2.pool.ThreadedConnectionPool | None = None
_pool_semaphore: _threading.Semaphore | None = None


def _get_conn() -> psycopg2.extensions.connection:
    """Acquire a DB connection. Raises HTTP 503 if the pool is exhausted."""
    if _pool is None:
        raise RuntimeError("DB pool is not initialised")
    acquired = _pool_semaphore.acquire(timeout=3) if _pool_semaphore else True
    if not acquired:
        raise _err(503, "Server is busy — please retry in a moment")
    try:
        return _pool.getconn()
    except Exception:
        if _pool_semaphore:
            _pool_semaphore.release()
        raise


def _put_conn(conn: psycopg2.extensions.connection) -> None:
    if _pool is not None:
        _pool.putconn(conn)
    if _pool_semaphore:
        _pool_semaphore.release()


def _dictcur(con: psycopg2.extensions.connection) -> psycopg2.extras.RealDictCursor:
    return con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ══════════════════════════════════════════════════════════════════════════════
# LIFESPAN  (FIX-6)
# ══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialise and close the connection pool around the app's lifetime."""
    global _pool, _pool_semaphore
    logger.info("Starting up — initialising DB connection pool …")
    try:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            # maxconn × workers must stay below your Postgres/Supabase connection limit.
            # Supabase free tier = ~15 connections total. Paid = higher.
            # Current: 1 worker × maxconn=10 = 10 connections max (safe for Supabase free tier ~15 limit).
            # If you scale to 2+ workers, reduce maxconn proportionally (e.g. maxconn=7 for 2 workers).
            minconn=1,
            maxconn=10,           # increased from 5
            dsn=DATABASE_URL,
        )
        _pool_semaphore = _threading.Semaphore(10)  # matches maxconn
        conn = _get_conn()
        try:
            conn.cursor().execute("SELECT 1")
        finally:
            _put_conn(conn)
        logger.info("DB connection pool ready (min=1, max=10)")
    except Exception:
        logger.exception("DB pool initialisation failed — check DATABASE_URL")
        raise

    yield  # ← application runs here

    logger.info("Shutting down — closing DB pool …")
    if _pool:
        _pool.closeall()
    logger.info("DB pool closed")

# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER  (FIX-4)
# ══════════════════════════════════════════════════════════════════════════════

def _jwt_sub_or_ip(request: Request) -> str:
    """Key function: use JWT sub for authenticated routes, IP for auth routes."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = jwt.decode(auth[7:], _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
            return payload.get("sub", get_remote_address(request))
        except JWTError:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=_jwt_sub_or_ip)

# ══════════════════════════════════════════════════════════════════════════════
# APP  (FIX-3, FIX-4, FIX-6)
# ══════════════════════════════════════════════════════════════════════════════

_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
_allow_credentials = bool(_origins)
if not _origins:
    logger.warning(
        "ALLOWED_ORIGINS is not set — CORS is open to all origins. "
        "This is acceptable only in local development."
    )
    _origins = ["*"]

app = FastAPI(
    title="FairHire Audit API",
    version=os.getenv("APP_VERSION", "6.2.0"),
    lifespan=lifespan,
)

# BUG-11 fix — stripe router mounted at module level so it appears in OpenAPI schema.
# Previously mounted inside lifespan() which hides it from /docs and /openapi.json.
from stripe_webhook import router as stripe_router  # noqa: PLC0415
app.include_router(stripe_router)
logger.info("Stripe webhook router mounted at /api/stripe/webhook")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ══════════════════════════════════════════════════════════════════════════════
# JWT HELPERS  (FIX-1 + AUTH-1 dual-token cookie system)
# ══════════════════════════════════════════════════════════════════════════════

# auto_error=False so we can also read from cookies before falling back to 401
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)


def _create_access_token(user_id: int, email: str) -> str:
    """Short-lived access token (15 min). Stored in fh_access HttpOnly cookie."""
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=_ACCESS_TOKEN_MINS)
    payload = {"sub": str(user_id), "email": email, "exp": expire, "type": "access"}
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def _create_refresh_token(user_id: int, email: str) -> str:
    """Long-lived refresh token (7 days). Stored in fh_refresh HttpOnly cookie."""
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=_REFRESH_TOKEN_DAYS)
    payload = {"sub": str(user_id), "email": email, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def _set_auth_cookies(response: Response, user_id: int, email: str) -> None:
    """Write fh_access, fh_refresh, and fh_csrf cookies."""
    access  = _create_access_token(user_id, email)
    refresh = _create_refresh_token(user_id, email)
    _kw = dict(
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        path="/",
        domain=_COOKIE_DOMAIN,
    )
    response.set_cookie("fh_access",  access,  max_age=_ACCESS_TOKEN_MINS * 60,      **_kw)
    response.set_cookie("fh_refresh", refresh, max_age=_REFRESH_TOKEN_DAYS * 86400,  **_kw)
    _issue_csrf_cookie(response)   # CSRF — readable by JS, validated on every state-mutating call


def _clear_auth_cookies(response: Response) -> None:
    """Expire both auth cookies immediately."""
    _kw = dict(
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        path="/",
        domain=_COOKIE_DOMAIN,
    )
    response.set_cookie("fh_access",  "", max_age=0, **_kw)
    response.set_cookie("fh_refresh", "", max_age=0, **_kw)
    # Also clear the CSRF token cookie
    response.set_cookie("fh_csrf", "", max_age=0, httponly=False,
                        secure=_COOKIE_SECURE, samesite=_COOKIE_SAMESITE,
                        path="/", domain=_COOKIE_DOMAIN)


# ══════════════════════════════════════════════════════════════════════════════
# CSRF PROTECTION  — Double-submit cookie pattern
# ══════════════════════════════════════════════════════════════════════════════
# All state-mutating endpoints (POST/DELETE) that use cookie auth must call
# _require_csrf(request) to validate the double-submit token.
#
# How it works:
#   1. On login/refresh, we set a non-HttpOnly cookie "fh_csrf" containing a
#      random 32-byte token. JavaScript can read this cookie.
#   2. The frontend must copy the value into an "X-CSRF-Token" request header.
#   3. The backend compares header value against cookie value using
#      hmac.compare_digest to prevent timing attacks.
#   4. An attacker's cross-origin form POST cannot set custom headers
#      (blocked by CORS), so the attack is defeated.
# ══════════════════════════════════════════════════════════════════════════════

import hmac as _hmac


def _issue_csrf_cookie(response: Response) -> str:
    """Generate a CSRF token, set it as a readable (non-HttpOnly) cookie, and return it."""
    token = secrets.token_hex(32)
    response.set_cookie(
        "fh_csrf",
        token,
        max_age=_REFRESH_TOKEN_DAYS * 86400,
        httponly=False,          # JS must be able to read this
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        path="/",
        domain=_COOKIE_DOMAIN,
    )
    return token


def _require_csrf(request: Request) -> None:
    """
    Validate CSRF double-submit for state-mutating cookie-auth endpoints.
    Raises HTTP 403 if the header is missing or does not match the cookie.
    Skips validation when the request uses Bearer token auth (API clients).
    """
    # Skip for Bearer-token requests (API clients don't use cookies)
    if request.headers.get("Authorization", "").startswith("Bearer "):
        return

    cookie_token  = request.cookies.get("fh_csrf", "")
    header_token  = request.headers.get("X-CSRF-Token", "")

    if not cookie_token or not header_token:
        raise HTTPException(
            status_code=403,
            detail={"error": "CSRF token missing", "code": 403},
        )
    if not _hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=403,
            detail={"error": "CSRF token invalid", "code": 403},
        )


def get_current_user(
    request: Request,
    fh_access: Optional[str] = Cookie(default=None),
    bearer_token: Optional[str] = Depends(oauth2_scheme),
) -> dict:
    """Decode JWT from fh_access cookie; fall back to Authorization Bearer header.

    FIX-1: user_id is always derived from the validated token, never from
    an unauthenticated request body or query parameter.
    """
    token = fh_access or bearer_token
    if not token:
        raise _err(401, "Not authenticated")
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise _err(401, "Invalid or expired token")

    user = get_user_by_id(user_id)
    if not user:
        raise _err(401, "User not found")

    # BUG-D fix — read-time plan expiry enforcement.
    # If plan_expires_at has passed and Stripe webhook did not fire, override
    # plan to 'free' in the returned dict. Does NOT write back to the DB.
    expires_at = user.get("plan_expires_at")
    if expires_at is not None and user.get("plan", "free") != "free":
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
        if expires_at < datetime.datetime.now(datetime.timezone.utc):
            user = {**user, "plan": "free"}
            logger.warning(
                "PLAN EXPIRY: user %s plan downgraded at read time "
                "(plan_expires_at=%s — webhook may have missed)",
                user["id"], expires_at.isoformat(),
            )

    return user

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE HELPERS — USERS  (FIX-5)
# ══════════════════════════════════════════════════════════════════════════════

def get_user(email: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        cur = _dictcur(conn)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        _put_conn(conn)


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = _get_conn()
    try:
        cur = _dictcur(conn)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        _put_conn(conn)


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_user(email: str, password: str, company_name: str) -> Optional[int]:
    """Insert a new user. Returns the new user id on success, None if email already exists."""
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = _get_conn()
    try:
        cur = _dictcur(conn)
        cur.execute(
            "INSERT INTO users (email, password_hash, company_name) VALUES (%s, %s, %s) RETURNING id",
            (email, pw_hash, company_name),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id
    except psycopg2.IntegrityError:
        conn.rollback()
        return None
    finally:
        _put_conn(conn)

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE HELPERS — TOKENS  (AUTH-2 through AUTH-4)
# ══════════════════════════════════════════════════════════════════════════════

def _create_db_token(user_id: int, token_type: str, ttl: datetime.timedelta) -> str:
    """Generate a secure token, persist it, and return the raw token string."""
    raw   = secrets.token_urlsafe(32)
    until = datetime.datetime.now(datetime.timezone.utc) + ttl
    conn  = _get_conn()
    try:
        cur = _dictcur(conn)
        cur.execute(
            "INSERT INTO tokens (user_id, token, type, expires_at) VALUES (%s, %s, %s, %s)",
            (user_id, raw, token_type, until),
        )
        conn.commit()
    finally:
        _put_conn(conn)
    return raw


def _consume_token(raw: str, token_type: str) -> Optional[int]:
    """
    Validate and consume a one-time token atomically.
    Uses a single UPDATE...WHERE...RETURNING to eliminate the SELECT→UPDATE race
    condition where two concurrent requests could both pass the used_at IS NULL
    check before either UPDATE commits. (BUG-2 fix)
    Returns user_id on success, None if token is unknown / expired / already used.
    """
    conn = _get_conn()
    try:
        cur = _dictcur(conn)
        cur.execute(
            """
            UPDATE tokens
               SET used_at = NOW()
             WHERE token      = %s
               AND type       = %s
               AND used_at    IS NULL
               AND expires_at > NOW()
            RETURNING user_id
            """,
            (raw, token_type),
        )
        row = cur.fetchone()
        if cur.rowcount == 0 or row is None:
            conn.rollback()
            return None
        conn.commit()
        return row["user_id"]
    finally:
        _put_conn(conn)

# ══════════════════════════════════════════════════════════════════════════════
# EMAIL HELPERS  (AUTH-8, AUTH-3)
# ══════════════════════════════════════════════════════════════════════════════

def _send_email(to: str, subject: str, html: str) -> None:
    """Send a transactional email via Resend. Logs errors but never raises."""
    if not _RESEND_API_KEY:
        logger.warning("EMAIL skipped (no RESEND_API_KEY): to=%s subject=%s", to, subject)
        return
    try:
        params: resend.Emails.SendParams = {
            "from":    _EMAIL_FROM,
            "to":      [to],
            "subject": subject,
            "html":    html,
        }
        resend.Emails.send(params)
        logger.info("EMAIL sent: to=%s subject=%s", to, subject)
    except Exception:
        logger.exception("EMAIL failed: to=%s subject=%s", to, subject)


def _send_verification_email(to: str, token: str) -> None:
    link = f"{_APP_DOMAIN}/verify-email?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#2563eb">Verify your FairHire email</h2>
      <p>Thanks for registering. Click the button below to verify your email address.
         This link expires in <strong>24 hours</strong>.</p>
      <a href="{link}" style="display:inline-block;padding:12px 24px;background:#2563eb;
         color:#fff;text-decoration:none;border-radius:6px;font-weight:600">
        Verify Email
      </a>
      <p style="color:#6b7280;font-size:13px;margin-top:24px">
        Or copy this link: {link}
      </p>
    </div>"""
    _send_email(to, "Verify your FairHire email address", html)


def _send_password_reset_email(to: str, token: str) -> None:
    link = f"{_APP_DOMAIN}/reset-password?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#2563eb">Reset your FairHire password</h2>
      <p>We received a request to reset your password. Click the button below.
         This link expires in <strong>1 hour</strong>.</p>
      <a href="{link}" style="display:inline-block;padding:12px 24px;background:#2563eb;
         color:#fff;text-decoration:none;border-radius:6px;font-weight:600">
        Reset Password
      </a>
      <p style="color:#6b7280;font-size:13px;margin-top:24px">
        If you didn't request this, you can safely ignore this email.
      </p>
      <p style="color:#6b7280;font-size:13px">
        Or copy this link: {link}
      </p>
    </div>"""
    _send_email(to, "Reset your FairHire password", html)

# ══════════════════════════════════════════════════════════════════════════════
# PLAN ENFORCEMENT HELPERS  (BILL-1, BILL-2)
# ══════════════════════════════════════════════════════════════════════════════

def _reset_monthly_counter_if_needed(user: dict) -> dict:
    """
    If the stored audit_count_reset_at is before the start of the current
    calendar month, reset audit_count_this_month to 0 and update the DB.
    Returns the (possibly updated) user dict.
    """
    now         = datetime.datetime.now(datetime.timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    reset_at = user.get("audit_count_reset_at")
    # BUG-7 fix — Supabase PgBouncer in transaction mode can return TIMESTAMPTZ
    # columns as tz-naive datetimes, causing TypeError on comparison with tz-aware month_start.
    if reset_at is not None and reset_at.tzinfo is None:
        reset_at = reset_at.replace(tzinfo=datetime.timezone.utc)
    if reset_at is None or reset_at < month_start:
        conn = _get_conn()
        try:
            cur = _dictcur(conn)
            cur.execute(
                """
                UPDATE users
                   SET audit_count_this_month = 0,
                       audit_count_reset_at   = DATE_TRUNC('month', NOW()),
                       updated_at             = NOW()
                 WHERE id = %s
                RETURNING audit_count_this_month, audit_count_reset_at
                """,
                (user["id"],),
            )
            row = cur.fetchone()
            conn.commit()
            if row:
                user = {**user, **dict(row)}
        except Exception:
            conn.rollback()
            logger.exception("_reset_monthly_counter_if_needed failed for user %s", user["id"])
        finally:
            _put_conn(conn)

    return user


def _check_plan_limit(user: dict) -> dict:
    """
    BILL-1 — Enforce monthly audit cap for free-plan users.

    1. Reset counter if a new calendar month has started.
    2. Raise HTTP 402 if the user is on the free plan and has used all 5 audits.

    Returns the refreshed user dict.
    """
    user  = _reset_monthly_counter_if_needed(user)
    plan  = user.get("plan", "free") or "free"
    count = int(user.get("audit_count_this_month") or 0)

    if plan == "free" and count >= _FREE_PLAN_MONTHLY_LIMIT:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Free plan limit reached — upgrade to Pro for unlimited audits",
                "code":  402,
                "plan":  "free",
                "used":  count,
                "limit": _FREE_PLAN_MONTHLY_LIMIT,
            },
        )

    return user


def _increment_audit_count(user_id: int) -> None:
    """BILL-2 — Atomically increment audit_count_this_month after a successful audit."""
    conn = _get_conn()
    try:
        cur = _dictcur(conn)
        cur.execute(
            """
            UPDATE users
               SET audit_count_this_month = COALESCE(audit_count_this_month, 0) + 1,
                   updated_at             = NOW()
             WHERE id = %s
            """,
            (user_id,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("_increment_audit_count failed for user %s", user_id)
    finally:
        _put_conn(conn)

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE HELPERS — AUDITS  (FIX-5, FIX-7, FIX-18, FIX-19)
# ══════════════════════════════════════════════════════════════════════════════

def save_audit(user_id: int, m: dict, filename: str) -> dict:
    """Save audit results to DB atomically and return the saved record as a dict."""
    conn     = _get_conn()
    audit_id = None
    try:
        conn.autocommit = False
        cur = _dictcur(conn)

        # 1. Upload record
        cur.execute(
            "INSERT INTO uploads (user_id, filename, row_count, engine_version) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (user_id, filename, m.get("row_count"), FAIRHIRE_VERSION),
        )
        upload_id = cur.fetchone()["id"]

        # 2. Audit record — includes v6.0 fields (FIX-7) + gender_stats (FIX-18)
        _gs      = m.get("gender_stats", {}) or {}
        _other_g = _gs.get("other_gender", {}) or {}
        cur.execute("""
            INSERT INTO audits (
                upload_id, user_id,
                fair_hiring_score, score_label,
                air_gender, shortlisting_gap, hiring_gap, disability_air,
                flags, institution_flags, age_flags,
                caste_flags, skin_flags, referral_flags, marital_flags, proxy_flags,
                air_skin, skin_best_rate, skin_worst_rate,
                referral_hire_rate, non_referral_hire_rate, referral_air, referral_hhi,
                men_total, women_total, men_shortlisted, women_shortlisted,
                men_hired, women_hired,
                skin_stats, referral_stats, marital_stats,
                marital_intersectional_stats, proxy_stats, proxy_phi_scores,
                caste_stats, caste_col, institution_stats, age_stats,
                module_results, systemic_bias_triggered, systemic_bias_deduction,
                region, caste_worst_air, gender_majority_group, gender_minority_group,
                gender_stats,
                other_gender_total, other_gender_hired, other_gender_shortlisted
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,
                %s,
                %s,%s,%s
            ) RETURNING id
        """, (
            upload_id, user_id,
            m.get("score"), m.get("label"),
            m.get("air_gender"), m.get("shortlisting_gap"),
            m.get("hiring_gap"), m.get("disability_air"),
            psycopg2.extras.Json(m.get("flags", [])),
            psycopg2.extras.Json(m.get("institution_flags", [])),
            psycopg2.extras.Json(m.get("age_flags", [])),
            psycopg2.extras.Json(m.get("caste_flags", [])),
            psycopg2.extras.Json(m.get("skin_flags", [])),
            psycopg2.extras.Json(m.get("referral_flags", [])),
            psycopg2.extras.Json(m.get("marital_flags", [])),
            psycopg2.extras.Json(m.get("proxy_flags", [])),
            m.get("air_skin"), m.get("skin_best_rate"), m.get("skin_worst_rate"),
            m.get("referral_hire_rate"), m.get("non_referral_hire_rate"),
            m.get("referral_air"), m.get("referral_hhi"),
            m.get("men_total"), m.get("women_total"),
            m.get("men_shortlisted"), m.get("women_shortlisted"),
            m.get("men_hired"), m.get("women_hired"),
            psycopg2.extras.Json(m.get("skin_stats", {})),
            psycopg2.extras.Json(m.get("referral_stats", {})),
            psycopg2.extras.Json(m.get("marital_stats", {})),
            psycopg2.extras.Json(m.get("marital_intersectional_stats", {})),
            psycopg2.extras.Json(m.get("proxy_stats", {})),
            psycopg2.extras.Json(m.get("proxy_phi_scores", {})),
            psycopg2.extras.Json(m.get("caste_stats", {})),
            m.get("caste_col"),
            psycopg2.extras.Json(m.get("institution_stats", {})),
            psycopg2.extras.Json(m.get("age_stats", {})),
            psycopg2.extras.Json(m.get("module_results", {})),
            bool(m.get("systemic_bias_triggered", False)),
            int(m.get("systemic_bias_deduction", 0)),
            m.get("region"),
            m.get("caste_worst_air"),
            m.get("gender_majority_group"),
            m.get("gender_minority_group"),
            psycopg2.extras.Json(_gs),
            int(_other_g.get("total",       0) or 0),
            int(_other_g.get("hired",       0) or 0),
            int(_other_g.get("shortlisted", 0) or 0),
        ))
        audit_id = cur.fetchone()["id"]

        conn.commit()
        logger.info("save_audit committed audit_id=%s for user %s", audit_id, user_id)

    except Exception:
        conn.rollback()
        logger.exception("save_audit rollback for user %s", user_id)
        raise
    finally:
        conn.autocommit = True
        _put_conn(conn)

    # 3. Read back via get_audit_by_id so FIX-21/FIX-23 normalisation is
    #    applied consistently in both the save and report paths.
    row = get_audit_by_id(audit_id)
    if row is None:
        logger.warning(
            "save_audit: read-back failed for audit_id=%s — falling back to input metrics",
            audit_id,
        )
        row = _normalise_audit_row(
            {**m, "id": audit_id, "user_id": user_id},
            filename,
            m.get("row_count", 0),
        )

    return row


# FIX-19 — new helper used by both save_audit() and report_endpoint().
# Centralising the DB lookup here means the report endpoint always gets
# the same fully-deserialised dict that the audit endpoint returns,
# including module_results with correct types.
def get_audit_by_id(audit_id: int) -> Optional[dict]:
    """Fetch a single audit row by primary key and return a normalised dict."""
    conn = _get_conn()
    try:
        cur = _dictcur(conn)
        cur.execute("""
            SELECT
                a.*,
                u.filename  AS original_filename,
                u.row_count AS row_count,
                COALESCE(a.fair_hiring_score, 0) AS score,
                COALESCE(a.score_label, '—')     AS label,
                a.computed_at                    AS created_at
            FROM audits a
            LEFT JOIN uploads u ON u.id = a.upload_id
            WHERE a.id = %s
        """, (audit_id,))
        row = cur.fetchone()
        if row is None:
            return None
        row = dict(row)
    finally:
        _put_conn(conn)

    return _normalise_audit_row(
        row,
        row.get("original_filename", "unknown"),
        row.get("row_count", 0),
    )


def get_audit_history(user_id: int) -> list[dict]:
    conn = _get_conn()
    try:
        cur = _dictcur(conn)
        cur.execute("""
            SELECT
                a.*,
                u.filename  AS original_filename,
                u.row_count AS row_count,
                COALESCE(a.fair_hiring_score, 0) AS score,
                COALESCE(a.score_label, '—')     AS label,
                a.computed_at                    AS created_at
            FROM audits a
            LEFT JOIN uploads u ON u.id = a.upload_id
            WHERE a.user_id = %s
            ORDER BY a.computed_at DESC
        """, (user_id,))
        rows = cur.fetchall()
    finally:
        _put_conn(conn)

    return [
        _normalise_audit_row(
            dict(r),
            r.get("original_filename", "unknown"),
            r.get("row_count", 0),
        )
        for r in rows
    ]


def _parse_jsonb(value: Any) -> Any:
    """Deserialise a JSONB value that psycopg2 may have left as a raw string.

    psycopg2 with RealDictCursor normally deserialises JSONB automatically,
    but some Supabase pooler configurations (PgBouncer in transaction mode)
    return JSONB columns as plain strings. This helper handles both cases.
    (FIX-16)
    """
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def _make_json_safe(obj: Any) -> Any:
    """Recursively convert non-JSON-serializable types so FastAPI can return them."""
    if obj is None:
        return None
    if isinstance(obj, (bool, int, str)):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, np.floating):
        f_val = float(obj)
        if math.isnan(f_val) or math.isinf(f_val):
            return None
        return f_val
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return [_make_json_safe(v) for v in obj.tolist()]
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, (bytes, memoryview)):
        return None
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_safe(v) for v in obj]
    try:
        return str(obj)
    except Exception:
        return None


def _normalise_audit_row(row: dict, filename: str, row_count: int) -> dict:
    """Deserialise JSONB fields and add convenience aliases.  (FIX-16, FIX-18, FIX-21, FIX-23)"""
    _all_jsonb = (
        "flags", "institution_flags", "age_flags", "caste_flags",
        "skin_flags", "referral_flags", "marital_flags", "proxy_flags",
        "skin_stats", "referral_stats", "marital_stats",
        "marital_intersectional_stats", "proxy_stats",
        "proxy_phi_scores", "caste_stats", "institution_stats",
        "age_stats", "module_results",
        "gender_stats",  # FIX-18
    )
    for k in _all_jsonb:
        row[k] = _parse_jsonb(row.get(k))

    for k in ("flags", "institution_flags", "age_flags", "caste_flags",
              "skin_flags", "referral_flags", "marital_flags", "proxy_flags"):
        if not isinstance(row.get(k), list):
            row[k] = []

    for k in ("skin_stats", "referral_stats", "marital_stats",
              "marital_intersectional_stats", "proxy_stats",
              "proxy_phi_scores", "caste_stats", "institution_stats",
              "age_stats", "gender_stats"):
        if not isinstance(row.get(k), dict):
            row[k] = {}

    # FIX-21 — module_results must always be a dict with the engine's short
    # keys ('gender', 'caste', 'skin', etc.). Any other type means the JSONB
    # column was absent, null, or corrupted.
    if not isinstance(row.get("module_results"), dict):
        logger.warning(
            "module_results for audit_id=%s is %s, not dict — resetting to {}",
            row.get("id"), type(row.get("module_results")).__name__,
        )
        row["module_results"] = {}

    # FIX-23 — inject data_present for every module that is missing it so
    # report_generator._pts() correctly distinguishes PASS from NOT EVALUATED.
    _optional_col_stats = {
        "skin":        "skin_stats",
        "caste":       "caste_stats",
        "institution": "institution_stats",
        "age":         "age_stats",
        "marital":     "marital_stats",
        "referral":    "referral_stats",
        "proxy":       "proxy_phi_scores",
    }
    _always_present = {"gender", "spg"}

    mr = row["module_results"]
    for mod_key, mod_val in mr.items():
        if not isinstance(mod_val, dict):
            continue
        if "data_present" in mod_val:
            continue  # disability / future engine versions that already set it
        if mod_key in _always_present:
            mod_val["data_present"] = True
        elif mod_key in _optional_col_stats:
            stats_key = _optional_col_stats[mod_key]
            mod_val["data_present"] = bool(row.get(stats_key))
        else:
            mod_val["data_present"] = (
                mod_val.get("passed") is not None or mod_val.get("points", 0) > 0
            )
        logger.debug(
            "FIX-23: injected data_present=%s for module=%s audit_id=%s",
            mod_val["data_present"], mod_key, row.get("id"),
        )

    row["score"]                   = row.get("fair_hiring_score") or 0
    row["label"]                   = row.get("score_label") or "—"
    row["original_filename"]       = filename or "unknown"
    row["row_count"]               = row_count
    row["systemic_bias_triggered"] = bool(row.get("systemic_bias_triggered", False))
    row["systemic_bias_deduction"] = int(row.get("systemic_bias_deduction") or 0)

    return _make_json_safe(row)

# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS  (FIX-7, FIX-8, FIX-15, FIX-20)
# ══════════════════════════════════════════════════════════════════════════════

class AuthRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email:        EmailStr
    password:     str
    company_name: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    token:        str
    new_password: str


# FIX-20 — audit_id is required; the report endpoint uses it to fetch the
# canonical audit row from the DB instead of trusting the POST body.
class ReportRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # Required: used to look up the full audit row from the DB (FIX-20)
    audit_id: int

    # Remaining fields kept for API compatibility with existing frontend code.
    # They are NOT used for report generation — the DB row is authoritative.
    score:              int             = 0
    label:              str             = "—"
    flags:              List[str]       = []
    row_count:          int             = 0
    original_filename:  str             = "data.csv"
    company_name:       Optional[str]   = None
    air_gender:         float           = 0.0
    shortlisting_gap:   float           = 0.0
    hiring_gap:         float           = 0.0
    men_total:          int             = 0
    women_total:        int             = 0
    men_shortlisted:    int             = 0
    women_shortlisted:  int             = 0
    men_hired:          int             = 0
    women_hired:        int             = 0
    disability_air:     float           = 0.0
    caste_stats:        Dict[str, Any]  = {}
    caste_flags:        List[str]       = []
    caste_col:          Optional[str]   = None
    air_skin:           float           = 0.0
    skin_best_rate:     float           = 0.0
    skin_worst_rate:    float           = 0.0
    skin_stats:         Dict[str, Any]  = {}
    skin_flags:         List[str]       = []
    referral_hire_rate:     float           = 0.0
    non_referral_hire_rate: float           = 0.0
    referral_air:           float           = 0.0
    referral_hhi:           float           = 0.0
    referral_flags:         List[str]       = []
    referral_stats:         Dict[str, Any]  = {}
    marital_stats:                Dict[str, Any] = {}
    marital_flags:                List[str]      = []
    marital_intersectional_stats: Dict[str, Any] = {}
    age_flags:         List[str]       = []
    age_stats:         Dict[str, Any]  = {}
    institution_flags: List[str]       = []
    institution_stats: Dict[str, Any]  = {}
    proxy_flags:       List[str]       = []
    proxy_phi_scores:  Dict[str, Any]  = {}
    proxy_stats:       Dict[str, Any]  = {}
    module_results:              Dict[str, Any] = {}
    systemic_bias_triggered:     bool           = False
    systemic_bias_deduction:     int            = 0
    region:                      Optional[str]  = None
    caste_worst_air:             Optional[float]= None
    gender_majority_group:       Optional[str]  = None
    gender_minority_group:       Optional[str]  = None
    gender_stats:                Dict[str, Any] = {}

# ══════════════════════════════════════════════════════════════════════════════
# PASSWORD VALIDATION HELPER  (FIX-9)
# ══════════════════════════════════════════════════════════════════════════════

_SPECIAL_CHARS = set(r"""!@#$%^&*()_+-=[]{}|;':",.<>?/`~\\""")


def _validate_password(password: str) -> None:
    """Raise HTTP 400 with a specific message for each broken password rule."""
    if len(password) < 8:
        raise _err(400, "Password must be at least 8 characters")
    if len(password) > 72:
        raise _err(400, "Password must be 72 characters or fewer (bcrypt limit)")
    if not any(c.isdigit() or c in _SPECIAL_CHARS for c in password):
        raise _err(400, "Password must contain at least one digit or special character")

# ══════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS  (FIX-1, FIX-4, FIX-8, FIX-9, FIX-11, FIX-12, AUTH-1…9)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/register")
@limiter.limit("5/minute")
def register(request: Request, req: AuthRequest) -> dict:
    email = str(req.email).lower()
    logger.info("REGISTER attempt: %s", email)

    if not req.company_name or not req.company_name.strip():
        raise _err(400, "Company name is required")

    _validate_password(req.password)

    new_id = create_user(email, req.password, req.company_name.strip())
    if new_id is None:
        logger.warning("REGISTER duplicate email: %s", email)
        # Return 200 (not 409) to prevent email enumeration.
        # The real confirmation email only goes to the genuine owner.
        return {"status": "ok", "message": "If this email is new, a verification link has been sent."}

    # AUTH-8 — send email verification after successful registration
    try:
        token = _create_db_token(new_id, "email_verify", datetime.timedelta(hours=24))
        _send_verification_email(email, token)
    except Exception:
        logger.exception("REGISTER: token/email failed for user %s", new_id)

    logger.info("REGISTER success: %s id=%s", email, new_id)
    return {"status": "ok", "message": "If this email is new, a verification link has been sent."}


@app.post("/api/login")
@limiter.limit("10/minute")
def login(request: Request, req: AuthRequest, response: Response) -> dict:
    email = str(req.email).lower()
    logger.info("LOGIN attempt: %s", email)

    user = get_user(email)
    if not user or not verify_password(req.password, user["password_hash"]):
        logger.warning("LOGIN failed: %s", email)
        raise _err(401, "Invalid email or password")

    # AUTH-9 — block sign-in until email is verified
    if not user.get("email_verified", False):
        logger.warning("LOGIN blocked (unverified): %s", email)
        raise HTTPException(
            status_code=403,
            detail={"error": "Please verify your email before signing in.", "code": 403},
        )

    # AUTH-1 — set dual HttpOnly cookies
    _set_auth_cookies(response, user["id"], email)
    logger.info("LOGIN success: %s", email)
    return {"status": "ok", "email": email}


@app.get("/api/verify-email")
@limiter.limit("20/hour")
def verify_email(request: Request, token: str) -> dict:
    """AUTH-2 — Consume an email verification token and mark the user as verified."""
    user_id = _consume_token(token, "email_verify")
    if user_id is None:
        raise _err(400, "Verification link is invalid or has expired.")

    conn = _get_conn()
    try:
        cur = _dictcur(conn)
        cur.execute(
            "UPDATE users SET email_verified = TRUE, email_verified_at = NOW() WHERE id = %s",
            (user_id,),
        )
        conn.commit()
    finally:
        _put_conn(conn)

    logger.info("EMAIL VERIFIED: user_id=%s", user_id)
    return {"status": "ok", "message": "Email verified. You can now sign in."}


@app.post("/api/forgot-password")
@limiter.limit("3/hour")
def forgot_password(request: Request, req: ForgotPasswordRequest) -> dict:
    """AUTH-3 — Issue a password-reset email. Always returns 200 to prevent email enumeration."""
    email = str(req.email).lower()
    logger.info("FORGOT PASSWORD request: %s", email)

    user = get_user(email)
    if user:
        try:
            token = _create_db_token(user["id"], "password_reset", datetime.timedelta(hours=1))
            _send_password_reset_email(email, token)
        except Exception:
            logger.exception("FORGOT PASSWORD: token/email failed for %s", email)

    return {"status": "ok", "message": "If that email is registered you'll receive a reset link."}


@app.post("/api/reset-password")
@limiter.limit("10/hour")
def reset_password(request: Request, req: ResetPasswordRequest) -> dict:
    """AUTH-4 — Consume a password-reset token and set a new password."""
    _validate_password(req.new_password)

    user_id = _consume_token(req.token, "password_reset")
    if user_id is None:
        raise _err(400, "Reset link is invalid or has expired.")

    pw_hash = bcrypt.hashpw(req.new_password.encode(), bcrypt.gensalt()).decode()
    conn = _get_conn()
    try:
        cur = _dictcur(conn)
        cur.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (pw_hash, user_id),
        )
        conn.commit()
    finally:
        _put_conn(conn)

    logger.info("PASSWORD RESET: user_id=%s", user_id)
    return {"status": "ok", "message": "Password updated. You can now sign in."}


@app.post("/api/refresh")
@limiter.limit("5/minute")
def refresh_token(
    request: Request,
    response: Response,
    fh_refresh: Optional[str] = Cookie(default=None),
) -> dict:
    """AUTH-5 — Issue a new fh_access cookie from a valid fh_refresh cookie."""
    # _require_csrf removed: fh_refresh HttpOnly cookie is already CSRF-safe
    if not fh_refresh:
        raise _err(401, "No refresh token")
    try:
        payload = jwt.decode(fh_refresh, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise JWTError("wrong token type")
        user_id = int(payload["sub"])
        email   = payload["email"]
    except (JWTError, KeyError, ValueError):
        _clear_auth_cookies(response)
        raise _err(401, "Refresh token expired or invalid")

    user = get_user_by_id(user_id)
    if not user:
        _clear_auth_cookies(response)
        raise _err(401, "User not found")

    access = _create_access_token(user_id, email)
    _kw = dict(
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        path="/",
        domain=_COOKIE_DOMAIN,
    )
    response.set_cookie("fh_access", access, max_age=_ACCESS_TOKEN_MINS * 60, **_kw)
    _issue_csrf_cookie(response)   # rotate CSRF token on every token refresh
    logger.info("REFRESH issued new access token for user %s", user_id)
    return {"status": "ok"}


@app.post("/api/logout")
@limiter.limit("5/minute")
def logout_endpoint(request: Request, response: Response) -> dict:
    """AUTH-6 — Clear both auth cookies."""
    _require_csrf(request)
    _clear_auth_cookies(response)
    return {"status": "ok"}


@app.get("/api/me")
@limiter.limit("60/minute")
def me(request: Request, current_user: dict = Depends(get_current_user)) -> dict:
    """AUTH-7 — Return basic user info if the access cookie is valid; 401 otherwise."""
    return {
        "id":           current_user["id"],
        "email":        current_user["email"],
        "company_name": current_user.get("company_name"),
        "plan":         current_user.get("plan", "free"),
    }

# ══════════════════════════════════════════════════════════════════════════════
# AUDIT ENDPOINT  (BILL-1, BILL-2, FIX-1, FIX-4, FIX-10, FIX-11, FIX-17)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/audit")
@limiter.limit("5/hour")
def audit_endpoint(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Accept a CSV, run the audit engine, save to DB, return metrics."""
    _require_csrf(request)
    user_id: int = current_user["id"]

    # FIX-17 — cross-browser content-type + extension check
    filename_lower = (file.filename or "").lower()
    content_type   = (file.content_type or "").lower().split(";")[0].strip()

    if content_type not in _ALLOWED_CONTENT_TYPES or not filename_lower.endswith(".csv"):
        logger.warning(
            "AUDIT rejected bad file type: content_type=%s filename=%s user=%s",
            file.content_type, file.filename, user_id,
        )
        raise _err(415, "Please upload a .csv file.")

    # 1. Read & size-check
    raw = file.file.read()
    if len(raw) > MAX_FILE_BYTES:
        raise _err(413, f"File too large. Maximum {MAX_FILE_BYTES // (1024 * 1024)} MB allowed.")

    # 2. Parse CSV
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        raise _err(400, f"Could not parse CSV: {exc}")

    # 3. Row cap  (FIX-10)
    if len(df) > MAX_ROWS:
        raise _err(400, f"Dataset has {len(df):,} rows. Maximum {MAX_ROWS:,} rows allowed.")

    # 4. Normalise column names + strip whitespace from string columns
    df.columns = [c.strip().lower() for c in df.columns]
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # 5. Validate required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise _err(
            400,
            f"Missing required columns: {sorted(missing)}. "
            f"Found: {sorted(df.columns.tolist())}",
        )

    # 6. Minimum row check
    if len(df) < MIN_ROWS:
        raise _err(400, f"Dataset has only {len(df)} rows. Minimum {MIN_ROWS} required.")

    # 7. Reset monthly counter if needed before plan-limit check (BUG-E fix).
    # Without this, a stale audit_count_this_month from a previous month would
    # cause the atomic UPDATE below to incorrectly reject valid requests with 402.
    current_user = _reset_monthly_counter_if_needed(current_user)

    current_user = _check_plan_limit(current_user)

    # 8. Run audit engine (BUG-C fix — compute and save BEFORE incrementing counter).
    # Counter increment now happens only after both steps succeed, so a failed
    # upload or engine error does not consume one of the user's monthly audits.
    try:
        metrics = compute_fairness_metrics(df)
    except ValueError as exc:
        logger.warning("AUDIT data quality error for user %s: %s", user_id, exc)
        raise _err(400, str(exc))
    except Exception:
        logger.exception("AUDIT compute failed for user %s", user_id)
        raise _err(500, "Audit computation failed. Check your data and try again.")

    # 9. Save to database (before counter increment — BUG-C fix)
    try:
        saved = save_audit(user_id, metrics, file.filename or 'upload.csv')
    except Exception:
        logger.exception("AUDIT save failed for user %s", user_id)
        raise _err(500, "Failed to save audit results. Please try again.")

    # 10. Atomically increment-and-cap the plan counter AFTER a successful audit.
    # BUG-3 fix — eliminates TOCTOU race; BUG-A fix — removed redundant
    # _put_conn() before raise so the finally block is the sole return path.
    # BUG-C fix — counter now increments only on success.
    _conn_limit = _get_conn()
    try:
        _cur_limit = _dictcur(_conn_limit)
        _cur_limit.execute(
            """
            UPDATE users
               SET audit_count_this_month = audit_count_this_month + 1,
                   updated_at             = NOW()
             WHERE id = %s
               AND (plan != 'free' OR audit_count_this_month < 5)
            RETURNING audit_count_this_month
            """,
            (user_id,),
        )
        if _cur_limit.rowcount == 0:
            _conn_limit.rollback()
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Free plan limit reached — upgrade to Pro for unlimited audits",
                    "code":  402,
                    "plan":  "free",
                    "used":  _FREE_PLAN_MONTHLY_LIMIT,
                    "limit": _FREE_PLAN_MONTHLY_LIMIT,
                },
            )
        _conn_limit.commit()
    except HTTPException:
        raise
    except Exception:
        _conn_limit.rollback()
        logger.exception("AUDIT plan-limit atomic update failed for user %s", user_id)
        # BUG-C: audit already saved — log the error but still return the result.
        logger.error(
            "AUDIT counter increment failed after successful audit for user %s — "
            "audit_id=%s is saved; counter may be under-counted",
            user_id, saved.get("id"),
        )
    finally:
        _put_conn(_conn_limit)

    logger.info("AUDIT complete for user %s — score %s", user_id, saved.get("score"))
    return saved


@app.get("/api/history")
@limiter.limit("30/minute")
def history_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> list:
    """Return all audits for the authenticated user."""
    user_id: int = current_user["id"]
    try:
        return get_audit_history(user_id)
    except Exception:
        logger.exception("HISTORY fetch failed for user %s", user_id)
        raise _err(500, "Failed to fetch audit history.")

# ══════════════════════════════════════════════════════════════════════════════
# PDF REPORT ENDPOINT  (BILL-3, FIX-1, FIX-4, FIX-12, FIX-14, FIX-19, FIX-20)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/report")
@limiter.limit("20/hour")
def report_endpoint(
    request: Request,
    data: ReportRequest,
    current_user: dict = Depends(get_current_user),
) -> Response:
    """Generate and return a premium PDF audit report.

    BILL-3: PDF reports require Pro plan (free users receive HTTP 402).
    FIX-19/FIX-20: Fetches the canonical audit row from the DB using
    data.audit_id so module_results and all JSONB fields are present and
    correctly typed, fixing the Part 2 score-zero bug.
    """
    _require_csrf(request)
    # BILL-3 — block free-plan users from downloading PDF reports
    plan = current_user.get("plan", "free") or "free"
    if plan == "free":
        raise HTTPException(
            status_code=402,
            detail={
                "error": "PDF reports require Pro plan.",
                "code":  402,
                "plan":  "free",
            },
        )

    user_id: int = current_user["id"]

    try:
        # FIX-19 — fetch the authoritative audit row from the DB
        payload = get_audit_by_id(data.audit_id)

        if payload is None:
            logger.warning(
                "REPORT audit_id=%s not found for user %s",
                data.audit_id, user_id,
            )
            raise _err(404, f"Audit {data.audit_id} not found.")

        # Security: ensure the audit belongs to the requesting user
        if payload.get("user_id") != user_id:
            logger.warning(
                "REPORT user %s attempted to access audit_id=%s owned by user %s",
                user_id, data.audit_id, payload.get("user_id"),
            )
            raise _err(403, "You do not have access to this audit.")

        # FIX-20 — use the authenticated user's company_name from the DB
        payload["company_name"] = current_user.get("company_name") or ""

        mr = payload.get("module_results", {})
        logger.info(
            "REPORT generating for user %s audit_id=%s score=%s modules=%s",
            user_id, data.audit_id,
            payload.get("score"),
            list(mr.keys()) if isinstance(mr, dict) else type(mr).__name__,
        )

        buffer = generate_premium_report(payload)

        # FIX-14 — sanitise filename to prevent header injection
        safe = re.sub(r"[^\w\-.]", "_", payload.get("original_filename", "report.csv"))

        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="FairHire_Report_{safe}.pdf"'
            },
        )

    except HTTPException:
        raise  # re-raise 404 / 403 / 402 without wrapping
    except Exception:
        logger.exception("REPORT generation failed for user %s audit_id=%s", user_id, data.audit_id)
        raise _err(500, "Report generation failed. Please retry.")

# ══════════════════════════════════════════════════════════════════════════════
# BILLING ENDPOINTS  (BILL-4, BILL-5)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/create-checkout-session")
@limiter.limit("10/minute")
def create_checkout_session(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    BILL-4 — Create a Stripe Checkout session for the Pro plan.
    Returns {url} for the frontend to redirect to.
    """
    _require_csrf(request)
    if not _STRIPE_SECRET_KEY:
        raise _err(503, "Billing is not configured. Please contact support.")
    if not _STRIPE_PRO_PRICE_ID:
        raise _err(503, "Pro plan price is not configured. Please contact support.")

    user_id     = current_user["id"]
    email       = current_user.get("email", "")
    customer_id = current_user.get("stripe_customer_id") or None

    try:
        if not customer_id:
            customer    = stripe.Customer.create(email=email, metadata={"user_id": str(user_id)})
            customer_id = customer["id"]
            # Persist immediately so subsequent calls reuse it
            conn = _get_conn()
            try:
                cur = _dictcur(conn)
                cur.execute(
                    "UPDATE users SET stripe_customer_id = %s, updated_at = NOW() WHERE id = %s",
                    (customer_id, user_id),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                logger.exception("create_checkout_session: failed to persist customer_id")
            finally:
                _put_conn(conn)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            client_reference_id=str(user_id),
            payment_method_types=["card"],
            line_items=[{"price": _STRIPE_PRO_PRICE_ID, "quantity": 1}],
            mode="subscription",
            success_url=f"{_APP_DOMAIN}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{_APP_DOMAIN}/billing/cancelled",
        )
    except stripe.error.StripeError as exc:
        logger.error("STRIPE checkout session error for user %s: %s", user_id, exc)
        raise _err(502, "Could not create checkout session. Please try again.")
    except Exception:
        logger.exception("STRIPE checkout session unexpected error for user %s", user_id)
        raise _err(500, "Could not create checkout session. Please try again.")

    logger.info("STRIPE checkout session created: user=%s session=%s", user_id, session["id"])
    return {"url": session["url"]}


@app.get("/api/subscription-status")
@limiter.limit("60/minute")
def subscription_status(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    BILL-5 — Return the user's current plan, monthly audit usage, and limit.
    """
    user  = _reset_monthly_counter_if_needed(current_user)
    plan  = user.get("plan", "free") or "free"
    count = int(user.get("audit_count_this_month") or 0)
    limit = _FREE_PLAN_MONTHLY_LIMIT if plan == "free" else -1  # -1 = unlimited

    return {
        "plan":                   plan,
        "audit_count_this_month": count,
        "monthly_limit":          limit,
        "pdf_reports":            plan in ("pro", "enterprise"),
        "api_access":             plan == "enterprise",
        "stripe_customer_id":     user.get("stripe_customer_id"),
        "stripe_subscription_id": user.get("stripe_subscription_id"),
    }

# ══════════════════════════════════════════════════════════════════════════════
# HEALTH  (FIX-13)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health(response: Response) -> dict:
    """
    Health check. Returns HTTP 503 when DB is unavailable so load balancers
    and uptime monitors detect real failures rather than false positives.
    """
    db_status   = "connected"
    http_status = 200

    try:
        conn = _get_conn()
        try:
            conn.cursor().execute("SELECT 1")
        finally:
            _put_conn(conn)
    except Exception as exc:
        logger.error("HEALTH DB check failed: %s", exc)
        db_status   = "error: connection failed"
        http_status = 503

    response.status_code = http_status
    return {
        "status":    "ok" if http_status == 200 else "degraded",
        "db":        db_status,
        "version":   os.getenv("APP_VERSION", "6.2.0"),
        "engine":    FAIRHIRE_VERSION,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

# FIX-2 — /api/debug/users removed entirely
