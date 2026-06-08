-- ════════════════════════════════════════════════════════════════════════════
-- Migration 0002 — FairHire v6 audit columns
-- Adds: gender_stats, other_gender_*, module_results, systemic_bias_*,
--       region, caste_worst_air, gender_majority/minority_group
-- ════════════════════════════════════════════════════════════════════════════

ALTER TABLE audits
    ADD COLUMN gender_stats               JSONB   DEFAULT '{}',
    ADD COLUMN other_gender_total         INTEGER DEFAULT 0,
    ADD COLUMN other_gender_hired         INTEGER DEFAULT 0,
    ADD COLUMN other_gender_shortlisted   INTEGER DEFAULT 0,
    ADD COLUMN module_results             JSONB   DEFAULT '{}',
    ADD COLUMN systemic_bias_triggered    BOOLEAN DEFAULT FALSE,
    ADD COLUMN systemic_bias_deduction    INTEGER DEFAULT 0,
    ADD COLUMN region                     TEXT,
    ADD COLUMN caste_worst_air            REAL,
    ADD COLUMN gender_majority_group      TEXT,
    ADD COLUMN gender_minority_group      TEXT;

INSERT INTO schema_migrations (version, description)
VALUES ('0002', 'v6 audit columns: gender stats, non-binary, module results, systemic bias, region, caste/skin fields');
