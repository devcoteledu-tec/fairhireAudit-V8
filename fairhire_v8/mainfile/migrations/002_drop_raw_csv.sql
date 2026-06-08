-- Migration 002: Drop unused raw_csv column (PII/GDPR hygiene)
-- The column was never populated by the API. Safe to drop.
ALTER TABLE uploads DROP COLUMN IF EXISTS raw_csv;
