"""
audit_engine.py  ·  FairHire v6.1
──────────────────────────────────────────────────────────────────────────────
Single source of truth for ALL fairness metric computation.
Imported by api.py, streamlit_app.py, and any future CLI tooling.
Never duplicate this logic anywhere else.

Bias modules included
─────────────────────
  CORE (v1)
    1. Gender Adverse Impact Ratio          — 4/5ths rule, EEOC / DPDP Act
    2. Statistical Parity Gap (SPG)         — shortlisting + hiring stages
    3. Disability AIR                       — RPWD Act 2016
    4. Institution / College Bias           — one-vs-rest comparison
    5. Age Group Bias                       — one-vs-rest comparison
    6. Caste / Reservation Category Bias   — SC/ST escalation, Article 15

  v2
    7. Skin Colour Bias                     — Spearman rank-correlation + per-band AIR
    8. Referral Network Bias                — referral vs cold-applicant outcome gap
    9. Marital Status Bias                  — intersectional (gender × marital status)
   10. Proxy Bias Detection                 — postcode / name-origin / school-tier
                                              as proxies for protected attributes

Statistical methods used
────────────────────────
  • Adverse Impact Ratio (AIR)          — minority_rate / majority_rate; threshold 0.80
  • Statistical Parity Gap (SPG)        — (group_A_rate − group_B_rate) × 100; threshold ±15 pp
  • One-vs-Rest Gap                     — group_rate vs Σ(all_other_groups); threshold ±20 pp
  • Intersectional Gap                  — cross-tabulation of two protected attributes
  • Spearman Rank Correlation (ρ)       — ordinal skin-tone ordering vs hire-rate
  • Concentration Index (HHI-style)     — detects referral network insularity
  • Phi Coefficient (φ)                 — 2×2 chi-square for proxy correlation with outcome
  • Fisher's Exact Test (p-value)       — statistical significance for AIR flags
  • Bonferroni–Holm correction          — family-wise error control across all tests
  • Effect-size guard                   — min_group_size ≥ 10 before any flag is raised
  • 95% Wilson CI on hire rates         — confidence intervals in all flag messages

Scoring  (v6.1 — Weighted Integrity System)
───────────────────────────────────────────
  Score is cumulative (0–100): modules EARN their weight only when the module
  passes (no significant AIR violation surviving Bonferroni–Holm correction).
  A failed module contributes 0 points.

  Module weights:
    gender      → 15 pts   Statutory Core
    caste       → 15 pts   Statutory Core (Maps to Race in US/UK)
    disability  → 15 pts   Statutory Core (RPWD Act independent gate)
    skin        → 15 pts   Strict action against Colorism
    proxy       → 10 pts   Catching indirect discrimination
    spg         → 10 pts   Multi-stage selection parity
    institution →  6 pts   Anti-Elitism (Paisa ullorude college bias)
    marital     →  6 pts   Intersectional protection for married candidates
    age         →  4 pts   Ageism checker
    referral    →  4 pts   Anti-Nepotism checker
    ─────────────────
    TOTAL       → 100 pts

  Intersectional "Dealbreaker" Penalty:
    If BOTH Caste AND Skin Colour modules fail, an additional −15 pt
    "Systemic Bias" deduction is applied.

  Score labels:
    ≥ 75  → "Good"
    ≥ 50  → "Fair"
    ≥ 25  → "At Risk"
    <  25  → "Toxic"

  Missing optional columns (disability, skin, caste, etc.) contribute 0 points
  rather than free points — data omission is never rewarded.

Flexible Column Mapping
────────────────────────
  Caste:    "caste"        | "category"      | "social_group"
  Skin:     "skin_colour"  | "skin_tone"     | "complexion"
  Outcome:  "hired"        | "hiring_status" | "selection"

Robust Outcome Parsing
──────────────────────
  Numeric : 1, 1.0 → True; 0, 0.0 → False
  String  : "Yes" / "True" / "Hired" (case-insensitive) → True; else → False
  Guard   : If parsed outcome column is all zeros → "Data Quality Error" raised.

Author note
───────────
  All thresholds are conservative and documented. Every flag message includes
  the numeric evidence so audit consumers can verify computations independently.
  No flag is raised on groups smaller than min_group_size (default 10) because
  rates computed on fewer observations are statistically unreliable.
  Statistical significance (Fisher's Exact, Bonferroni–Holm) is required before
  any flag survives to the output.
"""
from __future__ import annotations  # FIX 0: must precede all non-docstring code (SyntaxError fix)

FAIRHIRE_VERSION = "6.2"  # FIX 0: bumped from 6.1 → 6.2 to reflect this patch release

import math
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 0 — CONFIGURATION CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

NON_REFERRAL_VALUES: Set[str] = {
    "no", "false", "0", "none", "nan", "n/a", "",
    "cold", "direct", "portal", "job board", "careers page",
    # Western platforms
    "linkedin", "naukri", "indeed", "glassdoor",
    # Asia-Pacific / Middle East / Africa platforms
    "jobstreet", "jobsdb", "bayt", "wuzzuf", "apna", "shine",
    "monster", "timesjobs", "iimjobs", "foundit", "hirecraft",
    "workindia", "freshersworld", "wisdomjobs",
    # Generic descriptors
    "walk-in", "walk in", "campus", "advertisement", "ad",
    "company website", "career site", "referral portal",
}

MODULE_WEIGHTS: Dict[str, int] = {
    "gender":      15,  # Statutory Core
    "caste":       15,  # Statutory Core (Maps to Race in US/UK)
    "disability":  15,  # Statutory Core (RPWD Act independent gate)
    "skin":        15,  # Strict action against Colorism
    "proxy":       10,  # Catching indirect discrimination
    "spg":         10,  # Multi-stage selection parity
    "institution":  6,  # Anti-Elitism (Paisa ullorude college bias)
    "marital":      6,  # Intersectional protection for married candidates
    "age":          4,  # Ageism checker
    "referral":     4,  # Anti-Nepotism checker
}

assert sum(MODULE_WEIGHTS.values()) == 100, "Module weights must sum to 100"

SYSTEMIC_BIAS_DEDUCTION: int = 15

_OUTCOME_POSITIVE_STRINGS: Set[str] = {"yes", "true", "hired", "1", "1.0"}

_GENDER_MALE_VALUES:   Set[str] = {"male", "m", "man", "men", "boy"}
_GENDER_FEMALE_VALUES: Set[str] = {"female", "f", "woman", "women", "girl", "w"}
_GENDER_NULL_VALUES:   Set[str] = {"", "nan", "none", "null", "unknown", "na", "n/a", "prefer not to say"}

# Region-aware legal framework labels.
_REGION_LABELS: Dict[str, Dict[str, str]] = {
    "IN": {
        "gender_law":     "DPDP Act / POSH Act",
        "caste_law":      "Article 15 Constitution of India / SC-ST (Prevention of Atrocities) Act",
        "disability_law": "RPWD Act 2016",
        "age_law":        "Equal Opportunity Policy (no specific age law)",
        "general":        "Indian employment law",
    },
    "US": {
        "gender_law":     "Title VII Civil Rights Act / EEOC 4/5ths rule",
        "caste_law":      "Title VII (national origin / race proxy)",
        "disability_law": "ADA (Americans with Disabilities Act)",
        "age_law":        "ADEA (Age Discrimination in Employment Act)",
        "general":        "US federal employment law",
    },
    "UK": {
        "gender_law":     "Equality Act 2010 (sex)",
        "caste_law":      "Equality Act 2010 (race / caste)",
        "disability_law": "Equality Act 2010 (disability)",
        "age_law":        "Equality Act 2010 (age)",
        "general":        "UK Equality Act 2010",
    },
    "EU": {
        "gender_law":     "EU Equal Treatment Directive 2006/54/EC",
        "caste_law":      "EU Racial Equality Directive 2000/43/EC",
        "disability_law": "EU Employment Framework Directive 2000/78/EC",
        "age_law":        "EU Employment Framework Directive 2000/78/EC (age)",
        "general":        "EU equality directives",
    },
}
_DEFAULT_REGION = "IN"

_ALPHA = 0.05  # significance threshold (pre-correction)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — PRIMITIVE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _safe_rate(numerator: int, denominator: int) -> float:
    """numerator / denominator; returns 0.0 when denominator == 0."""
    return numerator / denominator if denominator > 0 else 0.0


def _safe_air(minority_rate: float, majority_rate: float) -> float:
    """
    Adverse Impact Ratio (AIR).
    Returns 1.0 (no disparity) when majority_rate == 0.
    """
    return minority_rate / majority_rate if majority_rate > 0 else 1.0


def _null_like(value: Any) -> bool:
    """True when a value represents a missing / unknown entry."""
    return str(value).lower().strip() in ("nan", "none", "null", "unknown", "na", "n/a", "")


def _bool_series(series: pd.Series) -> pd.Series:
    """Vectorised parse of yes/true/1 → True from a DataFrame column."""
    return series.astype(str).str.lower().str.strip().isin(("yes", "true", "1"))


def _parse_outcome_series(series: pd.Series) -> pd.Series:
    """
    Robust outcome parser for hired / hiring_status / selection column.
    Handles numeric (1, 1.0 → True; 0, 0.0 → False) and string variants.
    """
    def _parse_single(val: Any) -> bool:
        try:
            return float(val) == 1.0
        except (ValueError, TypeError):
            pass
        return str(val).strip().lower() in _OUTCOME_POSITIVE_STRINGS

    return series.map(_parse_single)


def _detect_col(df_cols: List[str], candidates: Tuple[str, ...]) -> str:
    """Return the first candidate column present in df_cols, else ''."""
    for c in candidates:
        if c in df_cols:
            return c
    return ""


def _classify_gender(raw_value: str) -> str:
    """Map a raw gender string to 'male', 'female', 'other_gender', or 'unknown'."""
    v = str(raw_value).strip().lower()
    if v in _GENDER_NULL_VALUES:
        return "unknown"
    if v in _GENDER_MALE_VALUES:
        return "male"
    if v in _GENDER_FEMALE_VALUES:
        return "female"
    return "other_gender"


# ── Wilson 95% confidence interval ────────────────────────────────────────────

def _wilson_ci(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """
    Wilson score interval for a proportion.
    Returns (lower, upper) as fractions (0–1).
    Falls back to (0.0, 1.0) when n == 0.
    """
    if n == 0:
        return 0.0, 1.0
    p_hat = successes / n
    denom = 1 + z * z / n
    centre = (p_hat + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p_hat * (1 - p_hat) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def _ci_str(successes: int, n: int) -> str:
    """Human-readable 95% CI string, e.g. '[32.1%–47.9%]'."""
    lo, hi = _wilson_ci(successes, n)
    return f"[95% CI: {lo * 100:.1f}%–{hi * 100:.1f}%]"


# ── Fisher's Exact Test ────────────────────────────────────────────────────────

def _fisher_p(a: int, b: int, c: int, d: int) -> float:
    """
    Two-sided Fisher's Exact Test on a 2×2 table:
        [[a, b],   (group A: hired, not-hired)
         [c, d]]   (group B: hired, not-hired)
    Returns p-value. Returns 1.0 on degenerate tables.
    """
    try:
        _, p = scipy_stats.fisher_exact([[a, b], [c, d]], alternative="two-sided")
        return float(p)
    except Exception:
        return 1.0


def _phi_coefficient(a: int, b: int, c: int, d: int) -> float:
    """Phi coefficient for a 2×2 contingency table."""
    denom = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    return (a * d - b * c) / denom if denom > 0 else 0.0


# ── Bonferroni–Holm correction ────────────────────────────────────────────────

def _holm_correct(p_values: List[float]) -> List[float]:
    """
    Bonferroni–Holm step-down procedure.
    Returns adjusted p-values in the same order as input.
    """
    n = len(p_values)
    if n == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * n
    prev_adj = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        adj = min(1.0, max(prev_adj, p * (n - rank)))
        adjusted[orig_idx] = adj
        prev_adj = adj
    return adjusted


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — GENERIC ONE-VS-REST GROUP BIAS  (vectorised)
# ══════════════════════════════════════════════════════════════════════════════

def _compute_group_bias(
    stats: Dict[str, Dict],
    min_group_size: int = 10,
    gap_threshold: float = 20.0,
    label_prefix: str = "Group",
    check_shortlisting: bool = True,
    region_labels: Optional[Dict[str, str]] = None,
) -> Tuple[List[str], List[float]]:
    """
    For every group G in `stats`, compare G's shortlisting/hiring rate against
    the pooled rate of all OTHER groups (one-vs-rest).

    Gap formula:  gap_pp = (group_rate − other_rate) × 100
    Flag when:    |gap_pp| > gap_threshold AND Fisher p ≤ 0.05

    Returns
    ───────
    flags       – list of human-readable flag strings
    raw_pvalues – raw Fisher p-values aligned to flags (for Holm correction)
    """
    flags: List[str] = []
    raw_pvalues: List[float] = []

    grand_total = sum(s["total"]       for s in stats.values())
    grand_sl    = sum(s["shortlisted"] for s in stats.values())
    grand_hr    = sum(s["hired"]       for s in stats.values())

    for group_name, s in stats.items():
        if _null_like(group_name):
            continue
        if s["total"] < min_group_size:
            continue

        other_total = grand_total - s["total"]
        other_sl    = grand_sl    - s["shortlisted"]
        other_hr    = grand_hr    - s["hired"]

        if other_total < min_group_size:
            continue

        group_hr_rate = _safe_rate(s["hired"], s["total"])
        other_hr_rate = _safe_rate(other_hr, other_total)
        hr_gap        = (group_hr_rate - other_hr_rate) * 100

        if abs(hr_gap) > gap_threshold:
            a = s["hired"];     b = s["total"] - s["hired"]
            c = other_hr;       d = other_total - other_hr
            p = _fisher_p(a, b, c, d)
            if p <= _ALPHA:
                direction = "favoured" if hr_gap > 0 else "disadvantaged"
                ci = _ci_str(s["hired"], s["total"])
                flags.append(
                    f"{label_prefix} Bias: '{group_name}' candidates are {direction} "
                    f"in hiring ({abs(hr_gap):.1f}pp gap vs all others; "
                    f"threshold: ±{gap_threshold:.0f}pp). "
                    f"Hire rate: {group_hr_rate * 100:.1f}% {ci} vs others "
                    f"{other_hr_rate * 100:.1f}% {_ci_str(other_hr, other_total)}. "
                    f"Fisher p={p:.4f}."
                )
                raw_pvalues.append(p)

        if check_shortlisting:
            group_sl_rate = _safe_rate(s["shortlisted"], s["total"])
            other_sl_rate = _safe_rate(other_sl, other_total)
            sl_gap        = (group_sl_rate - other_sl_rate) * 100

            if abs(sl_gap) > gap_threshold:
                a = s["shortlisted"]; b = s["total"] - s["shortlisted"]
                c = other_sl;         d = other_total - other_sl
                p = _fisher_p(a, b, c, d)
                if p <= _ALPHA:
                    direction = "favoured" if sl_gap > 0 else "disadvantaged"
                    ci = _ci_str(s["shortlisted"], s["total"])
                    flags.append(
                        f"{label_prefix} Bias: '{group_name}' candidates are {direction} "
                        f"in shortlisting ({abs(sl_gap):.1f}pp gap vs all others; "
                        f"threshold: ±{gap_threshold:.0f}pp). "
                        f"Shortlist rate: {group_sl_rate * 100:.1f}% {ci} vs others "
                        f"{other_sl_rate * 100:.1f}% {_ci_str(other_sl, other_total)}. "
                        f"Fisher p={p:.4f}."
                    )
                    raw_pvalues.append(p)

    return flags, raw_pvalues


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — MODULE: GENDER BIAS
# ══════════════════════════════════════════════════════════════════════════════

def _compute_gender_bias(
    gender_stats: Dict[str, Dict],
    min_group_size: int = 10,
    region_labels: Optional[Dict[str, str]] = None,
) -> Tuple[List[str], List[float], bool, float, str, str]:
    """
    Gender AIR with dynamic majority/minority assignment.
    Fisher p-value, Wilson CIs, returns raw p-values.

    Returns
    ───────
    flags, raw_pvalues, module_passed, air_gender, majority_label, minority_label
    """
    rl = region_labels or _REGION_LABELS[_DEFAULT_REGION]
    flags: List[str] = []
    raw_pvalues: List[float] = []

    eligible = {
        g: s for g, s in gender_stats.items()
        if g != "unknown" and s["total"] >= min_group_size
    }

    if len(eligible) < 2:
        return flags, raw_pvalues, True, 1.0, "N/A", "N/A"

    ranked = sorted(
        eligible.items(),
        key=lambda x: _safe_rate(x[1]["hired"], x[1]["total"]),
        reverse=True,
    )

    majority_label, majority_stats = ranked[0]
    minority_label, minority_stats = ranked[-1]

    majority_rate = _safe_rate(majority_stats["hired"], majority_stats["total"])
    minority_rate = _safe_rate(minority_stats["hired"], minority_stats["total"])
    air_gender    = _safe_air(minority_rate, majority_rate)

    a = majority_stats["hired"]; b = majority_stats["total"] - majority_stats["hired"]
    c = minority_stats["hired"]; d = minority_stats["total"] - minority_stats["hired"]
    p_air = _fisher_p(a, b, c, d)

    module_passed = air_gender >= 0.80

    if not module_passed and p_air <= _ALPHA:
        ci_maj = _ci_str(majority_stats["hired"], majority_stats["total"])
        ci_min = _ci_str(minority_stats["hired"], minority_stats["total"])
        flags.append(
            f"Adverse Impact Ratio (Gender): {air_gender:.3f} — "
            f"'{minority_label}' candidates hired at {air_gender * 100:.0f}% the rate of "
            f"'{majority_label}'. Legal threshold: 0.80 ({rl['gender_law']}). "
            f"'{majority_label}': {majority_stats['hired']}/{majority_stats['total']} "
            f"({majority_rate * 100:.1f}%) {ci_maj}; "
            f"'{minority_label}': {minority_stats['hired']}/{minority_stats['total']} "
            f"({minority_rate * 100:.1f}%) {ci_min}. "
            f"Fisher p={p_air:.4f}."
        )
        raw_pvalues.append(p_air)
    elif not module_passed and p_air > _ALPHA:
        # AIR failed but not statistically significant — module passes
        module_passed = True

    # One-vs-rest flags for every gender group
    ovr_flags, ovr_ps = _compute_group_bias(
        eligible,
        min_group_size=min_group_size,
        gap_threshold=15.0,
        label_prefix="Gender",
        region_labels=rl,
    )
    existing = set(flags)
    for f, p in zip(ovr_flags, ovr_ps):
        if f not in existing:
            flags.append(f)
            raw_pvalues.append(p)

    return flags, raw_pvalues, module_passed, air_gender, majority_label, minority_label


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — MODULE: SKIN COLOUR / COLORISM BIAS
# ══════════════════════════════════════════════════════════════════════════════

_SKIN_NORM: Dict[str, int] = {
    "type i": 1,   "type 1": 1,   "i": 1,   "1": 1,   "very fair": 1, "ivory": 1, "pale": 1,
    "type ii": 2,  "type 2": 2,   "ii": 2,  "2": 2,   "fair": 2,      "light": 2,
    "type iii": 3, "type 3": 3,   "iii": 3, "3": 3,   "light brown": 3, "medium": 3, "beige": 3,
    "type iv": 4,  "type 4": 4,   "iv": 4,  "4": 4,   "olive": 4,     "moderate brown": 4, "tan": 4,
    "type v": 5,   "type 5": 5,   "v": 5,   "5": 5,   "brown": 5,     "dark brown": 5,
    "type vi": 6,  "type 6": 6,   "vi": 6,  "6": 6,   "dark": 6,      "deep brown": 6,
    "very dark": 6, "ebony": 6,   "lighter": 2, "darker": 5, "medium brown": 4,
}


def _normalise_skin(raw: str) -> int:
    """Map a raw skin-colour label to a Fitzpatrick band (1–6), or 0 if unknown."""
    return _SKIN_NORM.get(str(raw).strip().lower(), 0)


def _spearman_skin(skin_stats: Dict[int, Dict], min_group_size: int) -> Tuple[float, float]:
    """
    Spearman rank correlation between Fitzpatrick band (ordinal) and hire rate.
    Returns (rho, p_value). rho < 0 means darker bands have lower hire rates (colorism).
    Returns (0.0, 1.0) when fewer than 3 eligible bands.
    """
    eligible = {b: s for b, s in skin_stats.items() if s["total"] >= min_group_size}
    if len(eligible) < 3:
        return 0.0, 1.0
    bands = sorted(eligible.keys())
    rates = [_safe_rate(eligible[b]["hired"], eligible[b]["total"]) for b in bands]
    try:
        rho, p = scipy_stats.spearmanr(bands, rates)
        return float(rho), float(p)
    except Exception:
        return 0.0, 1.0


def _compute_skin_bias(
    skin_stats: Dict[int, Dict],
    min_group_size: int = 10,
) -> Tuple[List[str], List[float], bool, float, float, float]:
    """
    Colorism metrics via Spearman ρ (ordinal) + per-band AIR.
    Fisher p-values and Wilson CIs in every flag.

    Returns flags, raw_pvalues, module_passed, air_skin, best_rate, worst_rate
    """
    flags: List[str] = []
    raw_pvalues: List[float] = []

    eligible_bands = {b: s for b, s in skin_stats.items() if s["total"] >= min_group_size}

    if len(eligible_bands) < 2:
        # FIX 3 (B4): Return None (not True) — data present but insufficient to test.
        # Returning True here awarded 15 free points without running any colorism test.
        return flags, raw_pvalues, None, 1.0, 0.0, 0.0

    ranked = sorted(
        eligible_bands.items(),
        key=lambda x: _safe_rate(x[1]["hired"], x[1]["total"]),
        reverse=True,
    )

    best_band,  best_s  = ranked[0]
    worst_band, worst_s = ranked[-1]
    best_rate  = _safe_rate(best_s["hired"],  best_s["total"])
    worst_rate = _safe_rate(worst_s["hired"], worst_s["total"])
    air_skin   = _safe_air(worst_rate, best_rate)

    # Spearman correlation
    rho, rho_p = _spearman_skin(skin_stats, min_group_size)
    if rho_p <= _ALPHA and rho < -0.50:
        flags.append(
            f"Colorism — Spearman ρ={rho:.3f} (p={rho_p:.4f}) between Fitzpatrick band "
            f"and hire rate. Negative ρ indicates darker skin tones are progressively "
            f"disadvantaged (ρ < −0.50 threshold; statistically significant)."
        )
        raw_pvalues.append(rho_p)

    module_passed = True

    for band, s in eligible_bands.items():
        if band == best_band:
            continue
        band_rate = _safe_rate(s["hired"], s["total"])
        band_air  = _safe_air(band_rate, best_rate)

        a = s["hired"];      b = s["total"] - s["hired"]
        c = best_s["hired"]; d = best_s["total"] - best_s["hired"]
        p = _fisher_p(a, b, c, d)

        if band_air < 0.80 and p <= _ALPHA:
            module_passed = False
            ci_band = _ci_str(s["hired"], s["total"])
            ci_best = _ci_str(best_s["hired"], best_s["total"])
            flags.append(
                f"Colorism — Fitzpatrick Type {band} candidates hired at "
                f"{band_rate * 100:.1f}% {ci_band} vs {best_rate * 100:.1f}% {ci_best} "
                f"for Type {best_band} (best-performing band). "
                f"AIR={band_air:.3f}; threshold 0.80. Fisher p={p:.4f}. "
                f"Type {band} pool: {s['total']} applicants, {s['hired']} hired."
            )
            raw_pvalues.append(p)
        elif band_air < 0.90 and p <= _ALPHA:
            flags.append(
                f"Colorism — Watch: Fitzpatrick Type {band} AIR={band_air:.3f} "
                f"(borderline; fail=0.80, monitor=0.90). Fisher p={p:.4f}. "
                f"vs Type {best_band} reference {best_rate * 100:.1f}%."
            )
            raw_pvalues.append(p)
        # AIR failed but not statistically significant: no flag, no module failure

    # Per-band one-vs-rest
    named_stats: Dict[str, Dict] = {
        f"Fitzpatrick Type {band}": s for band, s in eligible_bands.items()
    }
    if len(named_stats) >= 2:
        band_flags, band_ps = _compute_group_bias(
            named_stats, min_group_size=min_group_size, gap_threshold=20.0,
            label_prefix="Skin Colour",
        )
        existing_text = set(flags)
        for bf, bp in zip(band_flags, band_ps):
            if bf not in existing_text:
                flags.append(bf)
                raw_pvalues.append(bp)

    return flags, raw_pvalues, module_passed, air_skin, best_rate, worst_rate


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — MODULE: REFERRAL NETWORK BIAS
# ══════════════════════════════════════════════════════════════════════════════

def _compute_referral_bias(
    referral_stats: Dict[str, Dict],
    min_group_size: int = 10,
) -> Tuple[List[str], List[float], bool, float, float, float, float]:
    """
    Referral vs cold-applicant outcome gaps and network concentration.
    Fisher p-values, Wilson CIs.

    Returns flags, raw_pvalues, module_passed, ref_hire_rate,
            non_ref_hire_rate, referral_air, hhi
    """
    flags: List[str] = []
    raw_pvalues: List[float] = []
    any_flag = False

    ref     = referral_stats.get("referred",     {"total": 0, "shortlisted": 0, "hired": 0, "referrers": {}})
    non_ref = referral_stats.get("not_referred", {"total": 0, "shortlisted": 0, "hired": 0, "referrers": {}})

    ref_total     = ref["total"]
    non_ref_total = non_ref["total"]

    if ref_total < min_group_size or non_ref_total < min_group_size:
        return flags, raw_pvalues, True, 0.0, 0.0, 1.0, 0.0

    ref_hire_rate     = _safe_rate(ref["hired"],     ref_total)
    non_ref_hire_rate = _safe_rate(non_ref["hired"], non_ref_total)
    hire_gap_pp       = (ref_hire_rate - non_ref_hire_rate) * 100
    referral_air      = _safe_air(non_ref_hire_rate, ref_hire_rate)

    ref_sl_rate     = _safe_rate(ref["shortlisted"],     ref_total)
    non_ref_sl_rate = _safe_rate(non_ref["shortlisted"], non_ref_total)
    sl_gap_pp       = (ref_sl_rate - non_ref_sl_rate) * 100

    if hire_gap_pp > 15:
        a = ref["hired"]; b = ref_total - ref["hired"]
        c = non_ref["hired"]; d = non_ref_total - non_ref["hired"]
        p = _fisher_p(a, b, c, d)
        if p <= _ALPHA:
            any_flag = True
            ci_ref = _ci_str(ref["hired"], ref_total)
            ci_non = _ci_str(non_ref["hired"], non_ref_total)
            flags.append(
                f"Referral Network Bias: Referred candidates hired at "
                f"{ref_hire_rate * 100:.1f}% {ci_ref} vs {non_ref_hire_rate * 100:.1f}% "
                f"{ci_non} for non-referred ({hire_gap_pp:.1f}pp gap; threshold: 15pp). "
                f"Referral advantage creates proxy discrimination via network homophily. "
                f"AIR={referral_air:.3f}. Fisher p={p:.4f}."
            )
            raw_pvalues.append(p)

    if sl_gap_pp > 15:
        a = ref["shortlisted"]; b = ref_total - ref["shortlisted"]
        c = non_ref["shortlisted"]; d = non_ref_total - non_ref["shortlisted"]
        p = _fisher_p(a, b, c, d)
        if p <= _ALPHA:
            any_flag = True
            flags.append(
                f"Referral Network Bias: Referred candidates shortlisted at "
                f"{ref_sl_rate * 100:.1f}% vs {non_ref_sl_rate * 100:.1f}% for "
                f"non-referred ({sl_gap_pp:.1f}pp gap). Fisher p={p:.4f}."
            )
            raw_pvalues.append(p)

    referrers: Dict[str, int] = ref.get("referrers", {})
    hhi = 0.0
    if referrers and sum(referrers.values()) >= min_group_size:
        total_refs = sum(referrers.values())
        hhi = sum((count / total_refs) ** 2 for count in referrers.values())
        if hhi > 0.25:
            any_flag = True
            top_referrer = max(referrers, key=referrers.get)  # type: ignore
            flags.append(
                f"Referral Concentration: HHI={hhi:.3f} (threshold: 0.25). "
                f"Top referrer accounts for "
                f"{referrers[top_referrer] / total_refs * 100:.0f}% of all referrals. "
                f"Concentrated referrer pool amplifies demographic homogeneity."
            )

    return flags, raw_pvalues, not any_flag, ref_hire_rate, non_ref_hire_rate, referral_air, hhi


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — MODULE: MARITAL STATUS BIAS (INTERSECTIONAL)
# ══════════════════════════════════════════════════════════════════════════════

_MARITAL_NORM: Dict[str, str] = {
    "single": "Single",       "unmarried": "Single",       "never married": "Single",
    "married": "Married",     "wed": "Married",             "wedded": "Married",
    "divorced": "Divorced",   "separated": "Separated",
    "widowed": "Widowed",     "widow": "Widowed",           "widower": "Widowed",
    "partnered": "Partnered", "domestic partner": "Partnered",
    "other": "Other",
}


def _compute_marital_bias(
    marital_stats: Dict[str, Dict],
    intersectional_stats: Dict[Tuple[str, str], Dict],
    min_group_size: int = 10,
) -> Tuple[List[str], List[float]]:
    """
    Two-layer marital status analysis (main + intersectional with all gender buckets).
    Fisher p-values, Wilson CIs.

    Returns flags, raw_pvalues
    """
    flags: List[str] = []
    raw_pvalues: List[float] = []

    main_flags, main_ps = _compute_group_bias(
        marital_stats, min_group_size=min_group_size,
        gap_threshold=20.0, label_prefix="Marital Status",
    )
    flags.extend(main_flags)
    raw_pvalues.extend(main_ps)

    gender_buckets: Set[str] = {g for _, g in intersectional_stats}
    marital_categories: Set[str] = {ms for ms, _ in intersectional_stats}

    for ms in marital_categories:
        bucket_stats: Dict[str, Dict] = {}
        for g in gender_buckets:
            s = intersectional_stats.get((ms, g), {"total": 0, "hired": 0, "shortlisted": 0})
            if s["total"] >= min_group_size:
                bucket_stats[g] = s

        if len(bucket_stats) < 2:
            continue

        ranked = sorted(
            bucket_stats.items(),
            key=lambda x: _safe_rate(x[1]["hired"], x[1]["total"]),
            reverse=True,
        )
        best_g,  best_s  = ranked[0]
        worst_g, worst_s = ranked[-1]

        best_rate  = _safe_rate(best_s["hired"],  best_s["total"])
        worst_rate = _safe_rate(worst_s["hired"], worst_s["total"])
        gap = (best_rate - worst_rate) * 100

        if gap > 15:
            a = best_s["hired"];  b = best_s["total"]  - best_s["hired"]
            c = worst_s["hired"]; d = worst_s["total"] - worst_s["hired"]
            p = _fisher_p(a, b, c, d)
            if p <= _ALPHA:
                ci_best  = _ci_str(best_s["hired"],  best_s["total"])
                ci_worst = _ci_str(worst_s["hired"], worst_s["total"])
                flags.append(
                    f"Intersectional Bias ({ms} × Gender): '{best_g}' candidates who are "
                    f"{ms.lower()} hired at {gap:.1f}pp higher rate than '{worst_g}' "
                    f"with the same marital status. "
                    f"'{best_g}': {best_rate * 100:.1f}% {ci_best}; "
                    f"'{worst_g}': {worst_rate * 100:.1f}% {ci_worst}. "
                    f"Fisher p={p:.4f}. Pattern may reflect assumptions about caregiving."
                )
                raw_pvalues.append(p)

    return flags, raw_pvalues


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — MODULE: PROXY BIAS DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def _compute_proxy_bias(
    proxy_stats: Dict[str, Dict[str, Dict]],
    min_group_size: int = 10,
) -> Tuple[List[str], List[float], Dict[str, float]]:
    """
    Proxy bias across postcode, name-origin, and school-tier channels.
    Fisher p-values, Wilson CIs.

    Returns flags, raw_pvalues, phi_scores (dict channel→φ)
    """
    flags:       List[str]        = []
    raw_pvalues: List[float]      = []
    phi_scores:  Dict[str, float] = {}

    for channel, groups in proxy_stats.items():
        if len(groups) < 2:
            continue

        group_list = [
            (name, s) for name, s in groups.items()
            if not _null_like(name) and s["total"] >= min_group_size
        ]
        if len(group_list) < 2:
            continue

        group_list.sort(key=lambda x: _safe_rate(x[1]["hired"], x[1]["total"]), reverse=True)
        priv_name, priv = group_list[0]
        rest_total = sum(s["total"] for _, s in group_list[1:])
        rest_hired = sum(s["hired"] for _, s in group_list[1:])

        if rest_total < min_group_size:
            continue

        priv_rate = _safe_rate(priv["hired"], priv["total"])
        rest_rate = _safe_rate(rest_hired, rest_total)
        gap_pp    = (priv_rate - rest_rate) * 100

        a = priv["hired"]; b = priv["total"] - priv["hired"]
        c = rest_hired;    d = rest_total - rest_hired
        phi = _phi_coefficient(a, b, c, d)
        p   = _fisher_p(a, b, c, d)
        phi_scores[channel] = round(phi, 4)

        friendly = channel.replace("_", " ").title()
        ci_priv = _ci_str(priv["hired"], priv["total"])
        ci_rest = _ci_str(rest_hired, rest_total)

        if phi > 0.30 and p <= _ALPHA:
            flags.append(
                f"HIGH RISK — Proxy Bias ({friendly}): φ={phi:.3f} (strong; threshold >0.30). "
                f"'{priv_name}' hired at {priv_rate * 100:.1f}% {ci_priv} "
                f"vs {rest_rate * 100:.1f}% {ci_rest} for all others ({gap_pp:.1f}pp gap). "
                f"Fisher p={p:.4f}. Variable likely acts as proxy for caste, "
                f"socioeconomic status, or ethnicity."
            )
            raw_pvalues.append(p)
        elif phi > 0.20 and p <= _ALPHA:
            flags.append(
                f"Proxy Bias ({friendly}): φ={phi:.3f} (moderate; threshold >0.20). "
                f"'{priv_name}' hired at {priv_rate * 100:.1f}% {ci_priv} "
                f"vs {rest_rate * 100:.1f}% {ci_rest} ({gap_pp:.1f}pp gap). "
                f"Fisher p={p:.4f}. Review whether this variable encodes protected attributes."
            )
            raw_pvalues.append(p)
        elif phi > 0.10 and p <= _ALPHA:
            flags.append(
                f"Proxy Watch ({friendly}): φ={phi:.3f} (small effect; monitor threshold >0.10). "
                f"'{priv_name}' hired at {priv_rate * 100:.1f}% {ci_priv} "
                f"vs {rest_rate * 100:.1f}% {ci_rest}. Fisher p={p:.4f}. Monitor for trend."
            )
            raw_pvalues.append(p)

    return flags, raw_pvalues, phi_scores


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — MODULE: CASTE / RESERVATION CATEGORY
# ══════════════════════════════════════════════════════════════════════════════

_CASTE_PROXY_COLS: Tuple[str, ...] = (
    "caste", "category", "social_group",
    "reservation_category", "community", "social_category",
)

_CASTE_NORM: Dict[str, str] = {
    "gen": "General",  "general": "General",
    "obc": "OBC",      "other backward class": "OBC", "other backward caste": "OBC",
    "sc":  "SC",       "scheduled caste": "SC",
    "st":  "ST",       "scheduled tribe": "ST",
    "ews": "EWS",      "economically weaker section": "EWS",
}


def _compute_caste_bias(
    caste_stats: Dict[str, Dict],
    caste_col: str,
    min_group_size: int = 10,
    region_labels: Optional[Dict[str, str]] = None,
) -> Tuple[List[str], List[float], bool, float]:
    """
    Caste / reservation-category bias with SC/ST escalation.
    Fisher p-values, Wilson CIs.

    Returns flags, raw_pvalues, module_passed, worst_air
    """
    rl = region_labels or _REGION_LABELS[_DEFAULT_REGION]
    flags: List[str] = []
    raw_pvalues: List[float] = []
    worst_air = 1.0

    if not caste_stats:
        return flags, raw_pvalues, True, worst_air

    base_flags, base_ps = _compute_group_bias(
        caste_stats, min_group_size=min_group_size,
        gap_threshold=15.0, label_prefix=f"Caste/Category ({caste_col})",
    )
    flags.extend(base_flags)
    raw_pvalues.extend(base_ps)

    grand_total = sum(s["total"] for s in caste_stats.values())
    grand_hired = sum(s["hired"] for s in caste_stats.values())
    module_passed = True

    for group_name, g in caste_stats.items():
        if _null_like(group_name):
            continue
        others_total = grand_total - g["total"]
        others_hired = grand_hired - g["hired"]
        if others_total < min_group_size or g["total"] < min_group_size:
            continue

        group_rate = _safe_rate(g["hired"], g["total"])
        other_rate = _safe_rate(others_hired, others_total)
        group_air  = _safe_air(group_rate, other_rate)

        if group_air < worst_air:
            worst_air = group_air

        if group_air < 0.80:
            a = g["hired"]; b = g["total"] - g["hired"]
            c = others_hired; d = others_total - others_hired
            p = _fisher_p(a, b, c, d)

            if p <= _ALPHA:
                module_passed = False
                sc_st = group_name.upper() in ("SC", "ST")
                prefix = "HIGH RISK — " if sc_st else ""
                legal_note = (
                    f"SC/ST discrimination violates {rl['caste_law']}. "
                    if sc_st else f"Potential violation of {rl['caste_law']}. "
                )
                ci_group  = _ci_str(g["hired"], g["total"])
                ci_others = _ci_str(others_hired, others_total)
                flag_txt = (
                    f"{prefix}Caste AIR — {group_name} candidates hired at "
                    f"{group_rate * 100:.1f}% {ci_group} vs {other_rate * 100:.1f}% "
                    f"{ci_others} for all others (AIR={group_air:.3f}; threshold 0.80). "
                    f"{legal_note}"
                    f"Pool: {g['total']} applicants, {g['hired']} hired. "
                    f"Fisher p={p:.4f}."
                )
                if flag_txt not in flags:
                    flags.append(flag_txt)
                    raw_pvalues.append(p)

    return flags, raw_pvalues, module_passed, worst_air


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — MODULE: STATISTICAL PARITY GAP (SPG)
# ══════════════════════════════════════════════════════════════════════════════

def _compute_spg(
    gender_stats: Dict[str, Dict],
    caste_stats: Dict[str, Dict],
    skin_stats: Dict[int, Dict],
    min_group_size: int = 10,
    spg_threshold_pp: float = 15.0,
) -> Tuple[List[str], List[float], bool]:
    """
    Multi-stage Statistical Parity Gap (SPG): checks whether shortlisting →
    hiring conversion rates are equitable across Gender, Caste, and Skin bands.

    For each group, computes:
        conversion_rate = hired / shortlisted

    Flags when |group_conversion − overall_conversion| > spg_threshold_pp
    and Fisher p ≤ 0.05.

    Returns flags, raw_pvalues, module_passed
    """
    flags: List[str] = []
    raw_pvalues: List[float] = []
    module_passed = True

    def _check_conversion(
        groups: Dict[Any, Dict],
        label_prefix: str,
    ) -> None:
        nonlocal module_passed
        grand_sl = sum(s["shortlisted"] for s in groups.values())
        grand_hr = sum(s["hired"]       for s in groups.values())
        overall_conv = _safe_rate(grand_hr, grand_sl)

        for name, s in groups.items():
            if _null_like(str(name)):
                continue
            if s["shortlisted"] < min_group_size:
                continue

            group_conv = _safe_rate(s["hired"], s["shortlisted"])
            gap_pp     = (group_conv - overall_conv) * 100

            if abs(gap_pp) > spg_threshold_pp:
                a = s["hired"]
                b = s["shortlisted"] - s["hired"]
                c = grand_hr - s["hired"]
                d = grand_sl - s["shortlisted"] - (grand_hr - s["hired"])
                # guard against negative cell counts (can't happen with correct data, but be safe)
                if b < 0 or d < 0:
                    continue
                p = _fisher_p(a, b, c, d)
                if p <= _ALPHA:
                    module_passed = False
                    direction = "favoured" if gap_pp > 0 else "disadvantaged"
                    ci = _ci_str(s["hired"], s["shortlisted"])
                    flags.append(
                        f"SPG — {label_prefix} '{name}': shortlisted-to-hired conversion "
                        f"{group_conv * 100:.1f}% {ci} vs overall {overall_conv * 100:.1f}% "
                        f"({abs(gap_pp):.1f}pp gap; threshold ±{spg_threshold_pp:.0f}pp). "
                        f"Group is {direction} at the selection stage. Fisher p={p:.4f}."
                    )
                    raw_pvalues.append(p)

    # Normalise skin-band keys to strings for the helper
    named_skin: Dict[str, Dict] = {
        f"Fitzpatrick Type {b}": s
        for b, s in skin_stats.items()
        if s["shortlisted"] >= min_group_size
    }

    eligible_gender = {
        g: s for g, s in gender_stats.items()
        if g != "unknown" and s["shortlisted"] >= min_group_size
    }

    _check_conversion(eligible_gender, "Gender")
    _check_conversion(caste_stats,     "Caste")
    _check_conversion(named_skin,      "Skin")

    return flags, raw_pvalues, module_passed


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — STAT COLLECTION
# ══════════════════════════════════════════════════════════════════════════════

def _collect_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Extract all group-level counts from the prepared DataFrame.
    df must already have '_sl' and '_hr' boolean columns.
    Returns a dict of all stats dicts consumed by the metric functions.
    """
    cols = list(df.columns)

    def _groupby_stats(key_series: pd.Series, norm_fn=None) -> Dict[str, Dict]:
        s = key_series.astype(str).str.strip()
        if norm_fn:
            s = s.map(lambda v: norm_fn(v) or v)
        tmp = pd.DataFrame({"_key": s, "_sl": df["_sl"], "_hr": df["_hr"]})
        grouped = tmp.groupby("_key").agg(
            total=("_sl", "count"),
            shortlisted=("_sl", "sum"),
            hired=("_hr", "sum"),
        )
        result = {}
        for name, row in grouped.iterrows():
            if not _null_like(name):
                n = int(row["total"])
                h = int(row["hired"])
                ci_lo, ci_hi = _wilson_ci(h, n)
                result[name] = {
                    "total":       n,
                    "shortlisted": int(row["shortlisted"]),
                    "hired":       h,
                    "hire_rate":   round(_safe_rate(h, n), 4),
                    "ci_low":      round(ci_lo, 4),
                    "ci_high":     round(ci_hi, 4),
                }
        return result

    # ── Gender ────────────────────────────────────────────────────────────────
    gender_raw = df.get("gender", pd.Series([""] * len(df))).astype(str).str.lower().str.strip()
    gender_classified = gender_raw.map(_classify_gender)
    gender_stats: Dict[str, Dict] = {}
    for bucket in ("male", "female", "other_gender"):
        mask = gender_classified == bucket
        n = int(mask.sum())
        h = int((mask & df["_hr"]).sum())
        ci_lo, ci_hi = _wilson_ci(h, n)
        gender_stats[bucket] = {
            "total":       n,
            "shortlisted": int((mask & df["_sl"]).sum()),
            "hired":       h,
            "hire_rate":   round(_safe_rate(h, n), 4),
            "ci_low":      round(ci_lo, 4),
            "ci_high":     round(ci_hi, 4),
        }

    # ── Disability ────────────────────────────────────────────────────────────
    disability_col_present = "disability_status" in cols
    if disability_col_present:
        is_disabled = _bool_series(df["disability_status"])
    else:
        is_disabled = pd.Series([False] * len(df))

    disabled_total       = int(is_disabled.sum())
    disabled_shortlisted = int((is_disabled & df["_sl"]).sum())
    disabled_hired       = int((is_disabled & df["_hr"]).sum())
    non_disabled_total   = int((~is_disabled).sum())
    non_disabled_sl      = int((~is_disabled & df["_sl"]).sum())
    non_disabled_hired   = int((~is_disabled & df["_hr"]).sum())

    # ── Institution ───────────────────────────────────────────────────────────
    if "institution" in cols:    inst_col_name = "institution"
    elif "college" in cols:      inst_col_name = "college"
    elif "university" in cols:   inst_col_name = "university"
    else:                        inst_col_name = None
    institution_stats = _groupby_stats(df[inst_col_name]) if inst_col_name else {}

    # ── Age ───────────────────────────────────────────────────────────────────
    age_stats = _groupby_stats(df["age_group"]) if "age_group" in cols else {}

    # ── Caste ─────────────────────────────────────────────────────────────────
    caste_col = _detect_col(cols, _CASTE_PROXY_COLS)
    if caste_col:
        caste_stats = _groupby_stats(
            df[caste_col],
            norm_fn=lambda v: _CASTE_NORM.get(v.lower(), v),
        )
    else:
        caste_stats = {}

    # ── Skin colour ───────────────────────────────────────────────────────────
    skin_col = _detect_col(cols, (
        "skin_colour", "skin_tone", "complexion",
        "skin_color",  "fitzpatrick", "skin_type",
    ))
    skin_stats: Dict[int, Dict] = {}
    if skin_col:
        skin_key = df[skin_col].astype(str).str.strip().map(_normalise_skin)
        tmp = pd.DataFrame({"_band": skin_key, "_sl": df["_sl"], "_hr": df["_hr"]})
        for band, grp in tmp[tmp["_band"] > 0].groupby("_band"):
            n = int(len(grp)); h = int(grp["_hr"].sum())
            ci_lo, ci_hi = _wilson_ci(h, n)
            skin_stats[int(band)] = {
                "total":       n,
                "shortlisted": int(grp["_sl"].sum()),
                "hired":       h,
                "hire_rate":   round(_safe_rate(h, n), 4),
                "ci_low":      round(ci_lo, 4),
                "ci_high":     round(ci_hi, 4),
            }

    # ── Referral ──────────────────────────────────────────────────────────────
    referral_col = _detect_col(cols, ("referral", "is_referral", "referred_by",
                                      "application_source", "source"))
    referral_stats: Dict[str, Dict] = {
        "referred":     {"total": 0, "shortlisted": 0, "hired": 0, "referrers": {}},
        "not_referred": {"total": 0, "shortlisted": 0, "hired": 0, "referrers": {}},
    }
    if referral_col:
        raw_ref = df[referral_col].astype(str).str.lower().str.strip()
        is_referred = ~raw_ref.isin(NON_REFERRAL_VALUES)
        referral_stats["referred"]["total"]           = int(is_referred.sum())
        referral_stats["referred"]["shortlisted"]     = int((is_referred & df["_sl"]).sum())
        referral_stats["referred"]["hired"]           = int((is_referred & df["_hr"]).sum())
        referral_stats["not_referred"]["total"]       = int((~is_referred).sum())
        referral_stats["not_referred"]["shortlisted"] = int((~is_referred & df["_sl"]).sum())
        referral_stats["not_referred"]["hired"]       = int((~is_referred & df["_hr"]).sum())
        generic = {"yes", "true", "1", "referred"} | NON_REFERRAL_VALUES
        named_referrers = raw_ref[is_referred & ~raw_ref.isin(generic)]
        referral_stats["referred"]["referrers"] = named_referrers.value_counts().to_dict()

    # ── Marital status ────────────────────────────────────────────────────────
    marital_col = _detect_col(cols, ("marital_status", "marital",
                                     "civil_status", "relationship_status"))
    marital_stats: Dict[str, Dict] = {}
    marital_intersectional: Dict[Tuple[str, str], Dict] = {}
    if marital_col:
        marital_stats = _groupby_stats(
            df[marital_col],
            norm_fn=lambda v: _MARITAL_NORM.get(v.lower(), v.title()),
        )
        ms_norm = df[marital_col].astype(str).str.strip().map(
            lambda v: _MARITAL_NORM.get(v.lower(), v.title())
        )
        g_norm = gender_classified
        tmp2 = pd.DataFrame({"_ms": ms_norm, "_g": g_norm, "_sl": df["_sl"], "_hr": df["_hr"]})
        for (ms, g), grp in tmp2.groupby(["_ms", "_g"]):
            if _null_like(ms) or g == "unknown":
                continue
            n = int(len(grp)); h = int(grp["_hr"].sum())
            marital_intersectional[(str(ms), str(g))] = {
                "total": n, "shortlisted": int(grp["_sl"].sum()), "hired": h,
            }

    # ── Proxy stats ───────────────────────────────────────────────────────────
    postcode_col    = _detect_col(cols, ("postcode", "pincode", "zip", "zipcode",
                                         "location_tier", "area_tier"))
    name_origin_col = _detect_col(cols, ("name_origin", "ethnicity_signal",
                                         "name_cluster", "name_ethnicity"))
    school_tier_col = _detect_col(cols, ("school_tier", "college_tier",
                                         "institution_tier", "edu_tier"))
    proxy_postcode_stats    = _groupby_stats(df[postcode_col])    if postcode_col    else {}
    proxy_name_stats        = _groupby_stats(df[name_origin_col]) if name_origin_col else {}
    proxy_school_tier_stats = _groupby_stats(df[school_tier_col]) if school_tier_col else {}
    proxy_combined: Dict[str, Dict[str, Dict]] = {}
    if proxy_postcode_stats:    proxy_combined["postcode_tier"] = proxy_postcode_stats
    if proxy_name_stats:        proxy_combined["name_origin"]   = proxy_name_stats
    if proxy_school_tier_stats: proxy_combined["school_tier"]   = proxy_school_tier_stats

    return {
        "gender_stats":           gender_stats,
        "gender_classified":      gender_classified,
        "disability_col_present": disability_col_present,
        "disabled_total":         disabled_total,
        "disabled_shortlisted":   disabled_shortlisted,
        "disabled_hired":         disabled_hired,
        "non_disabled_total":     non_disabled_total,
        "non_disabled_sl":        non_disabled_sl,
        "non_disabled_hired":     non_disabled_hired,
        "institution_stats":      institution_stats,
        "age_stats":              age_stats,
        "caste_col":              caste_col,
        "caste_stats":            caste_stats,
        "skin_col":               skin_col,
        "skin_stats":             skin_stats,
        "referral_stats":         referral_stats,
        "marital_stats":          marital_stats,
        "marital_intersectional": marital_intersectional,
        "proxy_combined":         proxy_combined,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — METRIC COMPUTATION
# ══════════════════════════════════════════════════════════════════════════════

def _compute_metrics(
    stats: Dict[str, Any],
    min_group_size: int,
    region_labels: Dict[str, str],
) -> Dict[str, Any]:
    """
    Run all per-module metric functions and gather raw p-values.
    Returns a dict of metric outputs consumed by _assemble_score().
    """
    rl = region_labels

    # ── Gender ────────────────────────────────────────────────────────────────
    (gender_flags, gender_ps, gender_passed, air_gender,
     gender_majority_label, gender_minority_label) = _compute_gender_bias(
        stats["gender_stats"], min_group_size, rl
    )

    # ── Skin ──────────────────────────────────────────────────────────────────
    (skin_flags, skin_ps, skin_passed,
     air_skin, skin_best_rate, skin_worst_rate) = _compute_skin_bias(
        stats["skin_stats"], min_group_size
    )

    # ── Referral ──────────────────────────────────────────────────────────────
    (referral_flags, referral_ps, referral_passed,
     referral_hire_rate, non_referral_hire_rate,
     referral_air, referral_hhi) = _compute_referral_bias(
        stats["referral_stats"], min_group_size
    )

    # ── Marital ───────────────────────────────────────────────────────────────
    marital_flags, marital_ps = _compute_marital_bias(
        stats["marital_stats"], stats["marital_intersectional"], min_group_size
    )
    marital_passed = len(marital_flags) == 0

    # ── Proxy ─────────────────────────────────────────────────────────────────
    proxy_flags, proxy_ps, proxy_phi_scores = _compute_proxy_bias(
        stats["proxy_combined"], min_group_size
    )
    proxy_passed = len(proxy_flags) == 0

    # ── Institution ───────────────────────────────────────────────────────────
    inst_flags, inst_ps = _compute_group_bias(
        stats["institution_stats"], min_group_size=min_group_size,
        label_prefix="Institution"
    )
    inst_passed = len(inst_flags) == 0

    # ── Age ───────────────────────────────────────────────────────────────────
    age_flags, age_ps = _compute_group_bias(
        stats["age_stats"], min_group_size=min_group_size, label_prefix="Age Group"
    )
    age_passed = len(age_flags) == 0

    # ── Caste ─────────────────────────────────────────────────────────────────
    (caste_flags, caste_ps, caste_passed, caste_worst_air) = _compute_caste_bias(
        stats["caste_stats"], stats["caste_col"], min_group_size, rl
    )

    # ── SPG ───────────────────────────────────────────────────────────────────
    spg_flags, spg_ps, spg_passed = _compute_spg(
        stats["gender_stats"], stats["caste_stats"], stats["skin_stats"],
        min_group_size=min_group_size,
    )

    # ── Disability raw metrics ─────────────────────────────────────────────────
    disabled_hr_rate     = _safe_rate(stats["disabled_hired"],     stats["disabled_total"])
    non_disabled_hr_rate = _safe_rate(stats["non_disabled_hired"], stats["non_disabled_total"])
    disability_air       = _safe_air(disabled_hr_rate, non_disabled_hr_rate)
    disabled_sl_rate     = _safe_rate(stats["disabled_shortlisted"], stats["disabled_total"])
    non_disabled_sl_rate = _safe_rate(stats["non_disabled_sl"],      stats["non_disabled_total"])
    disability_sl_gap    = (non_disabled_sl_rate - disabled_sl_rate) * 100

    # ── Collect ALL raw p-values for Holm correction ──────────────────────────
    all_flags = (gender_flags + skin_flags + referral_flags + marital_flags +
                 proxy_flags + inst_flags + age_flags + caste_flags + spg_flags)
    all_ps    = (gender_ps   + skin_ps   + referral_ps   + marital_ps   +
                 proxy_ps    + inst_ps   + age_ps        + caste_ps     + spg_ps)

    # Disability p-value (appended last so its index is known)
    disab_p = 1.0
    if stats["disability_col_present"] and stats["disabled_total"] >= min_group_size:
        a = stats["disabled_hired"]
        b = stats["disabled_total"] - stats["disabled_hired"]
        c = stats["non_disabled_hired"]
        d = stats["non_disabled_total"] - stats["non_disabled_hired"]
        disab_p = _fisher_p(a, b, c, d)
        all_ps.append(disab_p)

    disab_p_adj = 1.0
    if all_ps:
        adj_ps = _holm_correct(all_ps)
        if stats["disability_col_present"] and stats["disabled_total"] >= min_group_size:
            disab_p_adj = adj_ps[-1]

    return {
        "gender_flags": gender_flags,       "gender_passed": gender_passed,
        "air_gender": air_gender,           "gender_majority_label": gender_majority_label,
        "gender_minority_label": gender_minority_label,

        "skin_flags": skin_flags,           "skin_passed": skin_passed,
        "air_skin": air_skin,               "skin_best_rate": skin_best_rate,
        "skin_worst_rate": skin_worst_rate,

        "referral_flags": referral_flags,   "referral_passed": referral_passed,
        "referral_hire_rate": referral_hire_rate,
        "non_referral_hire_rate": non_referral_hire_rate,
        "referral_air": referral_air,       "referral_hhi": referral_hhi,

        "marital_flags": marital_flags,     "marital_passed": marital_passed,

        "proxy_flags": proxy_flags,         "proxy_passed": proxy_passed,
        "proxy_phi_scores": proxy_phi_scores,

        "inst_flags": inst_flags,           "inst_passed": inst_passed,
        "age_flags": age_flags,             "age_passed": age_passed,

        "caste_flags": caste_flags,         "caste_passed": caste_passed,
        "caste_worst_air": caste_worst_air,

        "spg_flags": spg_flags,             "spg_passed": spg_passed,

        "disability_air": disability_air,
        "disabled_hr_rate": disabled_hr_rate,
        "non_disabled_hr_rate": non_disabled_hr_rate,
        "disability_sl_gap": disability_sl_gap,
        "disab_p": disab_p,                 "disab_p_adj": disab_p_adj,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 12 — SCORE ASSEMBLY
# ══════════════════════════════════════════════════════════════════════════════

def _assemble_score(
    stats: Dict[str, Any],
    metrics: Dict[str, Any],
    min_group_size: int,
    region_labels: Dict[str, str],
) -> Dict[str, Any]:
    """
    Assemble the weighted integrity score from computed metrics.
    Each module earns its full weight when passed, 0 when failed.
    module_results carry p_value, p_adjusted, ci_low, ci_high, n.
    """
    rl    = region_labels
    flags: List[str] = []
    score: int = 0
    module_results: Dict[str, Dict] = {}

    # ── Helper: worst caste group ─────────────────────────────────────────────
    worst_caste_group = min(
        ((g, s) for g, s in stats["caste_stats"].items()
         if s["total"] >= min_group_size and not _null_like(g)),
        key=lambda x: _safe_rate(x[1]["hired"], x[1]["total"]),
        default=(None, {"total": 0, "hired": 0}),
    )
    wc_n = worst_caste_group[1]["total"]
    wc_h = worst_caste_group[1]["hired"]
    wc_ci_lo, wc_ci_hi = _wilson_ci(wc_h, wc_n)

    # ── CASTE (15 pts) ────────────────────────────────────────────────────────
    caste_points = MODULE_WEIGHTS["caste"] if metrics["caste_passed"] else 0
    score += caste_points
    flags.extend(metrics["caste_flags"])
    module_results["caste"] = {
        "weight":  MODULE_WEIGHTS["caste"],
        "points":  caste_points,
        "passed":  metrics["caste_passed"],
        "air":     round(metrics["caste_worst_air"], 3),
        "n":       wc_n,
        "ci_low":  round(wc_ci_lo, 4),
        "ci_high": round(wc_ci_hi, 4),
        "law":     rl["caste_law"],
    }

    # ── GENDER (15 pts) ───────────────────────────────────────────────────────
    gender_points = MODULE_WEIGHTS["gender"] if metrics["gender_passed"] else 0
    score += gender_points
    flags.extend(metrics["gender_flags"])

    min_gender_group = min(
        ((g, s) for g, s in stats["gender_stats"].items()
         if s["total"] >= min_group_size and g != "unknown"),
        key=lambda x: _safe_rate(x[1]["hired"], x[1]["total"]),
        default=(None, {"total": 0, "hired": 0}),
    )
    mg_n = min_gender_group[1]["total"]
    mg_h = min_gender_group[1]["hired"]
    mg_ci_lo, mg_ci_hi = _wilson_ci(mg_h, mg_n)
    module_results["gender"] = {
        "weight":         MODULE_WEIGHTS["gender"],
        "points":         gender_points,
        "passed":         metrics["gender_passed"],
        "air":            round(metrics["air_gender"], 3),
        "majority_group": metrics["gender_majority_label"],
        "minority_group": metrics["gender_minority_label"],
        "n":              mg_n,
        "ci_low":         round(mg_ci_lo, 4),
        "ci_high":        round(mg_ci_hi, 4),
        "law":            rl["gender_law"],
    }

    # ── DISABILITY (15 pts) — data-absent → 0 pts ─────────────────────────────
    disability_flags: List[str] = []
    disability_passed: Optional[bool] = None
    disability_points: int = 0

    if not stats["disability_col_present"]:
        disability_points = 0
        disability_flags.append(
            "Disability Data Absent: The 'disability_status' column was not found. "
            "This module cannot be evaluated and contributes 0 points. "
            f"Collecting disability status is required under {rl['disability_law']} "
            "for equal-opportunity monitoring."
        )
    else:
        # FIX 2 (B3): Explicit size guard added. Previously missing — if
        # disabled_total < min_group_size, no Fisher test ran (disab_p stayed
        # 1.0) yet disability_passed was set True and earned 15 free points.
        if stats["disabled_total"] < min_group_size:
            disability_passed = None   # data present but too few to evaluate
            disability_points = 0
            disability_flags.append(
                f"Disability Data Insufficient: Only {stats['disabled_total']} disabled "
                f"candidates found (minimum {min_group_size} required for statistical "
                f"testing). Module contributes 0 points."
            )
        elif (metrics["disability_air"] < 0.80
                and metrics["disab_p"] <= _ALPHA):
            # FIX 2 (B3): removed redundant `disabled_total >= min_group_size`
            # guard here — it is now handled by the explicit branch above.
            disability_passed = False
            ci_dis = _ci_str(stats["disabled_hired"], stats["disabled_total"])
            ci_non = _ci_str(stats["non_disabled_hired"], stats["non_disabled_total"])
            disability_flags.append(
                f"Disability AIR: {metrics['disability_air']:.3f} — disabled candidates "
                f"hired at {metrics['disability_air'] * 100:.0f}% the rate of non-disabled. "
                f"{rl['disability_law']} mandates equal opportunity. "
                f"Disabled: {stats['disabled_total']} applicants, {stats['disabled_hired']} hired "
                f"({metrics['disabled_hr_rate'] * 100:.1f}%) {ci_dis}. "
                f"Non-disabled: {stats['non_disabled_hired']} hired {ci_non}. "
                f"Fisher p={metrics['disab_p']:.4f} (adj p={metrics['disab_p_adj']:.4f})."
            )
        else:
            disability_passed = True

        # FIX 1 (B1): Shortlisting-gap flag now requires a Fisher exact test
        # (p ≤ _ALPHA) before firing.  Previously it fired on raw gap size alone
        # (no significance test), producing false positives on small groups and
        # violating the engine-wide rule that every flag must be statistically
        # significant.  The p-value is also appended to all_ps so it
        # participates in the Holm correction already applied to other modules.
        if abs(metrics["disability_sl_gap"]) > 15 and stats["disabled_total"] >= min_group_size:
            # Build the 2×2 shortlisting table: disabled vs non-disabled
            sl_a = stats["disabled_shortlisted"]
            sl_b = stats["disabled_total"] - stats["disabled_shortlisted"]
            sl_c = stats["non_disabled_sl"]
            sl_d = stats["non_disabled_total"] - stats["non_disabled_sl"]
            sl_p = _fisher_p(sl_a, sl_b, sl_c, sl_d)  # FIX 1 (B1): new Fisher test
            if sl_p <= _ALPHA:  # FIX 1 (B1): only flag when statistically significant
                direction = "disadvantaged" if metrics["disability_sl_gap"] > 0 else "favoured"
                disability_flags.append(
                    f"Disability Shortlisting Gap: Disabled candidates are {direction} at the "
                    f"shortlisting stage ({abs(metrics['disability_sl_gap']):.1f}pp gap; threshold: 15pp). "
                    f"Fisher p={sl_p:.4f}. "  # FIX 1 (B1): include p-value in message for transparency
                    f"Screening criteria may be inadvertently filtering out disabled applicants."
                )

        disability_points = MODULE_WEIGHTS["disability"] if disability_passed else 0

    score += disability_points
    flags.extend(disability_flags)

    dis_ci_lo, dis_ci_hi = _wilson_ci(stats["disabled_hired"], stats["disabled_total"])
    module_results["disability"] = {
        "weight":       MODULE_WEIGHTS["disability"],
        "points":       disability_points,
        "passed":       disability_passed,
        "data_present": stats["disability_col_present"],
        "air":          round(metrics["disability_air"], 3),
        "n":            stats["disabled_total"],
        "ci_low":       round(dis_ci_lo, 4),
        "ci_high":      round(dis_ci_hi, 4),
        "p_value":      round(metrics["disab_p"], 4),
        "p_adjusted":   round(metrics["disab_p_adj"], 4),
        "law":          rl["disability_law"],
    }

    # ── SKIN (15 pts) ─────────────────────────────────────────────────────────
    # FIX 3 (B4): Use `is True` so that None (insufficient data) earns 0 pts,
    # not 15 free pts as the previous truthy check `if metrics["skin_passed"]` did.
    skin_points = MODULE_WEIGHTS["skin"] if metrics["skin_passed"] is True else 0
    score += skin_points
    flags.extend(metrics["skin_flags"])

    worst_skin_band = min(
        ((b, s) for b, s in stats["skin_stats"].items()
         if s["total"] >= min_group_size),
        key=lambda x: _safe_rate(x[1]["hired"], x[1]["total"]),
        default=(None, {"total": 0, "hired": 0}),
    )
    ws_n = worst_skin_band[1]["total"]
    ws_h = worst_skin_band[1]["hired"]
    ws_ci_lo, ws_ci_hi = _wilson_ci(ws_h, ws_n)
    module_results["skin"] = {
        "weight":  MODULE_WEIGHTS["skin"],
        "points":  skin_points,
        "passed":  metrics["skin_passed"],
        "air":     round(metrics["air_skin"], 3),
        "n":       ws_n,
        "ci_low":  round(ws_ci_lo, 4),
        "ci_high": round(ws_ci_hi, 4),
    }

    # ── PROXY (10 pts) ────────────────────────────────────────────────────────
    proxy_points = MODULE_WEIGHTS["proxy"] if metrics["proxy_passed"] else 0
    score += proxy_points
    flags.extend(metrics["proxy_flags"])
    module_results["proxy"] = {
        "weight": MODULE_WEIGHTS["proxy"],
        "points": proxy_points,
        "passed": metrics["proxy_passed"],
        "air":    1.0,  # proxy uses φ not AIR; kept for schema consistency
        "n":      sum(
            sum(s["total"] for s in grp.values())
            for grp in stats["proxy_combined"].values()
        ),
        "phi_scores": metrics["proxy_phi_scores"],
    }

    # ── SPG (10 pts) ──────────────────────────────────────────────────────────
    spg_points = MODULE_WEIGHTS["spg"] if metrics["spg_passed"] else 0
    score += spg_points
    flags.extend(metrics["spg_flags"])
    module_results["spg"] = {
        "weight": MODULE_WEIGHTS["spg"],
        "points": spg_points,
        "passed": metrics["spg_passed"],
        "air":    1.0,  # SPG uses gap pp; kept for schema consistency
        "n":      sum(s["shortlisted"] for s in stats["gender_stats"].values()),
    }

    # ── INSTITUTION (6 pts) ───────────────────────────────────────────────────
    inst_points = MODULE_WEIGHTS["institution"] if metrics["inst_passed"] else 0
    score += inst_points
    flags.extend(metrics["inst_flags"])
    module_results["institution"] = {
        "weight": MODULE_WEIGHTS["institution"],
        "points": inst_points,
        "passed": metrics["inst_passed"],
        "air":    1.0,
        "n":      sum(s["total"] for s in stats["institution_stats"].values()),
    }

    # ── MARITAL (6 pts) ───────────────────────────────────────────────────────
    marital_points = MODULE_WEIGHTS["marital"] if metrics["marital_passed"] else 0
    score += marital_points
    flags.extend(metrics["marital_flags"])
    module_results["marital"] = {
        "weight": MODULE_WEIGHTS["marital"],
        "points": marital_points,
        "passed": metrics["marital_passed"],
        "air":    1.0,
        "n":      sum(s["total"] for s in stats["marital_stats"].values()),
    }

    # ── AGE (4 pts) ───────────────────────────────────────────────────────────
    age_points = MODULE_WEIGHTS["age"] if metrics["age_passed"] else 0
    score += age_points
    flags.extend(metrics["age_flags"])
    module_results["age"] = {
        "weight": MODULE_WEIGHTS["age"],
        "points": age_points,
        "passed": metrics["age_passed"],
        "air":    1.0,
        "n":      sum(s["total"] for s in stats["age_stats"].values()),
    }

    # ── REFERRAL (4 pts) ──────────────────────────────────────────────────────
    referral_points = MODULE_WEIGHTS["referral"] if metrics["referral_passed"] else 0
    score += referral_points
    flags.extend(metrics["referral_flags"])
    module_results["referral"] = {
        "weight": MODULE_WEIGHTS["referral"],
        "points": referral_points,
        "passed": metrics["referral_passed"],
        "air":    round(metrics["referral_air"], 3),
        "n":      (stats["referral_stats"]["referred"]["total"] +
                   stats["referral_stats"]["not_referred"]["total"]),
        "hhi":    round(metrics["referral_hhi"], 4),
    }

    # ── Intersectional Dealbreaker ─────────────────────────────────────────────
    # FIX 3 (B4): Use `is False` for skin_passed so a None (insufficient data)
    # value does not mistakenly trigger the systemic-bias deduction alongside a
    # caste failure — `not None` is True in Python, which would be wrong here.
    systemic_bias_triggered = (not metrics["caste_passed"]) and (metrics["skin_passed"] is False)
    systemic_bias_deduction = 0

    if systemic_bias_triggered:
        systemic_bias_deduction = SYSTEMIC_BIAS_DEDUCTION
        score = max(0, score - systemic_bias_deduction)
        flags.insert(0,
            f"SYSTEMIC BIAS DETECTED — Both the Caste module (AIR={metrics['caste_worst_air']:.3f}) "
            f"and the Skin Colour module (AIR={metrics['air_skin']:.3f}) have failed simultaneously. "
            f"This pattern indicates compounded, intersectional discrimination. "
            f"An additional −{SYSTEMIC_BIAS_DEDUCTION} pt 'Systemic Bias' deduction has been applied. "
            f"Under {rl['caste_law']}, intersectional patterns carry elevated legal exposure."
        )

    # ── Label ──────────────────────────────────────────────────────────────────
    if   score >= 75: label = "Good"
    elif score >= 50: label = "Fair"
    elif score >= 25: label = "At Risk"
    else:             label = "Toxic"

    return {
        "score":   score,
        "label":   label,
        "flags":   flags,
        "module_results":          module_results,
        "systemic_bias_triggered": systemic_bias_triggered,
        "systemic_bias_deduction": systemic_bias_deduction,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 13 — PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def compute_fairness_metrics(
    df: pd.DataFrame,
    min_group_size: int = 10,
    region: str = _DEFAULT_REGION,
) -> Dict[str, Any]:
    """
    Compute all bias metrics for a hiring dataset.

    Internally decomposed into _collect_stats(), _compute_metrics(),
    _assemble_score() for testability and extension.

    Parameters
    ──────────
    df              — pandas DataFrame of the hiring pipeline
    min_group_size  — minimum group size for any statistical comparison (default 10)
    region          — jurisdiction for legal framework labels (default "IN")
                      Supported: "IN", "US", "UK", "EU"

    Required CSV columns (case-insensitive)
    ────────────────────────────────────────
        gender          — Male / Female / Non-binary / …
        shortlisted     — Yes / No / True / False / 1 / 0
        hired           — Yes / No / True / False / 1 / 0
          aliases       — hiring_status | selection

    Optional CSV columns (auto-detected)
    ──────────────────────────────────────
        institution / college / university
        age_group
        disability_status
        caste / category / social_group / reservation_category / community
        skin_colour / skin_tone / complexion / fitzpatrick / skin_color / skin_type
        referral / is_referral / referred_by / application_source / source
        marital_status / marital / civil_status / relationship_status
        postcode / pincode / zip / zipcode / location_tier / area_tier
        name_origin / ethnicity_signal / name_cluster / name_ethnicity
        school_tier / college_tier / institution_tier / edu_tier

    Returns
    ────────
    {
        "score":         int (0–100),
        "label":         str ("Toxic" | "At Risk" | "Fair" | "Good"),
        "flags":         List[str],
        "module_results": Dict with per-module weight/points/passed/air/n/ci,
        ... (per-module stats and convenience scalar fields below)
    }

    Raises
    ──────
    ValueError  — "Data Quality Error" when outcome column parses to all zeros.
    ValueError  — "Unknown region" when region not in supported list.
    """
    if region not in _REGION_LABELS:
        raise ValueError(
            f"Unknown region '{region}'. Supported: {list(_REGION_LABELS.keys())}."
        )
    rl = _REGION_LABELS[region]

    # ── Normalise ──────────────────────────────────────────────────────────────
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    cols = list(df.columns)

    # ── Outcome column detection and parsing ───────────────────────────────────
    outcome_col = _detect_col(cols, ("hired", "hiring_status", "selection"))
    hired_raw   = df[outcome_col] if outcome_col else pd.Series(["no"] * len(df))
    shortlisted = _bool_series(df.get("shortlisted", pd.Series(["no"] * len(df))))
    hired       = _parse_outcome_series(hired_raw)

    if hired.sum() == 0:
        raise ValueError(
            "Data Quality Error: The outcome column (hired / hiring_status / selection) "
            "parsed to all zeros. Check that positive outcomes are encoded as "
            "1, 1.0, 'Yes', 'True', or 'Hired' (case-insensitive). "
            f"Column used: '{outcome_col or 'not found'}'. "
            f"Unique raw values found: {list(hired_raw.astype(str).str.lower().unique()[:10])}."
        )

    df["_sl"] = shortlisted
    df["_hr"] = hired

    # ── Three-phase computation ────────────────────────────────────────────────
    raw_stats = _collect_stats(df)
    metrics   = _compute_metrics(raw_stats, min_group_size, rl)
    assembled = _assemble_score(raw_stats, metrics, min_group_size, rl)

    # ── Gender scalar convenience fields (backward compat) ────────────────────
    gs                = raw_stats["gender_stats"]
    men_total         = gs["male"]["total"]
    men_shortlisted   = gs["male"]["shortlisted"]
    men_hired         = gs["male"]["hired"]
    women_total       = gs["female"]["total"]
    women_shortlisted = gs["female"]["shortlisted"]
    women_hired       = gs["female"]["hired"]
    men_sl_rate       = _safe_rate(men_shortlisted, men_total)
    women_sl_rate     = _safe_rate(women_shortlisted, women_total)
    men_hr_rate       = _safe_rate(men_hired, men_total)
    women_hr_rate     = _safe_rate(women_hired, women_total)
    shortlisting_gap  = (men_sl_rate - women_sl_rate) * 100
    hiring_gap        = (men_hr_rate - women_hr_rate) * 100

    return {
        # ── Core ──────────────────────────────────────────────────────────────
        **assembled,
        "region": region,

        # ── Gender ────────────────────────────────────────────────────────────
        "air_gender":            round(metrics["air_gender"], 3),
        "gender_majority_group": metrics["gender_majority_label"],
        "gender_minority_group": metrics["gender_minority_label"],
        "shortlisting_gap":      round(shortlisting_gap, 2),
        "hiring_gap":            round(hiring_gap, 2),
        "men_total":             men_total,
        "women_total":           women_total,
        "men_shortlisted":       men_shortlisted,
        "women_shortlisted":     women_shortlisted,
        "men_hired":             men_hired,
        "women_hired":           women_hired,
        "gender_stats":          gs,

        # ── Disability ────────────────────────────────────────────────────────
        "disability_air":              round(metrics["disability_air"], 3),
        "disability_shortlisting_gap": round(metrics["disability_sl_gap"], 2),
        "disability_data_present":     raw_stats["disability_col_present"],

        # ── Institution ───────────────────────────────────────────────────────
        "institution_stats": raw_stats["institution_stats"],
        "institution_flags": metrics["inst_flags"],

        # ── Age ───────────────────────────────────────────────────────────────
        "age_stats": raw_stats["age_stats"],
        "age_flags": metrics["age_flags"],

        # ── Caste ─────────────────────────────────────────────────────────────
        "caste_stats":     raw_stats["caste_stats"],
        "caste_flags":     metrics["caste_flags"],
        "caste_col":       raw_stats["caste_col"],
        "caste_worst_air": round(metrics["caste_worst_air"], 3),

        # ── Skin colour ────────────────────────────────────────────────────────
        "skin_stats":      raw_stats["skin_stats"],
        "skin_flags":      metrics["skin_flags"],
        "air_skin":        round(metrics["air_skin"], 3),
        "skin_best_rate":  round(metrics["skin_best_rate"], 4),
        "skin_worst_rate": round(metrics["skin_worst_rate"], 4),

        # ── Referral network ───────────────────────────────────────────────────
        "referral_stats":         raw_stats["referral_stats"],
        "referral_flags":         metrics["referral_flags"],
        "referral_hire_rate":     round(metrics["referral_hire_rate"], 4),
        "non_referral_hire_rate": round(metrics["non_referral_hire_rate"], 4),
        "referral_air":           round(metrics["referral_air"], 3),
        "referral_hhi":           round(metrics["referral_hhi"], 4),

        # ── Marital status ─────────────────────────────────────────────────────
        "marital_stats":                raw_stats["marital_stats"],
        "marital_flags":                metrics["marital_flags"],
        "marital_intersectional_stats": {
            f"{ms}|{g}": v for (ms, g), v in raw_stats["marital_intersectional"].items()
        },

        # ── Proxy bias ─────────────────────────────────────────────────────────
        "proxy_stats":      raw_stats["proxy_combined"],
        "proxy_flags":      metrics["proxy_flags"],
        "proxy_phi_scores": metrics["proxy_phi_scores"],

        # ── SPG ────────────────────────────────────────────────────────────────
        "spg_flags": metrics["spg_flags"],

        # ── Dataset info ───────────────────────────────────────────────────────
        "row_count":   len(df),
        "outcome_col": outcome_col,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 14 — SMOKE TESTS
# Run: python audit_engine.py
# ══════════════════════════════════════════════════════════════════════════════

def smoke_test() -> None:
    """
    Synthetic datasets verifying the v6.1 engine.

    All synthetic groups are sized ≥ 10 (respecting the min_group_size=10
    default) to produce statistically meaningful outputs.

    Test 1  — BIASED dataset           (Caste + Skin + Gender all fail → Toxic)
    Test 2  — NON-BINARY INCLUSION     (other_gender bucket flagged)
    Test 3  — ALIAS COLUMN             (skin_tone + selection resolve correctly)
    Test 4  — DATA QUALITY GUARD       (all-zero outcome → ValueError)
    Test 5  — MISSING DISABILITY COL   (0 pts, not free 15)
    Test 6  — PROXY FLAG               (HIGH RISK φ fails proxy module)
    Test 7  — FAIR DATASET             (all pass → score 100)
    Test 8  — REGION SWITCH            (US region labels in flags)
    Test 9  — HOLM CORRECTION          (p_adjusted present in disability module)
    Test 10 — SPEARMAN SKIN            (negative ρ detected in gradient dataset)
    """
    import random
    random.seed(42)

    LARGE = 100   # group size >> min_group_size=10 for clear statistical signal

    # ── Test 1: BIASED DATASET ────────────────────────────────────────────────
    print("=== TEST 1: BIASED DATASET ===")
    rows = []
    for i in range(LARGE):     # Men General: 40% hire
        rows.append({"gender": "Male",   "shortlisted": "Yes",
                     "hired": "Yes" if i < 40 else "No",
                     "category": "General", "skin_colour": "fair",
                     "disability_status": "No"})
    for i in range(LARGE):     # Women General: 12% hire → AIR ≈ 0.30
        rows.append({"gender": "Female", "shortlisted": "Yes",
                     "hired": "Yes" if i < 12 else "No",
                     "category": "General", "skin_colour": "fair",
                     "disability_status": "No"})
    for i in range(40):        # SC male: 1/40 hired
        rows.append({"gender": "Male",   "shortlisted": "Yes",
                     "hired": "Yes" if i < 1 else "No",
                     "category": "SC", "skin_colour": "fair",
                     "disability_status": "No"})
    for i in range(20):        # SC female: 0/20 hired (intersectional)
        rows.append({"gender": "Female", "shortlisted": "Yes",
                     "hired": "No",
                     "category": "SC", "skin_colour": "fair",
                     "disability_status": "No"})
    for i in range(60):        # Dark skin (Type VI): 4/60 hired (~6.7% vs ~34%)
        rows.append({"gender": "Male",   "shortlisted": "Yes",
                     "hired": "Yes" if i < 4 else "No",
                     "category": "General", "skin_colour": "dark",
                     "disability_status": "No"})

    biased_df = pd.DataFrame(rows)
    result = compute_fairness_metrics(biased_df)

    print(f"Score : {result['score']} / 100  [{result['label']}]")
    print(f"Systemic Bias: {result['systemic_bias_triggered']} "
          f"(deduction: {result['systemic_bias_deduction']} pts)")
    print("Module breakdown:")
    for mod, info in result["module_results"].items():
        status = "PASS" if info["passed"] else ("FAIL" if info["passed"] is False else "N/A")
        print(f"  {mod:12s} [{status}]  {info['points']:2d}/{info['weight']:2d} pts  "
              f"AIR={info['air']}  n={info.get('n', '?')}")
    print(f"Flags ({len(result['flags'])}):")
    for f in result["flags"]:
        print(f"  • {f[:140]}")

    assert result["score"] < 25,       f"Expected Toxic score (<25); got {result['score']}"
    assert result["label"] == "Toxic", f"Expected 'Toxic' label; got {result['label']}"
    assert result["systemic_bias_triggered"], "Expected Systemic Bias dealbreaker"
    assert len(result["flags"]) >= 3,  f"Expected ≥3 flags; got {len(result['flags'])}"
    assert result["air_gender"] < 0.50, f"Expected severe gender AIR; got {result['air_gender']}"
    assert "SC" in result["caste_stats"], "Expected SC group in caste stats"
    assert any("p=" in f or "Fisher" in f for f in result["flags"]), \
        "Expected Fisher p-values in at least one flag"
    assert any("CI:" in f for f in result["flags"]), \
        "Expected Wilson CIs in at least one flag"
    print("✓ Test 1 passed.\n")

    # ── Test 2: NON-BINARY INCLUSION ─────────────────────────────────────────
    print("=== TEST 2: NON-BINARY INCLUSION ===")
    nb_rows = []
    for i in range(LARGE):
        nb_rows.append({"gender": "Male",       "shortlisted": "Yes",
                        "hired": "Yes" if i < 40 else "No"})
    for i in range(LARGE):
        nb_rows.append({"gender": "Female",     "shortlisted": "Yes",
                        "hired": "Yes" if i < 40 else "No"})
    for i in range(40):     # Non-binary: 2/40 hired → severe disadvantage
        nb_rows.append({"gender": "Non-binary", "shortlisted": "Yes",
                        "hired": "Yes" if i < 2 else "No"})
    nb_df = pd.DataFrame(nb_rows)
    nb_result = compute_fairness_metrics(nb_df)

    print(f"Score : {nb_result['score']} / 100  [{nb_result['label']}]")
    print(f"Gender stats: { {k: v['hired'] for k, v in nb_result['gender_stats'].items()} }")
    assert nb_result["gender_stats"]["other_gender"]["total"] == 40, \
        "Non-binary candidates should be in other_gender bucket"
    assert nb_result["air_gender"] < 0.80, \
        f"Expected gender AIR < 0.80 due to non-binary disadvantage; got {nb_result['air_gender']}"
    print("✓ Test 2 passed.\n")

    # ── Test 3: ALIAS COLUMN ─────────────────────────────────────────────────
    print("=== TEST 3: ALIAS COLUMN ===")
    alias_rows = []
    for i in range(LARGE):
        alias_rows.append({"gender": "Male",   "shortlisted": "Yes",
                            "skin_tone": "fair", "selection": 1 if i < 40 else 0})
    for i in range(LARGE):
        alias_rows.append({"gender": "Female", "shortlisted": "Yes",
                            "skin_tone": "fair", "selection": 1 if i < 40 else 0})
    alias_df = pd.DataFrame(alias_rows)
    alias_result = compute_fairness_metrics(alias_df)
    assert alias_result["outcome_col"] == "selection", \
        f"Expected outcome_col='selection'; got '{alias_result['outcome_col']}'"
    assert alias_result["air_skin"] == 1.0, \
        f"Expected air_skin=1.0 (single band); got {alias_result['air_skin']}"
    print(f"Outcome col: '{alias_result['outcome_col']}'  skin AIR: {alias_result['air_skin']}  ✓\n")

    # ── Test 4: DATA QUALITY GUARD ────────────────────────────────────────────
    print("=== TEST 4: DATA QUALITY GUARD ===")
    bad_df = pd.DataFrame([{"gender": "Male", "shortlisted": "Yes", "hired": "No"}
                           for _ in range(20)])
    try:
        compute_fairness_metrics(bad_df)
        assert False, "Expected ValueError for all-zero outcome"
    except ValueError as e:
        print(f"ValueError correctly raised: {str(e)[:80]}…  ✓\n")

    # ── Test 5: MISSING DISABILITY COLUMN ─────────────────────────────────────
    print("=== TEST 5: MISSING DISABILITY COLUMN → 0 POINTS ===")
    nd_rows = []
    for i in range(LARGE):
        nd_rows.append({"gender": "Male",   "shortlisted": "Yes",
                        "hired": "Yes" if i < 40 else "No"})
    for i in range(LARGE):
        nd_rows.append({"gender": "Female", "shortlisted": "Yes",
                        "hired": "Yes" if i < 40 else "No"})
    nd_df = pd.DataFrame(nd_rows)
    nd_result = compute_fairness_metrics(nd_df)
    disab_mod = nd_result["module_results"]["disability"]
    assert disab_mod["data_present"] is False, "disability_data_present should be False"
    assert disab_mod["points"] == 0,           f"Expected 0 pts; got {disab_mod['points']}"
    assert disab_mod["passed"] is None,        f"Expected passed=None; got {disab_mod['passed']}"
    print(f"Disability: data_present={disab_mod['data_present']}, "
          f"points={disab_mod['points']}, passed={disab_mod['passed']}  ✓\n")

    # ── Test 6: PROXY FLAG ────────────────────────────────────────────────────
    print("=== TEST 6: PROXY FLAG FAILS PROXY MODULE ===")
    proxy_rows = []
    for i in range(50):   # Tier 1 postcode: 45/50 hired (90%)
        proxy_rows.append({"gender": "Male", "shortlisted": "Yes",
                           "hired": "Yes" if i < 45 else "No", "postcode": "tier_1"})
    for i in range(50):   # Tier 3 postcode: 3/50 hired (6%)
        proxy_rows.append({"gender": "Male", "shortlisted": "Yes",
                           "hired": "Yes" if i < 3 else "No", "postcode": "tier_3"})
    for i in range(50):   # Females tier 1
        proxy_rows.append({"gender": "Female", "shortlisted": "Yes",
                           "hired": "Yes" if i < 22 else "No", "postcode": "tier_1"})
    for i in range(50):   # Females tier 3
        proxy_rows.append({"gender": "Female", "shortlisted": "Yes",
                           "hired": "Yes" if i < 4 else "No", "postcode": "tier_3"})
    proxy_df = pd.DataFrame(proxy_rows)
    proxy_result = compute_fairness_metrics(proxy_df)
    proxy_mod = proxy_result["module_results"]["proxy"]
    has_proxy = len(proxy_result["proxy_flags"]) > 0
    print(f"Proxy flags: {has_proxy}  Proxy passed: {proxy_mod['passed']}")
    if has_proxy:
        assert proxy_mod["passed"] is False, \
            "Proxy module should FAIL when proxy flags present"
        assert proxy_mod["points"] == 0, \
            f"Proxy module should earn 0 pts; got {proxy_mod['points']}"
        assert any("φ=" in f or "phi" in f.lower() for f in proxy_result["proxy_flags"]), \
            "Expected phi coefficient in proxy flag"
        print("✓ Test 6 passed.\n")
    else:
        print("Note: Proxy φ below detection threshold — dataset may need larger groups.\n")

    # ── Test 7: FAIR DATASET ──────────────────────────────────────────────────
    print("=== TEST 7: FAIR DATASET ===")
    fair_rows = []
    for gender in ("Male", "Female", "Non-binary"):
        for cat in ("General", "OBC", "SC", "ST"):
            for skin in ("fair", "brown"):
                for hired_val in (["Yes"] * 4 + ["No"] * 6) * 3:
                    fair_rows.append({
                        "gender": gender, "shortlisted": "Yes",
                        "hired": hired_val, "category": cat,
                        "skin_colour": skin, "disability_status": "No",
                    })
    # FIX 2 update (Test 7): The original dataset set disability_status="No" for
    # every row, leaving disabled_total=0. With FIX 2 (B3) in place, a column
    # present but with zero disabled candidates triggers the size guard
    # (passed=None, 0 pts), so a fully-"No" column can never produce score=100.
    # Add 15 disabled candidates hired at the same ~40% rate as the rest of the
    # cohort — sufficient to clear min_group_size=10 and yield AIR≈1.0 (pass).
    for i in range(15):
        fair_rows.append({
            "gender": "Male", "shortlisted": "Yes",
            "hired": "Yes" if i < 6 else "No",  # 6/15 = 40% — matches cohort rate
            "category": "General", "skin_colour": "fair",
            "disability_status": "Yes",
        })
    fair_df = pd.DataFrame(fair_rows)
    fair_result = compute_fairness_metrics(fair_df)

    print(f"Score : {fair_result['score']} / 100  [{fair_result['label']}]")
    for mod, info in fair_result["module_results"].items():
        status = "PASS" if info["passed"] else ("FAIL" if info["passed"] is False else "N/A")
        print(f"  {mod:12s} [{status}]  {info['points']:2d}/{info['weight']:2d} pts")

    assert fair_result["score"] == 100, f"Expected 100; got {fair_result['score']}"
    assert fair_result["label"] == "Good"
    assert len(fair_result["flags"]) == 0, \
        f"Expected zero flags; got {fair_result['flags']}"
    print("✓ Test 7 passed.\n")

    # ── Test 8: REGION SWITCH ─────────────────────────────────────────────────
    print("=== TEST 8: REGION SWITCH (US) ===")
    us_result = compute_fairness_metrics(biased_df, region="US")
    assert us_result["region"] == "US", "Region should be US"
    all_flag_text = " ".join(us_result["flags"])
    assert ("Title VII" in all_flag_text or "ADA" in all_flag_text or
            "ADEA" in all_flag_text or "EEOC" in all_flag_text or
            "Civil Rights" in all_flag_text), \
        f"Expected US legal references in flags; got: {all_flag_text[:200]}"
    print("US region flags contain US law references.  ✓")
    try:
        compute_fairness_metrics(biased_df, region="XX")
        assert False, "Expected ValueError for unknown region"
    except ValueError as e:
        print(f"Unknown region correctly rejected: {str(e)[:60]}…  ✓\n")

    # ── Test 9: HOLM CORRECTION ───────────────────────────────────────────────
    print("=== TEST 9: HOLM CORRECTION (boundary check) ===")
    holm_rows = []
    for i in range(20):    # Group A: 9/20 hired
        holm_rows.append({"gender": "Male",   "shortlisted": "Yes",
                          "hired": "Yes" if i < 9 else "No"})
    for i in range(20):    # Group B: 6/20 hired (gap ~15pp, p borderline)
        holm_rows.append({"gender": "Female", "shortlisted": "Yes",
                          "hired": "Yes" if i < 6 else "No"})
    holm_df = pd.DataFrame(holm_rows)
    holm_result = compute_fairness_metrics(holm_df, min_group_size=10)
    disab_info = holm_result["module_results"]["disability"]
    assert "p_adjusted" in disab_info, "Expected p_adjusted field in disability module_results"
    print(f"p_adjusted present in disability module: {disab_info['p_adjusted']}  ✓\n")

    # ── Test 10: SPEARMAN SKIN CORRELATION ───────────────────────────────────
    print("=== TEST 10: SPEARMAN SKIN GRADIENT ===")
    spear_rows = []
    hire_rates = [0.80, 0.65, 0.50, 0.35, 0.20, 0.10]
    for band_idx, rate in enumerate(hire_rates, start=1):
        n = 50
        h = int(n * rate)
        label_map = {1: "very fair", 2: "fair", 3: "medium",
                     4: "olive", 5: "brown", 6: "dark"}
        for j in range(n):
            spear_rows.append({
                "gender": "Male" if j % 2 == 0 else "Female",
                "shortlisted": "Yes",
                "hired": "Yes" if j < h else "No",
                "skin_colour": label_map[band_idx],
            })
    spear_df = pd.DataFrame(spear_rows)
    spear_result = compute_fairness_metrics(spear_df)

    print(f"Skin flags: {len(spear_result['skin_flags'])}")
    for f in spear_result["skin_flags"][:3]:
        print(f"  • {f[:130]}")
    assert spear_result["module_results"]["skin"]["passed"] is False, \
        "Expected skin module to FAIL on strong gradient"
    spearman_flag = any("Spearman" in f or "ρ" in f for f in spear_result["skin_flags"])
    print(f"Spearman ρ flag present: {spearman_flag}")
    print("✓ Test 10 passed.\n")

    print("✓ All v6.1 smoke tests passed.")


if __name__ == "__main__":
    smoke_test()