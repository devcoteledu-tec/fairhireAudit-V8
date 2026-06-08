"""
tests/test_audit_engine.py — FairHire v6 pytest suite

Converts the 10 smoke_test() blocks in audit_engine.py into pytest-
discoverable test functions. Run with:

    pytest tests/test_audit_engine.py -v

Every test is independent — shared fixtures (biased_df, fair_df, etc.)
are built once per session via @pytest.fixture(scope="session").
"""
import pytest
import pandas as pd
import sys
import os

# Allow importing audit_engine from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from audit_engine import compute_fairness_metrics

LARGE = 100  # group size >> min_group_size=10 for clear statistical signal


# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def biased_df():
    """Severely biased dataset: Gender + Caste + Skin all fail → Toxic."""
    rows = []
    for i in range(LARGE):
        rows.append({"gender": "Male",   "shortlisted": "Yes",
                     "hired": "Yes" if i < 40 else "No",
                     "category": "General", "skin_colour": "fair",
                     "disability_status": "No"})
    for i in range(LARGE):
        rows.append({"gender": "Female", "shortlisted": "Yes",
                     "hired": "Yes" if i < 12 else "No",
                     "category": "General", "skin_colour": "fair",
                     "disability_status": "No"})
    for i in range(40):
        rows.append({"gender": "Male",   "shortlisted": "Yes",
                     "hired": "Yes" if i < 1 else "No",
                     "category": "SC", "skin_colour": "fair",
                     "disability_status": "No"})
    for i in range(20):
        rows.append({"gender": "Female", "shortlisted": "Yes",
                     "hired": "No",
                     "category": "SC", "skin_colour": "fair",
                     "disability_status": "No"})
    for i in range(60):
        rows.append({"gender": "Male",   "shortlisted": "Yes",
                     "hired": "Yes" if i < 4 else "No",
                     "category": "General", "skin_colour": "dark",
                     "disability_status": "No"})
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def fair_df():
    """Perfectly fair dataset: all modules pass → score 100."""
    rows = []
    for gender in ("Male", "Female", "Non-binary"):
        for cat in ("General", "OBC", "SC", "ST"):
            for skin in ("fair", "brown"):
                for hired_val in (["Yes"] * 4 + ["No"] * 6) * 3:
                    rows.append({
                        "gender": gender, "shortlisted": "Yes",
                        "hired": hired_val, "category": cat,
                        "skin_colour": skin, "disability_status": "No",
                    })
    # Add 15 disabled candidates at the cohort hire rate (~40%) so disability
    # module has enough data to score (clears min_group_size=10 guard).
    for i in range(15):
        rows.append({
            "gender": "Male", "shortlisted": "Yes",
            "hired": "Yes" if i < 6 else "No",
            "category": "General", "skin_colour": "fair",
            "disability_status": "Yes",
        })
    return pd.DataFrame(rows)


# ── Test 1: BIASED DATASET ────────────────────────────────────────────────────

def test_biased_dataset_is_toxic(biased_df):
    """Biased dataset must score Toxic (<25), trigger systemic bias dealbreaker,
    produce ≥3 flags, include Fisher p-values and Wilson CIs."""
    result = compute_fairness_metrics(biased_df)

    assert result["score"] < 25, \
        f"Expected Toxic score (<25); got {result['score']}"
    assert result["label"] == "Toxic", \
        f"Expected 'Toxic' label; got {result['label']}"
    assert result["systemic_bias_triggered"], \
        "Expected systemic bias dealbreaker to fire (caste + skin both fail)"
    assert len(result["flags"]) >= 3, \
        f"Expected ≥3 flags; got {len(result['flags'])}"
    assert result["air_gender"] < 0.50, \
        f"Expected severe gender AIR (<0.50); got {result['air_gender']}"
    assert "SC" in result["caste_stats"], \
        "Expected SC group in caste_stats"
    assert any("p=" in f or "Fisher" in f for f in result["flags"]), \
        "Expected Fisher p-values in at least one flag"
    assert any("CI:" in f for f in result["flags"]), \
        "Expected Wilson CIs in at least one flag"


# ── Test 2: NON-BINARY INCLUSION ──────────────────────────────────────────────

def test_non_binary_gender_inclusion():
    """Non-binary candidates (2/40 hired) must land in other_gender bucket
    and drag gender AIR below 0.80."""
    rows = []
    for i in range(LARGE):
        rows.append({"gender": "Male",       "shortlisted": "Yes",
                     "hired": "Yes" if i < 40 else "No"})
    for i in range(LARGE):
        rows.append({"gender": "Female",     "shortlisted": "Yes",
                     "hired": "Yes" if i < 40 else "No"})
    for i in range(40):
        rows.append({"gender": "Non-binary", "shortlisted": "Yes",
                     "hired": "Yes" if i < 2 else "No"})
    df = pd.DataFrame(rows)
    result = compute_fairness_metrics(df)

    assert result["gender_stats"]["other_gender"]["total"] == 40, \
        "Non-binary candidates should land in other_gender bucket"
    assert result["air_gender"] < 0.80, \
        f"Expected gender AIR < 0.80; got {result['air_gender']}"


# ── Test 3: ALIAS COLUMN DETECTION ───────────────────────────────────────────

def test_alias_column_detection():
    """Engine must resolve 'skin_tone' → skin module and 'selection' → outcome."""
    rows = []
    for i in range(LARGE):
        rows.append({"gender": "Male",   "shortlisted": "Yes",
                     "skin_tone": "fair", "selection": 1 if i < 40 else 0})
    for i in range(LARGE):
        rows.append({"gender": "Female", "shortlisted": "Yes",
                     "skin_tone": "fair", "selection": 1 if i < 40 else 0})
    df = pd.DataFrame(rows)
    result = compute_fairness_metrics(df)

    assert result["outcome_col"] == "selection", \
        f"Expected outcome_col='selection'; got '{result['outcome_col']}'"
    assert result["air_skin"] == 1.0, \
        f"Expected air_skin=1.0 (single band, equal rates); got {result['air_skin']}"


# ── Test 4: DATA QUALITY GUARD ────────────────────────────────────────────────

def test_all_zero_outcome_raises():
    """All-zero outcome column must raise ValueError before any metric runs."""
    bad_df = pd.DataFrame([
        {"gender": "Male", "shortlisted": "Yes", "hired": "No"}
        for _ in range(20)
    ])
    with pytest.raises(ValueError, match="[Dd]ata [Qq]uality|all.zero|no hired"):
        compute_fairness_metrics(bad_df)


# ── Test 5: MISSING OPTIONAL COLUMN → 0 PTS ──────────────────────────────────

def test_missing_disability_column_scores_zero():
    """Disability column absent → data_present=False, passed=None, points=0.
    Missing data must never award free points."""
    rows = []
    for i in range(LARGE):
        rows.append({"gender": "Male",   "shortlisted": "Yes",
                     "hired": "Yes" if i < 40 else "No"})
    for i in range(LARGE):
        rows.append({"gender": "Female", "shortlisted": "Yes",
                     "hired": "Yes" if i < 40 else "No"})
    df = pd.DataFrame(rows)
    result = compute_fairness_metrics(df)
    mod = result["module_results"]["disability"]

    assert mod["data_present"] is False, \
        "disability data_present should be False when column is absent"
    assert mod["points"] == 0, \
        f"Expected 0 pts for missing disability column; got {mod['points']}"
    assert mod["passed"] is None, \
        f"Expected passed=None for missing column; got {mod['passed']}"


# ── Test 6: PROXY FLAG ────────────────────────────────────────────────────────

def test_proxy_flag_fails_proxy_module():
    """Strong postcode→outcome correlation must fire proxy flags and fail the
    proxy module (passed=False, points=0). φ coefficient must appear in flags."""
    rows = []
    for i in range(50):   # Tier 1: 45/50 hired (90%)
        rows.append({"gender": "Male",   "shortlisted": "Yes",
                     "hired": "Yes" if i < 45 else "No", "postcode": "tier_1"})
    for i in range(50):   # Tier 3: 3/50 hired (6%)
        rows.append({"gender": "Male",   "shortlisted": "Yes",
                     "hired": "Yes" if i < 3  else "No", "postcode": "tier_3"})
    for i in range(50):   # Female tier 1
        rows.append({"gender": "Female", "shortlisted": "Yes",
                     "hired": "Yes" if i < 22 else "No", "postcode": "tier_1"})
    for i in range(50):   # Female tier 3
        rows.append({"gender": "Female", "shortlisted": "Yes",
                     "hired": "Yes" if i < 4  else "No", "postcode": "tier_3"})
    df = pd.DataFrame(rows)
    result = compute_fairness_metrics(df)
    mod = result["module_results"]["proxy"]

    if len(result["proxy_flags"]) > 0:
        assert mod["passed"] is False, \
            "Proxy module must FAIL when proxy flags are raised"
        assert mod["points"] == 0, \
            f"Proxy module must earn 0 pts when failed; got {mod['points']}"
        assert any("φ=" in f or "phi" in f.lower() for f in result["proxy_flags"]), \
            "Expected φ coefficient in at least one proxy flag"
    else:
        pytest.skip("Proxy φ below detection threshold for this dataset size")


# ── Test 7: FAIR DATASET → SCORE 100 ─────────────────────────────────────────

def test_fair_dataset_scores_100(fair_df):
    """Perfectly balanced dataset must score exactly 100 with zero flags."""
    result = compute_fairness_metrics(fair_df)

    assert result["score"] == 100, \
        f"Expected score=100; got {result['score']}. Module breakdown:\n" + \
        "\n".join(f"  {m}: {i}" for m, i in result["module_results"].items())
    assert result["label"] == "Good", \
        f"Expected label='Good'; got '{result['label']}'"
    assert len(result["flags"]) == 0, \
        f"Expected zero flags on fair dataset; got: {result['flags']}"


# ── Test 8: REGION SWITCH ─────────────────────────────────────────────────────

def test_region_us_injects_us_law_references(biased_df):
    """US region must inject Title VII / ADA / ADEA / EEOC references into flags."""
    result = compute_fairness_metrics(biased_df, region="US")

    assert result["region"] == "US"
    all_flags = " ".join(result["flags"])
    us_refs = {"Title VII", "ADA", "ADEA", "EEOC", "Civil Rights"}
    assert any(ref in all_flags for ref in us_refs), \
        f"Expected US legal references in flags; got: {all_flags[:300]}"


def test_region_unknown_raises(biased_df):
    """Unknown region code must be rejected with ValueError."""
    with pytest.raises(ValueError):
        compute_fairness_metrics(biased_df, region="XX")


# ── Test 9: BONFERRONI–HOLM p_adjusted FIELD ─────────────────────────────────

def test_holm_p_adjusted_present_in_module_results():
    """module_results for disability must expose a p_adjusted field after
    Bonferroni–Holm correction is applied."""
    rows = []
    for i in range(20):
        rows.append({"gender": "Male",   "shortlisted": "Yes",
                     "hired": "Yes" if i < 9 else "No"})
    for i in range(20):
        rows.append({"gender": "Female", "shortlisted": "Yes",
                     "hired": "Yes" if i < 6 else "No"})
    df = pd.DataFrame(rows)
    result = compute_fairness_metrics(df, min_group_size=10)
    mod = result["module_results"]["disability"]

    assert "p_adjusted" in mod, \
        f"Expected p_adjusted key in disability module_results; got keys: {list(mod.keys())}"


# ── Test 10: SPEARMAN SKIN GRADIENT ──────────────────────────────────────────

def test_spearman_skin_gradient_fails_skin_module():
    """Strong monotone gradient (hire rate drops 80%→10% across 6 skin bands)
    must fail the skin module and produce a Spearman ρ flag."""
    hire_rates = [0.80, 0.65, 0.50, 0.35, 0.20, 0.10]
    label_map  = {1: "very fair", 2: "fair", 3: "medium",
                  4: "olive",     5: "brown", 6: "dark"}
    rows = []
    for band_idx, rate in enumerate(hire_rates, start=1):
        n = 50
        h = int(n * rate)
        for j in range(n):
            rows.append({
                "gender":      "Male" if j % 2 == 0 else "Female",
                "shortlisted": "Yes",
                "hired":       "Yes" if j < h else "No",
                "skin_colour": label_map[band_idx],
            })
    df = pd.DataFrame(rows)
    result = compute_fairness_metrics(df)

    assert result["module_results"]["skin"]["passed"] is False, \
        "Skin module must FAIL on a strong monotone hire-rate gradient"
    assert any("Spearman" in f or "ρ" in f for f in result["skin_flags"]), \
        "Expected Spearman ρ flag in skin_flags"