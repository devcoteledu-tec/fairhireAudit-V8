-- ════════════════════════════════════════════════════════════════════════════
-- FairHire v6.2 — Consolidated schema
-- For FRESH installs only. Existing databases use migrate.py instead.
--
-- Reflects the complete state after all migrations 0001–0004.
-- When you add migration 0005+, update this file to match.
-- ════════════════════════════════════════════════════════════════════════════

-- ── Migration tracking ────────────────────────────────────────────────────────
CREATE TABLE schema_migrations (
    version     TEXT        PRIMARY KEY,
    description TEXT        NOT NULL,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── users ─────────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id                        SERIAL      PRIMARY KEY,
    email                     TEXT        NOT NULL UNIQUE,
    password_hash             TEXT        NOT NULL,
    company_name              TEXT        NOT NULL DEFAULT '',
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    plan                      TEXT                 DEFAULT 'free',
    industry                  TEXT,
    employee_count            TEXT,
    country                   TEXT,
    updated_at                TIMESTAMPTZ,
    -- 0003: email verification
    email_verified            BOOLEAN              DEFAULT FALSE,
    email_verified_at         TIMESTAMPTZ,
    -- 0004: Stripe billing
    stripe_customer_id        TEXT,
    stripe_subscription_id    TEXT,
    plan_expires_at           TIMESTAMPTZ,
    audit_count_this_month    INTEGER              DEFAULT 0,
    audit_count_reset_at      TIMESTAMPTZ          DEFAULT DATE_TRUNC('month', NOW())
);

-- ── uploads ───────────────────────────────────────────────────────────────────
CREATE TABLE uploads (
    id               SERIAL      PRIMARY KEY,
    user_id          INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename         TEXT,
    row_count        INTEGER,
    uploaded_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detected_columns TEXT,
    engine_version   TEXT                 DEFAULT '2.0',
    company_name     TEXT
);

-- ── audits ────────────────────────────────────────────────────────────────────
CREATE TABLE audits (
    id                           SERIAL      PRIMARY KEY,
    upload_id                    INTEGER     REFERENCES uploads(id) ON DELETE SET NULL,
    user_id                      INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- scores
    fair_hiring_score            REAL,
    score_label                  TEXT,
    -- gender
    air_gender                   REAL,
    shortlisting_gap             REAL,
    hiring_gap                   REAL,
    men_total                    INTEGER,
    women_total                  INTEGER,
    men_shortlisted              INTEGER,
    women_shortlisted            INTEGER,
    men_hired                    INTEGER,
    women_hired                  INTEGER,
    gender_stats                 JSONB       DEFAULT '{}',   -- 0002
    other_gender_total           INTEGER     DEFAULT 0,      -- 0002
    other_gender_hired           INTEGER     DEFAULT 0,      -- 0002
    other_gender_shortlisted     INTEGER     DEFAULT 0,      -- 0002
    gender_majority_group        TEXT,                       -- 0002
    gender_minority_group        TEXT,                       -- 0002
    -- disability
    disability_air               REAL,
    -- skin / colorism
    air_skin                     REAL,
    skin_best_rate               REAL,
    skin_worst_rate              REAL,
    skin_stats                   JSONB       DEFAULT '{}',
    -- referral
    referral_hire_rate           REAL,
    non_referral_hire_rate       REAL,
    referral_air                 REAL,
    referral_hhi                 REAL,
    referral_stats               JSONB       DEFAULT '{}',
    -- marital
    marital_stats                JSONB       DEFAULT '{}',
    marital_intersectional_stats JSONB       DEFAULT '{}',
    -- proxy
    proxy_stats                  JSONB       DEFAULT '{}',
    proxy_phi_scores             JSONB       DEFAULT '{}',
    -- caste
    caste_stats                  JSONB       DEFAULT '{}',
    caste_col                    TEXT,
    caste_worst_air              REAL,                       -- 0002
    -- institution / age
    institution_stats            JSONB       DEFAULT '{}',
    age_stats                    JSONB       DEFAULT '{}',
    -- flag arrays
    flags                        JSONB       DEFAULT '[]',
    institution_flags            JSONB       DEFAULT '[]',
    age_flags                    JSONB       DEFAULT '[]',
    caste_flags                  JSONB       DEFAULT '[]',
    skin_flags                   JSONB       DEFAULT '[]',
    referral_flags               JSONB       DEFAULT '[]',
    marital_flags                JSONB       DEFAULT '[]',
    proxy_flags                  JSONB       DEFAULT '[]',
    -- module results                                        -- 0002
    module_results               JSONB       DEFAULT '{}',
    systemic_bias_triggered      BOOLEAN     DEFAULT FALSE,
    systemic_bias_deduction      INTEGER     DEFAULT 0,
    region                       TEXT,
    -- legacy significance fields
    p_value                      REAL,
    is_significant               BOOLEAN     DEFAULT FALSE,
    -- metadata
    original_filename            TEXT,
    row_count                    INTEGER,
    computed_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── tokens (email verify + password reset) ────────────────────────────────────
CREATE TABLE tokens (
    id         SERIAL      PRIMARY KEY,
    user_id    INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT        NOT NULL UNIQUE,
    type       TEXT        NOT NULL CHECK (type IN ('email_verify', 'password_reset')),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── plan limits ───────────────────────────────────────────────────────────────
CREATE TABLE plan_limits (
    plan           TEXT    PRIMARY KEY,
    monthly_audits INTEGER NOT NULL,
    pdf_reports    BOOLEAN NOT NULL DEFAULT FALSE,
    api_access     BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO plan_limits (plan, monthly_audits, pdf_reports, api_access) VALUES
    ('free',        5, FALSE, FALSE),
    ('pro',        -1, TRUE,  FALSE),
    ('enterprise', -1, TRUE,  TRUE);

-- ── indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX idx_audits_user_id               ON audits(user_id);
CREATE INDEX idx_audits_computed_at           ON audits(computed_at DESC);
CREATE INDEX idx_uploads_user_id              ON uploads(user_id);
CREATE INDEX idx_tokens_token                 ON tokens(token);
CREATE INDEX idx_tokens_user_id              ON tokens(user_id);
CREATE INDEX idx_users_stripe_customer_id    ON users(stripe_customer_id);
CREATE INDEX idx_users_stripe_subscription_id ON users(stripe_subscription_id);

-- ── mark all migrations as applied (fresh install) ────────────────────────────
INSERT INTO schema_migrations (version, description) VALUES
    ('0001', 'Initial schema: users, uploads, audits, indexes'),
    ('0002', 'v6 audit columns: gender stats, non-binary, module results, systemic bias, region, caste/skin fields'),
    ('0003', 'Email verification and password reset: users.email_verified, tokens table'),
    ('0004', 'Stripe billing: stripe columns on users, plan_limits table, seed data');

-- BUG-8 fix — indexes on tokens.expires_at to prevent full table scans during
-- token validation queries and scheduled cleanup of expired/used rows.
CREATE INDEX IF NOT EXISTS idx_tokens_expires_at
    ON tokens(expires_at);

CREATE INDEX IF NOT EXISTS idx_tokens_active
    ON tokens(token)
 WHERE used_at IS NULL AND expires_at > NOW();
