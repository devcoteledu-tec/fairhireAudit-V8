-- ════════════════════════════════════════════════════════════════════════════
-- Migration 0001 — Initial schema
-- FairHire v2.0
-- Tables: users, uploads, audits
-- ════════════════════════════════════════════════════════════════════════════

-- ── Migrations tracking table (created once, never dropped) ──────────────────
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT        PRIMARY KEY,
    description TEXT        NOT NULL,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── users ─────────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id             SERIAL      PRIMARY KEY,
    email          TEXT        NOT NULL UNIQUE,
    password_hash  TEXT        NOT NULL,
    company_name   TEXT        NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    plan           TEXT                 DEFAULT 'free',
    industry       TEXT,
    employee_count TEXT,
    country        TEXT,
    updated_at     TIMESTAMPTZ
);

-- ── uploads ───────────────────────────────────────────────────────────────────
CREATE TABLE uploads (
    id               SERIAL      PRIMARY KEY,
    user_id          INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename         TEXT,
    row_count        INTEGER,
    raw_csv          TEXT,
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
    fair_hiring_score            REAL,
    score_label                  TEXT,
    air_gender                   REAL,
    shortlisting_gap             REAL,
    hiring_gap                   REAL,
    disability_air               REAL,
    flags                        JSONB       DEFAULT '[]',
    institution_flags            JSONB       DEFAULT '[]',
    age_flags                    JSONB       DEFAULT '[]',
    caste_flags                  JSONB       DEFAULT '[]',
    skin_flags                   JSONB       DEFAULT '[]',
    referral_flags               JSONB       DEFAULT '[]',
    marital_flags                JSONB       DEFAULT '[]',
    proxy_flags                  JSONB       DEFAULT '[]',
    air_skin                     REAL,
    skin_best_rate               REAL,
    skin_worst_rate              REAL,
    referral_hire_rate           REAL,
    non_referral_hire_rate       REAL,
    referral_air                 REAL,
    referral_hhi                 REAL,
    men_total                    INTEGER,
    women_total                  INTEGER,
    men_shortlisted              INTEGER,
    women_shortlisted            INTEGER,
    men_hired                    INTEGER,
    women_hired                  INTEGER,
    skin_stats                   JSONB       DEFAULT '{}',
    referral_stats               JSONB       DEFAULT '{}',
    marital_stats                JSONB       DEFAULT '{}',
    marital_intersectional_stats JSONB       DEFAULT '{}',
    proxy_stats                  JSONB       DEFAULT '{}',
    proxy_phi_scores             JSONB       DEFAULT '{}',
    caste_stats                  JSONB       DEFAULT '{}',
    caste_col                    TEXT,
    institution_stats            JSONB       DEFAULT '{}',
    age_stats                    JSONB       DEFAULT '{}',
    p_value                      REAL,
    is_significant               BOOLEAN     DEFAULT FALSE,
    original_filename            TEXT,
    row_count                    INTEGER,
    computed_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX idx_audits_user_id    ON audits(user_id);
CREATE INDEX idx_audits_computed_at ON audits(computed_at DESC);
CREATE INDEX idx_uploads_user_id   ON uploads(user_id);

-- ── record ────────────────────────────────────────────────────────────────────
INSERT INTO schema_migrations (version, description)
VALUES ('0001', 'Initial schema: users, uploads, audits, indexes');
