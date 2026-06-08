"""
stripe_webhook.py  ·  FairHire v2.2
════════════════════════════════════════════════════════════════════════════════
Stripe webhook handler mounted into the main FastAPI app.

Handles:
  • checkout.session.completed   → set plan='pro', store stripe IDs
  • customer.subscription.deleted → downgrade to plan='free'
  • invoice.payment_failed        → send warning email to customer

Mount in api.py:
    from stripe_webhook import router as stripe_router
    app.include_router(stripe_router)

Required env vars (already in .env):
    STRIPE_SECRET_KEY      sk_live_... or sk_test_...
    STRIPE_WEBHOOK_SECRET  whsec_...
════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
import os

import stripe
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger("fairhire.stripe")

# ── Stripe SDK init ───────────────────────────────────────────────────────────
_STRIPE_SECRET_KEY      = os.getenv("STRIPE_SECRET_KEY", "")
_STRIPE_WEBHOOK_SECRET  = os.getenv("STRIPE_WEBHOOK_SECRET", "")
_STRIPE_PRO_PRICE_ID    = os.getenv("STRIPE_PRO_PRICE_ID", "")   # e.g. price_xxx
_APP_DOMAIN             = os.getenv("APP_DOMAIN", "https://your-domain.com")

if not _STRIPE_SECRET_KEY:
    logger.warning("STRIPE_SECRET_KEY is not set — Stripe features are disabled")

stripe.api_key = _STRIPE_SECRET_KEY

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_conn_and_helpers():
    """
    Import DB helpers lazily to avoid a circular import.
    stripe_webhook.py is imported by api.py, which defines _get_conn etc.
    We import from api at call time, not at module load time.
    """
    from api import _get_conn, _put_conn, _dictcur, _send_email  # noqa: PLC0415
    return _get_conn, _put_conn, _dictcur, _send_email


def _set_user_plan(
    *,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    plan: str,
    plan_expires_at=None,
) -> None:
    """Update a user's plan and Stripe IDs by customer ID."""
    _get_conn, _put_conn, _dictcur, _ = _get_conn_and_helpers()
    conn = _get_conn()
    try:
        cur = _dictcur(conn)
        cur.execute(
            """
            UPDATE users
               SET plan                   = %s,
                   stripe_customer_id     = %s,
                   stripe_subscription_id = %s,
                   plan_expires_at        = COALESCE(%s, plan_expires_at),
                   updated_at             = NOW()
             WHERE stripe_customer_id = %s
                OR stripe_subscription_id = %s
            """,
            (plan, stripe_customer_id, stripe_subscription_id, plan_expires_at,
             stripe_customer_id, stripe_subscription_id),
        )
        if cur.rowcount == 0:
            # Fallback: look up by customer ID only (new subscription flow)
            cur.execute(
                """
                UPDATE users
                   SET plan                   = %s,
                       stripe_customer_id     = %s,
                       stripe_subscription_id = %s,
                       plan_expires_at        = COALESCE(%s, plan_expires_at),
                       updated_at             = NOW()
                 WHERE stripe_customer_id = %s
                """,
                (plan, stripe_customer_id, stripe_subscription_id, plan_expires_at, stripe_customer_id),
            )
        conn.commit()
        logger.info(
            "STRIPE plan updated: customer=%s sub=%s plan=%s rows=%s",
            stripe_customer_id, stripe_subscription_id, plan, cur.rowcount,
        )
    except Exception:
        conn.rollback()
        logger.exception("STRIPE _set_user_plan failed")
        raise
    finally:
        _put_conn(conn)


def _downgrade_by_subscription(stripe_subscription_id: str) -> None:
    """Set plan='free' when a subscription is deleted/cancelled."""
    _get_conn, _put_conn, _dictcur, _ = _get_conn_and_helpers()
    conn = _get_conn()
    try:
        cur = _dictcur(conn)
        cur.execute(
            """
            UPDATE users
               SET plan                   = 'free',
                   stripe_subscription_id = NULL,
                   plan_expires_at        = COALESCE(%s, plan_expires_at),
                   updated_at             = NOW()
             WHERE stripe_subscription_id = %s
            """,
            (None, stripe_subscription_id),
        )
        conn.commit()
        logger.info(
            "STRIPE downgrade to free: sub=%s rows=%s",
            stripe_subscription_id, cur.rowcount,
        )
    except Exception:
        conn.rollback()
        logger.exception("STRIPE _downgrade_by_subscription failed")
        raise
    finally:
        _put_conn(conn)


def _get_customer_email(stripe_customer_id: str) -> str | None:
    """Return the email stored against a Stripe customer ID in our DB."""
    _get_conn, _put_conn, _dictcur, _ = _get_conn_and_helpers()
    conn = _get_conn()
    try:
        cur = _dictcur(conn)
        cur.execute(
            "SELECT email FROM users WHERE stripe_customer_id = %s",
            (stripe_customer_id,),
        )
        row = cur.fetchone()
        return row["email"] if row else None
    finally:
        _put_conn(conn)


def _send_payment_failed_email(customer_email: str) -> None:
    _, _, _, _send_email = _get_conn_and_helpers()
    html = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
      <h2 style="color:#dc2626">FairHire — Payment Failed</h2>
      <p>We were unable to process your most recent payment for your FairHire Pro subscription.</p>
      <p>To keep your Pro features active, please update your payment method:</p>
      <a href="{_APP_DOMAIN}/billing"
         style="display:inline-block;padding:12px 24px;background:#2563eb;
                color:#fff;text-decoration:none;border-radius:6px;font-weight:600">
        Update Payment Method
      </a>
      <p style="color:#6b7280;font-size:13px;margin-top:24px">
        If payment is not received within 7 days your account will be downgraded
        to the Free plan (5 audits/month, no PDF reports).
      </p>
    </div>
    """
    _send_email(customer_email, "FairHire — Action required: payment failed", html)


# ── Webhook endpoint ──────────────────────────────────────────────────────────

@router.post("/api/stripe/webhook")
async def stripe_webhook(request: Request) -> dict:
    """
    Verify Stripe signature and dispatch to the appropriate handler.
    Stripe requires the raw request body for signature verification — do NOT
    use request.json() here, which parses and re-encodes the body.
    """
    if not _STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET not set — rejecting webhook")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, _STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError as exc:
        logger.warning("STRIPE invalid signature: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as exc:
        logger.exception("STRIPE webhook parse error: %s", exc)
        raise HTTPException(status_code=400, detail="Webhook parse error")

    event_type = event["type"]
    data_obj   = event["data"]["object"]
    logger.info("STRIPE event received: %s id=%s", event_type, event["id"])

    # ── checkout.session.completed ────────────────────────────────────────────
    if event_type == "checkout.session.completed":
        customer_id     = data_obj.get("customer", "")
        subscription_id = data_obj.get("subscription", "")
        client_ref      = data_obj.get("client_reference_id", "")  # our user_id

        # Persist Stripe IDs + upgrade plan
        if customer_id and subscription_id:
            try:
                # If we have a client_reference_id (our user_id), use it for a
                # more reliable lookup (handles new users who have no stripe ID yet)
                if client_ref:
                    _get_conn, _put_conn, _dictcur, _ = _get_conn_and_helpers()
                    conn = _get_conn()
                    try:
                        cur = _dictcur(conn)
                        cur.execute(
                            """
                            UPDATE users
                               SET plan                   = 'pro',
                                   stripe_customer_id     = %s,
                                   stripe_subscription_id = %s,
                                   plan_expires_at        = COALESCE(%s, plan_expires_at),
                       updated_at             = NOW()
                             WHERE id = %s
                            """,
                            (customer_id, subscription_id, None, int(client_ref)),
                        )
                        conn.commit()
                        logger.info(
                            "STRIPE checkout.completed: user=%s customer=%s sub=%s",
                            client_ref, customer_id, subscription_id,
                        )
                    except Exception:
                        conn.rollback()
                        logger.exception("STRIPE checkout update failed")
                        raise
                    finally:
                        _put_conn(conn)
                else:
                    _set_user_plan(
                        stripe_customer_id=customer_id,
                        stripe_subscription_id=subscription_id,
                        plan="pro",
                    )
            except Exception:
                logger.exception("STRIPE checkout.session.completed handler failed")
                # Return 200 so Stripe does not retry — we log for manual review
        else:
            logger.warning(
                "STRIPE checkout.session.completed missing IDs: customer=%s sub=%s",
                customer_id, subscription_id,
            )

    # ── customer.subscription.deleted ────────────────────────────────────────
    elif event_type == "customer.subscription.deleted":
        subscription_id = data_obj.get("id", "")
        if subscription_id:
            try:
                _downgrade_by_subscription(subscription_id)
            except Exception:
                logger.exception("STRIPE subscription.deleted handler failed")

    # ── invoice.payment_failed ────────────────────────────────────────────────
    elif event_type == "invoice.payment_failed":
        customer_id = data_obj.get("customer", "")
        if customer_id:
            try:
                email = _get_customer_email(customer_id)
                if email:
                    _send_payment_failed_email(email)
                else:
                    logger.warning(
                        "STRIPE invoice.payment_failed: no user found for customer=%s",
                        customer_id,
                    )
            except Exception:
                logger.exception("STRIPE payment_failed handler failed")

    else:
        logger.debug("STRIPE unhandled event type: %s", event_type)

    # Always return 200 so Stripe marks the webhook as delivered
    return {"received": True}
