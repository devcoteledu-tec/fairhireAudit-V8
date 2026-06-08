"""
Tests for stripe_webhook.py
Cover the four plan-state transitions that affect user access.
"""
import json
import hmac
import hashlib
import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)


def _make_stripe_sig(payload: bytes, secret: str) -> str:
    ts = int(time.time())
    signed = f"{ts}.{payload.decode()}"
    sig = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


WEBHOOK_SECRET = "whsec_test_secret"


def _post_event(event: dict):
    payload = json.dumps(event).encode()
    sig = _make_stripe_sig(payload, WEBHOOK_SECRET)
    with patch("stripe_webhook._STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET):
        return client.post(
            "/api/stripe/webhook",
            content=payload,
            headers={"stripe-signature": sig, "content-type": "application/json"},
        )


def test_checkout_completed_upgrades_plan():
    """A completed checkout session must set plan='pro'."""
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "customer": "cus_abc",
            "subscription": "sub_123",
            "client_reference_id": "",
        }},
    }
    with patch("stripe_webhook._set_user_plan") as mock_set:
        r = _post_event(event)
    assert r.status_code == 200
    mock_set.assert_called_once_with(
        stripe_customer_id="cus_abc",
        stripe_subscription_id="sub_123",
        plan="pro",
    )


def test_subscription_deleted_downgrades_plan():
    """A deleted subscription must downgrade to free."""
    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_456"}},
    }
    with patch("stripe_webhook._downgrade_by_subscription") as mock_down:
        r = _post_event(event)
    assert r.status_code == 200
    mock_down.assert_called_once_with("sub_456")


def test_payment_failed_sends_email():
    """A failed invoice must trigger the recovery email."""
    event = {
        "type": "invoice.payment_failed",
        "data": {"object": {"customer": "cus_abc"}},
    }
    with patch("stripe_webhook._get_customer_email", return_value="test@example.com") as mock_get, \
         patch("stripe_webhook._send_payment_failed_email") as mock_email:
        r = _post_event(event)
    assert r.status_code == 200
    mock_get.assert_called_once_with("cus_abc")
    mock_email.assert_called_once_with("test@example.com")


def test_invalid_signature_returns_400():
    """A request with a bad Stripe signature must be rejected."""
    payload = json.dumps({"type": "checkout.session.completed"}).encode()
    with patch("stripe_webhook._STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET):
        r = client.post(
            "/api/stripe/webhook",
            content=payload,
            headers={"stripe-signature": "t=0,v1=badsig", "content-type": "application/json"},
        )
    assert r.status_code in (400, 401)
