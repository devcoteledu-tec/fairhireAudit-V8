-- ════════════════════════════════════════════════════════════════════════════
-- Migration 0003 — Email verification & password reset  (post-v2.1)
-- Adds: users.email_verified, users.email_verified_at
-- Creates: tokens table
-- ════════════════════════════════════════════════════════════════════════════

ALTER TABLE users
    ADD COLUMN email_verified    BOOLEAN     DEFAULT FALSE,
    ADD COLUMN email_verified_at TIMESTAMPTZ;

CREATE TABLE tokens (
    id         SERIAL      PRIMARY KEY,
    user_id    INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT        NOT NULL UNIQUE,
    type       TEXT        NOT NULL CHECK (type IN ('email_verify', 'password_reset')),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tokens_token   ON tokens(token);
CREATE INDEX idx_tokens_user_id ON tokens(user_id);

INSERT INTO schema_migrations (version, description)
VALUES ('0003', 'Email verification and password reset: users.email_verified, tokens table');
