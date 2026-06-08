-- ════════════════════════════════════════════════════════════════════════════
-- Migration 0004 — Stripe billing  (post-v2.2)
-- Adds: stripe columns on users, plan_limits table + seed rows
-- ════════════════════════════════════════════════════════════════════════════

-- ── Stripe columns on users ───────────────────────────────────────────────────
ALTER TABLE users
    ADD COLUMN stripe_customer_id     TEXT,
    ADD COLUMN stripe_subscription_id TEXT,
    ADD COLUMN IF NOT EXISTS plan_expires_at        TIMESTAMPTZ,
    ADD COLUMN audit_count_this_month INTEGER     DEFAULT 0,
    ADD COLUMN audit_count_reset_at   TIMESTAMPTZ DEFAULT DATE_TRUNC('month', NOW());

-- ── Plan limits reference table ───────────────────────────────────────────────
CREATE TABLE plan_limits (
    plan           TEXT    PRIMARY KEY,
    monthly_audits INTEGER NOT NULL,        -- -1 = unlimited
    pdf_reports    BOOLEAN NOT NULL DEFAULT FALSE,
    api_access     BOOLEAN NOT NULL DEFAULT FALSE
);

-- ── Seed plan rows ────────────────────────────────────────────────────────────
INSERT INTO plan_limits (plan, monthly_audits, pdf_reports, api_access) VALUES
    ('free',        5, FALSE, FALSE),
    ('pro',        -1, TRUE,  FALSE),
    ('enterprise', -1, TRUE,  TRUE);

-- ── Indexes for Stripe webhook lookups ────────────────────────────────────────
CREATE INDEX idx_users_stripe_customer_id     ON users(stripe_customer_id);
CREATE INDEX idx_users_stripe_subscription_id ON users(stripe_subscription_id);

INSERT INTO schema_migrations (version, description)
VALUES ('0004', 'Stripe billing: stripe columns on users, plan_limits table, seed data');
