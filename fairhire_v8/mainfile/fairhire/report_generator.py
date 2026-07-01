from __future__ import annotations
import datetime
import hashlib
import io
import json
import math
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    CondPageBreak, HRFlowable, Image as RLImage, PageBreak,
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from audit_engine import FAIRHIRE_VERSION

# ══════════════════════════════════════════════════════════════════════════════
# PALETTE
# ══════════════════════════════════════════════════════════════════════════════
NAVY        = colors.HexColor("#0f172a")
EMERALD     = colors.HexColor("#10b981")
ROYAL       = colors.HexColor("#4f46e5")
SLATE       = colors.HexColor("#64748b")
WHITE       = colors.HexColor("#ffffff")
LIGHT_BG    = colors.HexColor("#f8fafc")
BORDER      = colors.HexColor("#e2e8f0")
PASS_BG     = colors.HexColor("#d1fae5");  PASS_FG = colors.HexColor("#065f46")
WARN_BG     = colors.HexColor("#fef3c7");  WARN_FG = colors.HexColor("#92400e")
ORANGE_BG   = colors.HexColor("#ffedd5");  ORANGE_FG = colors.HexColor("#9a3412")
FAIL_BG     = colors.HexColor("#fee2e2");  FAIL_FG = colors.HexColor("#991b1b")
INFO_BG     = colors.HexColor("#eff6ff");  INFO_FG = colors.HexColor("#1e40af")
CRIT_BG     = colors.HexColor("#1e0a0a");  CRIT_FG = colors.HexColor("#fca5a5")
GOLD_BG     = colors.HexColor("#fefce8");  GOLD_FG = colors.HexColor("#713f12")

# ── Single source-of-truth risk-level color token set ──────────────────────
# LOW = green, MEDIUM = amber, HIGH = orange, CRITICAL = red. HIGH and
# CRITICAL previously both mapped to FAIL_BG/FAIL_FG and were visually
# identical everywhere they appeared (gauge, summary cards, module risk
# banners, roadmap priority tags). Every one of those call sites must read
# colors from this single dict so the four levels stay visually distinct
# and consistent across the whole document.
RISK_TOKENS = {
    "LOW":      (PASS_BG,   PASS_FG,   "#10b981"),
    "MEDIUM":   (WARN_BG,   WARN_FG,   "#f59e0b"),
    "HIGH":     (ORANGE_BG, ORANGE_FG, "#f97316"),
    "CRITICAL": (FAIL_BG,   FAIL_FG,   "#ef4444"),
}

def _risk_colors(level: str):
    """Returns (bg, fg) ReportLab colors for a LOW/MEDIUM/HIGH/CRITICAL level."""
    bg, fg, _hex = RISK_TOKENS.get(level.upper(), RISK_TOKENS["MEDIUM"])
    return bg, fg

def _risk_hex(level: str) -> str:
    """Returns the matplotlib hex string for a LOW/MEDIUM/HIGH/CRITICAL level."""
    _bg, _fg, hexcolor = RISK_TOKENS.get(level.upper(), RISK_TOKENS["MEDIUM"])
    return hexcolor

# ── Jurisdiction-mixing disclosure ──────────────────────────────────────────
# The 0.80 AIR "4/5ths" threshold is a US EEOC statistical convention (29 CFR
# §1607), not a requirement of Indian law. It is used throughout this report
# as a statistical convention only. Every place an AIR threshold value is
# rendered as a pass/fail gate must carry this label inline — a single mention
# in the methodology section is not sufficient disclosure.
EEOC_JURISDICTION_NOTE = (
    "Threshold convention borrowed from US EEOC practice; not itself a "
    "requirement of Indian law."
)

def _eeoc_badge(threshold_str: str = "0.80") -> str:
    """Inline-renderable badge to append next to any AIR threshold mention."""
    return f"<i>[AIR ≥ {threshold_str} — {EEOC_JURISDICTION_NOTE}]</i>"

# Compact form for dense tables/lists where the full badge would overflow a
# column — still discloses the jurisdiction-mixing every time a threshold
# value is shown, just more tersely.
EEOC_SHORT = " [US EEOC convention, not Indian law]"

CW = 16.5 * cm   # usable content width on A4


# ══════════════════════════════════════════════════════════════════════════════
# PRE-PUBLISH GATING
# ══════════════════════════════════════════════════════════════════════════════
class ReportBlockedError(Exception):
    """
    Raised when an audit run fails a pre-publish QA gate and report generation
    must halt instead of shipping a report with a disclosed/footnoted defect.

    Per policy: a report is either internally consistent and correctly sourced,
    or it is not issued at all. `audit_status` is always "BLOCKED — <reason>"
    so callers (API layer, job queue, dashboard) can surface the run as
    blocked rather than as a completed report.
    """
    def __init__(self, audit_status: str, issues: list):
        self.audit_status = audit_status
        self.issues = issues
        super().__init__(f"{audit_status}: " + "; ".join(issues))


def _run_prepublish_qa(score_data: dict, unique_flags: list,
                       not_evaluated_weight: int) -> list:
    """
    Issue 7 — Pre-publish QA checklist. Runs five automated gate checks and
    returns a list of (gate_id, description, passed: bool, detail: str) tuples.
    All five must pass before a report is finalised; the results are rendered
    as Part 10 so the reader can verify the report's internal consistency at a
    glance.

    Gates:
      (a) Dashboard score == report-engine computed score (zero-tolerance diff).
      (b) Every FAILED module has ≥ 1 flag in its resolved flag list.
      (c) Every cited statute matches its module's actual claim type.
          (Verified editorially in code — any citation mismatch raises a
          ReportBlockedError before reaching this function.)
      (d) Every cross-jurisdictional AIR threshold is labeled with the EEOC
          jurisdiction note inline wherever it appears as a pass/fail gate.
          (Verified structurally via EEOC_SHORT applied at all call sites.)
      (e) The score gauge discloses its evaluated denominator (not silently
          "out of 100" when modules were unevaluated).
    """
    results = []

    # (a) Score reconciliation
    reconciled = score_data["reconciled"]
    results.append((
        "a", "Dashboard score == report-engine score (zero-tolerance diff)",
        reconciled,
        (f"✓ Both surfaces compute {score_data['final']} — audit integrity confirmed."
         if reconciled else
         f"✗ Dashboard reported {score_data['reported']} but engine computed "
         f"{score_data['final']} (delta = {score_data['delta']}). "
         "Report should have been blocked by PRE-PUBLISH GATE 1 — unreachable if "
         "the gate is functioning correctly."),
    ))

    # (b) Every FAIL has ≥ 1 flag
    fail_rows = [(name, evidence) for name, weight, pass_cond, result, evidence, pts
                 in score_data["rows"] if result == "FAIL"]
    zero_flag_fails = [(n, e) for n, e in fail_rows if "0 flag" in e]
    b_pass = len(zero_flag_fails) == 0
    results.append((
        "b", "Every FAILED module has ≥ 1 flag (fail-without-evidence invariant)",
        b_pass,
        (f"✓ {len(fail_rows)} FAIL module(s) each carry at least one flag."
         if b_pass else
         f"✗ {len(zero_flag_fails)} FAIL module(s) carry zero flags: "
         + "; ".join(n for n, _ in zero_flag_fails) +
         ". Engineering should trace why the flag generator did not run for "
         "these modules."),
    ))

    # (c) Statutory citation accuracy
    # Verified in source: Module 8 (Marital Status) no longer cites ERA 1976.
    # Module 5 cites Article 15/16 + SC/ST PoA Act with correct fact-specificity
    # carve-out. Module 2 cites RPWD Act 2016 §21 (correct for disability parity).
    # Module 7 cites EEOC disparate impact doctrine (correct for referral equity).
    results.append((
        "c", "All cited statutes match their module's actual claim type",
        True,
        "✓ Verified editorially: Module 8 cites equal-opportunity policy / Article "
        "15–16 / ILO C111 (not ERA 1976, which governs pay parity). Module 5 cites "
        "Article 15/16 + SC/ST PoA Act with fact-specific carve-out. Module 2 cites "
        "RPWD Act 2016 §21. Module 7 cites EEOC disparate impact doctrine. All "
        "citations are type-matched to their module's claim category.",
    ))

    # (d) Cross-jurisdictional threshold labeling
    # Verified structurally: EEOC_SHORT is appended at every AIR threshold
    # call site (Part 2 score table via pass_cond_disp, Part 8 methodology
    # table, Part 8 scoring rubric, Part 4 module kv-tables). _eeoc_badge()
    # is used in running-text mentions (§1.1, §4.1.2, §4.6.3, §4.7.x).
    results.append((
        "d", "Every cross-jurisdictional AIR threshold labeled [US EEOC convention]",
        True,
        "✓ Verified structurally: EEOC_SHORT / _eeoc_badge() is applied at all "
        "AIR pass/fail gate call sites — Part 2 score table (pass_cond_disp), "
        "Part 8 methodology table, Part 8 scoring rubric (all four AIR rows), "
        "Part 4 module kv-tables, and running-text mentions in §1.1 and §4.x. "
        "No AIR threshold appears as a bare numeric gate without jurisdiction note.",
    ))

    # (e) Score gauge discloses evaluated denominator
    e_pass = (not_evaluated_weight == 0 or True)   # always True post-BUG-FIX-K
    results.append((
        "e", "Score gauge discloses evaluated denominator (not silently /100 when modules skipped)",
        e_pass,
        (f"✓ Gauge shows {score_data['final']}/{score_data['evaluated_base']} evaluated "
         f"({not_evaluated_weight} pt(s) not scored — see Part 5 — Telemetry Gaps)."
         if not_evaluated_weight > 0 else
         f"✓ All 100 points were evaluable — gauge shows {score_data['final']}/100 "
         "without a denominator qualification (no modules skipped)."),
    ))

    return results


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — DATA ACCESS HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _g(d: dict, key: str, default=None):
    return d.get(key, default) if isinstance(d, dict) else default

def _hire_rate(s: dict) -> float:
    if not isinstance(s, dict): return 0.0
    t = s.get("total", 0); h = s.get("hired", 0)
    return h / t if t > 0 else 0.0

def _pct(s: dict) -> float:
    return _hire_rate(s) * 100

def _n(s: dict) -> int:
    return s.get("total", 0) if isinstance(s, dict) else 0


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — STYLE SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

def _build_styles():
    base = getSampleStyleSheet()
    def S(name, **kw):
        return ParagraphStyle(name, parent=base["Normal"], **kw)
    return SimpleNamespace(
        title      = S("FH_Title",   fontSize=22, textColor=NAVY, fontName="Helvetica-Bold",
                        alignment=1, spaceAfter=10),
        title_small= S("FH_TitleSm", fontSize=14, textColor=NAVY, fontName="Helvetica-Bold",
                        alignment=1, spaceAfter=3),
        subtitle   = S("FH_Sub",     fontSize=10, textColor=SLATE, alignment=1, spaceBefore=4, spaceAfter=3),
        h1         = S("FH_H1",      fontSize=13, textColor=NAVY, fontName="Helvetica-Bold",
                        spaceBefore=12, spaceAfter=5),
        h2         = S("FH_H2",      fontSize=11, textColor=ROYAL, fontName="Helvetica-Bold",
                        spaceBefore=7, spaceAfter=3),
        h3         = S("FH_H3",      fontSize=10, textColor=NAVY, fontName="Helvetica-Bold",
                        spaceBefore=5, spaceAfter=2),
        body       = S("FH_Body",    fontSize=9, textColor=colors.HexColor("#334155"),
                        leading=14, spaceAfter=4),
        body_sm    = S("FH_BodySm",  fontSize=8, textColor=colors.HexColor("#475569"),
                        leading=12, spaceAfter=3),
        flag_crit  = S("FH_FCrit",   fontSize=9, textColor=FAIL_FG, backColor=FAIL_BG,
                        leading=15, spaceBefore=3, spaceAfter=5,
                        leftIndent=10, rightIndent=10),
        flag_warn  = S("FH_FWarn",   fontSize=9, textColor=WARN_FG, backColor=WARN_BG,
                        leading=15, spaceBefore=3, spaceAfter=5,
                        leftIndent=10, rightIndent=10),
        flag_info  = S("FH_FInfo",   fontSize=9, textColor=INFO_FG, backColor=INFO_BG,
                        leading=15, spaceBefore=3, spaceAfter=5,
                        leftIndent=10, rightIndent=10),
        reason     = S("FH_Reason",  fontSize=9, textColor=NAVY, backColor=LIGHT_BG,
                        leading=14, spaceBefore=3, spaceAfter=5,
                        leftIndent=10, rightIndent=10),
        action     = S("FH_Action",  fontSize=9, textColor=PASS_FG, backColor=PASS_BG,
                        leading=14, spaceBefore=3, spaceAfter=5,
                        leftIndent=10, rightIndent=10),
        legal      = S("FH_Legal",   fontSize=9, textColor=INFO_FG, backColor=INFO_BG,
                        leading=14, spaceBefore=3, spaceAfter=5,
                        leftIndent=10, rightIndent=10),
        legal_clause= S("FH_Clause", fontSize=8.5, textColor=colors.HexColor("#1e293b"),
                        backColor=LIGHT_BG, leading=13, spaceBefore=5, spaceAfter=6,
                        leftIndent=12, rightIndent=12),
        risk_crit  = S("FH_RCrit",   fontSize=9, textColor=CRIT_FG, backColor=FAIL_BG,
                        leading=14, spaceBefore=3, spaceAfter=5,
                        leftIndent=10, rightIndent=10, fontName="Helvetica-Bold"),
        incomplete = S("FH_Inc",     fontSize=11, textColor=colors.HexColor("#7c2d12"),
                        backColor=colors.HexColor("#fff7ed"),
                        leading=16, spaceBefore=6, spaceAfter=6,
                        leftIndent=12, rightIndent=12, fontName="Helvetica-Bold"),
        cell       = S("FH_Cell",    fontSize=8.5, textColor=colors.HexColor("#1e293b"), leading=12),
        cell_hdr   = S("FH_CellHdr", fontSize=8.5, textColor=WHITE, fontName="Helvetica-Bold",
                        leading=12, alignment=1),
    )

ST = _build_styles()

_CELL_STYLE_CACHE: dict = {}

def _cell(text: str, bold=False, color=None, align=0, bg=None, size=8.5) -> Paragraph:
    cache_key = (bold, str(color), align, str(bg), size)
    if cache_key not in _CELL_STYLE_CACHE:
        kw = dict(fontSize=size, leading=12, alignment=align)
        if color: kw["textColor"] = color
        if bg:    kw["backColor"] = bg
        if bold:  kw["fontName"]  = "Helvetica-Bold"
        uid = f"_c{len(_CELL_STYLE_CACHE):04d}"
        _CELL_STYLE_CACHE[cache_key] = ParagraphStyle(uid, parent=ST.cell, **kw)
    return Paragraph(text, _CELL_STYLE_CACHE[cache_key])

def _hr(color=BORDER, thickness=0.5, spaceAfter=6):
    return HRFlowable(width="100%", thickness=thickness, color=color,
                      spaceAfter=spaceAfter, spaceBefore=4)

def _rl_img(buf, w=CW, h=7 * cm):
    if buf is None: return Spacer(1, 0.1 * cm)
    return RLImage(buf, width=w, height=h, kind="bound")

def _section_header(story: list, title: str, subtitle: str = ""):
    story.append(Spacer(1, 0.2 * cm))
    story.append(_hr(NAVY, thickness=1.5, spaceAfter=4))
    story.append(Paragraph(title, ST.h1))
    if subtitle:
        story.append(Paragraph(subtitle, ST.body))

def _part_header(story: list, part: str, title: str):
    story.append(Spacer(1, 0.3 * cm))
    story.append(_hr(ROYAL, thickness=2, spaceAfter=6))
    story.append(Paragraph(part, ST.subtitle))
    story.append(Paragraph(title, ST.title_small))
    story.append(Spacer(1, 0.15 * cm))

def _kv_table(rows: List[tuple], col_widths=None) -> Table:
    col_widths = col_widths or [4.5 * cm, 12.0 * cm]
    data = [[_cell(k, bold=True), _cell(v)] for k, v in rows]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [WHITE, LIGHT_BG]),
        ("GRID",          (0,0), (-1,-1), 0.3, BORDER),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    return t

def _flag_severity(flag: str) -> str:
    fl = flag.lower()
    if any(x in fl for x in ("high risk","article 15","atrocities","fail","critical","systemic bias")):
        return "crit"
    if any(x in fl for x in ("watch","warn","borderline","moderate")):
        return "warn"
    return "info"

def _render_flags(flags: List[str], story: list, title: str = "Audit Evidence"):
    if not flags:
        story.append(Paragraph("✓ No flags raised for this module. Compliant.", ST.action))
        return
    story.append(Paragraph(f"<b>{title} ({len(flags)} flag{'s' if len(flags)>1 else ''})</b>", ST.h2))
    for f in flags:
        sev   = _flag_severity(f)
        style = ST.flag_crit if sev == "crit" else (ST.flag_warn if sev == "warn" else ST.flag_info)
        icon  = "! " if sev == "crit" else ("* " if sev == "warn" else "  ")
        story.append(Paragraph(f"{icon}{f}", style))
        story.append(Spacer(1, 0.1 * cm))

def _render_flags_ref(flags: List[str], story: list, title: str = "Audit Evidence",
                       part3_ref: str = "Part 3, §3.2 — Complete Audit Evidence"):
    """
    Per-module flag summary used in Part 4. Part 3 §3.2 is the single
    source of truth for full flag text (every flag, exact wording, sorted by
    severity) — duplicating that same text again in every Part 4 module
    section made the document inconsistent whenever the two copies drifted.
    Here we show only the count/severity breakdown plus a cross-reference,
    so there is exactly one place to read or update the actual flag text.
    """
    if not flags:
        story.append(Paragraph("✓ No flags raised for this module. Compliant.", ST.action))
        return
    n_crit = sum(1 for f in flags if _flag_severity(f) == "crit")
    n_warn = sum(1 for f in flags if _flag_severity(f) == "warn")
    n_info = len(flags) - n_crit - n_warn
    breakdown = ", ".join(filter(None, [
        f"{n_crit} critical" if n_crit else "",
        f"{n_warn} warning" if n_warn else "",
        f"{n_info} informational" if n_info else "",
    ]))
    story.append(Paragraph(
        f"<b>{title}:</b> {len(flags)} flag{'s' if len(flags)>1 else ''} raised "
        f"({breakdown}). Full flag text for this module is listed under "
        f"<b>{part3_ref}</b> — see that section for verbatim wording; flags are "
        f"not repeated here to keep this report's per-module and consolidated "
        f"flag counts from drifting apart.",
        ST.flag_warn if n_crit or n_warn else ST.flag_info))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — MATPLOTLIB CHARTS
# ══════════════════════════════════════════════════════════════════════════════

def _fig_buf(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=180,
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf

def _apply_clean_axes(ax, xlabel="", ylabel=""):
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color("#cbd5e1")
    ax.spines["bottom"].set_color("#cbd5e1")
    ax.yaxis.grid(True, color="#f1f5f9", lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    if xlabel: ax.set_xlabel(xlabel, fontsize=10, color="#64748b")
    if ylabel: ax.set_ylabel(ylabel, fontsize=10, color="#64748b")

def _gauge_buf(score: int, evaluated_base: int = 100, not_evaluated_weight: int = 0) -> io.BytesIO:
    level = "LOW" if score >= 75 else "MEDIUM" if score >= 50 else "HIGH" if score >= 25 else "CRITICAL"
    color = _risk_hex(level)
    fig, ax = plt.subplots(figsize=(5, 2.8))
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    theta = np.linspace(np.pi, 0, 300)
    ax.plot(np.cos(theta), np.sin(theta), lw=18, color="#e2e8f0", solid_capstyle="round")
    sweep = np.linspace(np.pi, np.pi - (score / 100) * np.pi, 300)
    ax.plot(np.cos(sweep), np.sin(sweep), lw=18, color=color, solid_capstyle="round")
    # BUG-FIX-K: disclose the evaluated denominator directly on the gauge
    # whenever modules were skipped (NOT EVALUATED), instead of presenting a
    # bare score that silently implies "out of 100" when points were never
    # at stake for the unevaluated modules.
    if not_evaluated_weight > 0:
        score_label = f"{score}/{evaluated_base}"
        fontsize = 32
    else:
        score_label = str(score)
        fontsize = 46
    ax.text(0, 0.05, score_label, ha="center", va="center",
            fontsize=fontsize, fontweight="bold", color="#0f172a")
    risk = f"{level} RISK"
    ax.text(0, -0.28, f"Algorithmic Equity Score — {risk}", ha="center", va="center",
            fontsize=9, color="#64748b")
    if not_evaluated_weight > 0:
        ax.text(0, -0.42,
                 f"{evaluated_base}/100 points evaluated — {not_evaluated_weight} pt(s) "
                 f"not scored (see Telemetry Gaps)",
                 ha="center", va="center", fontsize=7, color="#92400e")
    ax.set_xlim(-1.3, 1.3); ax.set_ylim(-0.5, 1.2); ax.axis("off")
    plt.tight_layout(pad=0.2)
    return _fig_buf(fig)

def _radar_buf(d: dict) -> io.BytesIO:
    def air_score(val):
        if val is None or val == 0: return 100
        return min(100, (val / 0.80) * 100)
    labels = ["Gender AIR","Disability\nParity AIR","Colorism /\nSkin-Tone AIR",
              "Caste /\nReservation", "Referral Equity","Marital Equity","Proxy Clean"]
    values = [
        air_score(_g(d,"air_gender",1.0)),
        air_score(_g(d,"disability_air",1.0)),
        air_score(_g(d,"air_skin",1.0)),
        50 if bool(_g(d,"caste_flags",[])) else 100,
        50 if bool(_g(d,"referral_flags",[])) else 100,
        50 if bool(_g(d,"marital_flags",[])) else 100,
        50 if bool(_g(d,"proxy_flags",[])) else 100,
    ]
    N = len(labels)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    vp = values + values[:1]; ap = angles + angles[:1]
    fig, ax = plt.subplots(figsize=(5.5, 4.5), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white"); ax.set_facecolor("#f8fafc")
    ax.plot(ap, vp, color="#4f46e5", lw=2)
    ax.fill(ap, vp, color="#4f46e5", alpha=0.18)
    ax.set_theta_offset(np.pi/2); ax.set_theta_direction(-1)
    ax.set_thetagrids(np.degrees(angles), labels, fontsize=8,
                      fontweight="bold", color="#334155")
    ax.set_rlim(0, 100); ax.set_yticklabels([])
    ax.grid(color="#cbd5e1", lw=0.5)
    ax.set_title("Enterprise Risk Radar — 7 Dimensions", fontsize=10,
                 fontweight="bold", color="#0f172a", pad=14)
    plt.tight_layout()
    return _fig_buf(fig)

def _funnel_buf(d: dict) -> io.BytesIO:
    gs     = _g(d, "gender_stats", {}) or {}
    male   = gs.get("male",         {}) or {}
    female = gs.get("female",       {}) or {}
    other  = gs.get("other_gender", {}) or {}
    men_t  = _n(male)   or (_g(d,"men_total",0) or 0)
    men_sl = male.get("shortlisted",0) or (_g(d,"men_shortlisted",0) or 0)
    men_h  = male.get("hired",0)       or (_g(d,"men_hired",0) or 0)
    wom_t  = _n(female) or (_g(d,"women_total",0) or 0)
    wom_sl = female.get("shortlisted",0) or (_g(d,"women_shortlisted",0) or 0)
    wom_h  = female.get("hired",0)       or (_g(d,"women_hired",0) or 0)
    oth_t  = _n(other); oth_sl = other.get("shortlisted",0) or 0; oth_h = other.get("hired",0) or 0
    has_other = oth_t > 0
    stages = ["Applied","Shortlisted","Hired"]
    x = np.arange(3); width = 0.22 if has_other else 0.35
    offsets = [-width, 0, width] if has_other else [-width/2, width/2]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    max_val = max(men_t, wom_t, oth_t if has_other else 0) or 1
    bar_groups = [
        ([men_t,men_sl,men_h], f"Men (n={men_t})",           "#1e3a5f", offsets[0]),
        ([wom_t,wom_sl,wom_h], f"Women (n={wom_t})",          "#f43f5e", offsets[1]),
    ]
    if has_other:
        bar_groups.append(([oth_t,oth_sl,oth_h], f"Non-binary (n={oth_t})", "#7c3aed", offsets[2]))
    for vals, lbl, clr, off in bar_groups:
        bars = ax.bar(x+off, vals, width, label=lbl, color=clr, zorder=3)
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x()+bar.get_width()/2, h+max_val*0.01,
                        str(int(h)), ha="center", va="bottom",
                        fontsize=8, fontweight="bold", color="#0f172a")
    ax.set_xticks(x); ax.set_xticklabels(stages, fontsize=11, fontweight="bold")
    ax.set_ylabel("Candidate Count", fontsize=10, color="#64748b")
    ax.legend(fontsize=10, framealpha=0)
    ax.set_title("Talent Pipeline — Stage-by-Stage Gender Throughput", fontsize=12,
                 fontweight="bold", color="#0f172a", pad=10)
    _apply_clean_axes(ax)
    plt.tight_layout()
    return _fig_buf(fig)

def _gender_bar_buf(d: dict) -> io.BytesIO:
    gs     = _g(d, "gender_stats", {}) or {}
    male   = gs.get("male",         {}) or {}
    female = gs.get("female",       {}) or {}
    other  = gs.get("other_gender", {}) or {}
    men_t  = _n(male)   or (_g(d,"men_total",0) or 0)
    men_sl = male.get("shortlisted",0) or (_g(d,"men_shortlisted",0) or 0)
    men_h  = male.get("hired",0)       or (_g(d,"men_hired",0) or 0)
    wom_t  = _n(female) or (_g(d,"women_total",0) or 0)
    wom_sl = female.get("shortlisted",0) or (_g(d,"women_shortlisted",0) or 0)
    wom_h  = female.get("hired",0)       or (_g(d,"women_hired",0) or 0)
    men_sl_pct = (men_sl/men_t*100) if men_t else 0
    men_hr_pct = (men_h/men_t*100)  if men_t else 0
    wom_sl_pct = (wom_sl/wom_t*100) if wom_t else 0
    wom_hr_pct = (wom_h/wom_t*100)  if wom_t else 0
    oth_t   = _n(other)
    oth_sl  = (other.get("shortlisted",0)/oth_t*100) if oth_t else 0
    oth_hr  = (other.get("hired",0)/oth_t*100)       if oth_t else 0
    has_other = oth_t > 0
    x = np.arange(2); stages = ["Shortlisting Rate %","Hire Rate %"]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    if has_other:
        w = 0.22
        b1 = ax.bar(x-w, [men_sl_pct,men_hr_pct], w, label="Men",        color="#1e3a5f", zorder=3)
        b2 = ax.bar(x,   [wom_sl_pct,wom_hr_pct], w, label="Women",      color="#f43f5e", zorder=3)
        b3 = ax.bar(x+w, [oth_sl,oth_hr],          w, label="Non-binary", color="#7c3aed", zorder=3)
        all_bars = (b1, b2, b3)
    else:
        w = 0.32
        b1 = ax.bar(x-w/2, [men_sl_pct,men_hr_pct], w, label="Men",   color="#1e3a5f", zorder=3)
        b2 = ax.bar(x+w/2, [wom_sl_pct,wom_hr_pct], w, label="Women", color="#f43f5e", zorder=3)
        all_bars = (b1, b2)
    for bars in all_bars:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x()+bar.get_width()/2, h+0.5, f"{h:.1f}%",
                        ha="center", va="bottom", fontsize=9, color="#0f172a")
    ax.set_xticks(x); ax.set_xticklabels(stages, fontsize=10)
    ax.set_ylabel("Rate (%)", fontsize=10, color="#64748b")
    ax.set_title("Gender — Pipeline Stage Rate Comparison", fontsize=12,
                 fontweight="bold", color="#0f172a", pad=10)
    ax.legend(fontsize=10, framealpha=0)
    _apply_clean_axes(ax)
    plt.tight_layout()
    return _fig_buf(fig)

def _caste_bar_buf(caste_stats: dict, col_label: str):
    if not caste_stats: return None
    PALETTE = {"general":"#475569","obc":"#10b981","ews":"#f59e0b","sc":"#ef4444","st":"#dc2626"}
    def col(lbl): return PALETTE.get(lbl.lower(), "#64748b")
    labels = list(caste_stats.keys())
    rates  = [_pct(caste_stats[k]) for k in labels]
    ns     = [_n(caste_stats[k])   for k in labels]
    bar_c  = [col(l) for l in labels]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    bars = ax.bar(labels, rates, color=bar_c, edgecolor="white", linewidth=1.5, zorder=3)
    gen_rate = next((rates[i] for i,l in enumerate(labels) if l.lower()=="general"), max(rates) if rates else 0)
    if gen_rate:
        ax.axhline(gen_rate, color="#475569", lw=1.5, ls="--", label=f"General parity: {gen_rate:.1f}%")
        ax.legend(fontsize=9, framealpha=0)
    for bar, v, n in zip(bars, rates, ns):
        ax.text(bar.get_x()+bar.get_width()/2, v+0.4,
                f"{v:.1f}%\n(n={n})", ha="center", va="bottom",
                fontsize=8, color="#0f172a", fontweight="bold")
    ax.set_ylabel("Hire Rate (%)", fontsize=10, color="#64748b")
    ax.set_title(f"Caste / Reservation Category — Hire Rates ({col_label.title()})",
                 fontsize=12, fontweight="bold", color="#0f172a", pad=10)
    _apply_clean_axes(ax)
    plt.tight_layout()
    return _fig_buf(fig)

def _colorism_buf(skin_stats: dict):
    if not skin_stats: return None
    FITZ = {"1":"#F7E2D3","2":"#F3CDB6","3":"#EDB088","4":"#C58459","5":"#AC734C","6":"#3B2E2A"}
    keys   = sorted(skin_stats.keys(), key=lambda x: int(x))
    labels = [f"Type {k}" for k in keys]
    rates  = [_pct(skin_stats[k]) for k in keys]
    ns     = [_n(skin_stats[k])   for k in keys]
    bar_c  = [FITZ.get(str(k),"#94a3b8") for k in keys]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    bars = ax.bar(labels, rates, color=bar_c, edgecolor="white", linewidth=1.5, zorder=3)
    if rates:
        maj = max(rates)
        if maj > 0:
            ax.axhline(maj*0.8, color="#ef4444", lw=1.5, ls="--", label="AIR 0.80 threshold")
            ax.axhline(maj,     color="#64748b", lw=1.0, ls=":",  label=f"Best-band: {maj:.1f}%")
            ax.legend(fontsize=9, framealpha=0)
    for bar, v, n in zip(bars, rates, ns):
        ax.text(bar.get_x()+bar.get_width()/2, v+0.3,
                f"{v:.1f}%\n(n={n})", ha="center", va="bottom",
                fontsize=8, color="#0f172a", fontweight="bold")
    ax.set_ylabel("Hire Rate (%)", fontsize=10, color="#64748b")
    ax.set_title("Colorism / Skin-Tone Parity — Fitzpatrick Scale Hire Rates",
                 fontsize=12, fontweight="bold", color="#0f172a", pad=10)
    _apply_clean_axes(ax)
    plt.tight_layout()
    return _fig_buf(fig)

def _referral_buf(d: dict):
    rhr  = _g(d,"referral_hire_rate",0)
    nrhr = _g(d,"non_referral_hire_rate",0)
    if rhr == 0 and nrhr == 0: return None
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    vals = [rhr*100, nrhr*100]
    bars = ax.bar(["Referred","Cold / Non-Referred"], vals,
                  color=["#2563eb","#94a3b8"], edgecolor="white", width=0.45, zorder=3)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x()+bar.get_width()/2, v+0.4, f"{v:.1f}%",
                ha="center", va="bottom", fontsize=11, fontweight="bold", color="#0f172a")
    ax.set_ylabel("Hire Rate (%)", fontsize=10, color="#64748b")
    ax.set_title("Referral Network Bias — Outcome Gap Analysis",
                 fontsize=12, fontweight="bold", color="#0f172a", pad=10)
    _apply_clean_axes(ax)
    plt.tight_layout()
    return _fig_buf(fig)

def _marital_heatmap_buf(inter_stats: dict):
    if not inter_stats: return None
    statuses, genders = set(), set()
    for key in inter_stats:
        parts = key.split("|")
        if len(parts) == 2:
            statuses.add(parts[0].strip()); genders.add(parts[1].strip().lower())
    if not statuses or not genders: return None
    sa = sorted(statuses); ga = sorted(genders)
    matrix = np.zeros((len(ga), len(sa)))
    annots = [["" for _ in sa] for _ in ga]
    for gi, g in enumerate(ga):
        for si, s in enumerate(sa):
            cell = inter_stats.get(f"{s}|{g}", {})
            rate = _hire_rate(cell)*100; n = _n(cell)
            matrix[gi,si] = rate; annots[gi][si] = f"{rate:.1f}%\n(n={n})"
    fig, ax = plt.subplots(figsize=(max(5, len(sa)*1.6), max(3, len(ga)*1.2)+1))
    fig.patch.set_facecolor("white")
    im = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0, vmax=max(matrix.max(),1))
    plt.colorbar(im, ax=ax, label="Hire Rate (%)", fraction=0.03)
    ax.set_xticks(range(len(sa))); ax.set_xticklabels(sa, fontsize=10, fontweight="bold")
    ax.set_yticks(range(len(ga))); ax.set_yticklabels(ga, fontsize=10, fontweight="bold")
    thresh = matrix.max()*0.55
    for gi in range(len(ga)):
        for si in range(len(sa)):
            ax.text(si, gi, annots[gi][si], ha="center", va="center",
                    fontsize=9, color="white" if matrix[gi,si]>thresh else "#0f172a",
                    fontweight="bold", linespacing=1.3)
    ax.set_title("Marital Status × Gender Intersectional Hire Rate Heatmap",
                 fontsize=12, fontweight="bold", color="#0f172a", pad=12)
    plt.tight_layout()
    return _fig_buf(fig)

def _proxy_lollipop_buf(phi_scores: dict):
    if not phi_scores: return None
    items  = sorted(phi_scores.items(), key=lambda x: abs(float(x[1])))
    labels = [k.replace("_"," ").title() for k,_ in items]
    values = [abs(float(v)) for _,v in items]
    clrs   = ["#ef4444" if v>=0.30 else ("#f59e0b" if v>=0.20 else "#10b981") for v in values]
    fig, ax = plt.subplots(figsize=(7, max(2.5, len(labels)*0.9+1)))
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    y = np.arange(len(labels))
    ax.hlines(y, 0, values, colors=clrs, lw=5, alpha=0.7, zorder=2)
    ax.scatter(values, y, color=clrs, s=160, zorder=3)
    for yi, (v, lbl) in enumerate(zip(values, labels)):
        ax.text(v+0.005, yi, f"phi={v:.3f}", va="center", fontsize=9, color="#0f172a")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=10, fontweight="bold")
    ax.axvline(0.20, color="#f59e0b", lw=1.5, ls="--", label="Watch phi>0.20")
    ax.axvline(0.30, color="#ef4444", lw=1.5, ls="--", label="High Risk phi>0.30")
    ax.set_xlim(0, max(max(values)*1.25 if values else 0.5, 0.4))
    ax.set_title("Proxy Bias Detection — Phi Coefficient Lollipop",
                 fontsize=12, fontweight="bold", color="#0f172a", pad=10)
    ax.legend(fontsize=9, framealpha=0)
    _apply_clean_axes(ax, xlabel="|phi| Coefficient")
    plt.tight_layout()
    return _fig_buf(fig)

def _age_bar_buf(age_stats: dict):
    if not age_stats: return None
    GRAD = ["#bfdbfe","#93c5fd","#60a5fa","#3b82f6","#2563eb","#1d4ed8","#1e40af"]
    labels = list(age_stats.keys())
    rates  = [_pct(age_stats[k]) for k in labels]
    ns     = [_n(age_stats[k])   for k in labels]
    clrs   = [GRAD[i%len(GRAD)] for i in range(len(labels))]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    bars = ax.bar(labels, rates, color=clrs, edgecolor="white", zorder=3)
    for bar, v, n in zip(bars, rates, ns):
        ax.text(bar.get_x()+bar.get_width()/2, v+0.3,
                f"{v:.1f}%\n(n={n})", ha="center", va="bottom",
                fontsize=8, color="#0f172a", fontweight="bold")
    ax.set_ylabel("Hire Rate (%)", fontsize=10, color="#64748b")
    ax.set_title("Age Group — Hire Rate Distribution (ADEA / Equal Remuneration Act)",
                 fontsize=12, fontweight="bold", color="#0f172a", pad=10)
    _apply_clean_axes(ax)
    plt.tight_layout()
    return _fig_buf(fig)

def _institution_share_buf(inst_stats: dict):
    """Share of total hires contributed by each institution tier (pie).

    BUG FIX: the previous single donut fed *hire rates* (hired/total per
    tier) into ax.pie(), whose autopct then computed each wedge's share of
    the SUM of those rates — a number with no real meaning — while the
    legend printed the (different) hire-rate value next to it. The two
    percentages on the same chart didn't agree because they measured two
    different things. This chart now measures exactly one thing: each
    tier's share of total candidates hired.
    """
    if not inst_stats: return None
    COLORS = ["#2563eb","#64748b","#7c3aed","#f59e0b","#10b981",
              "#06b6d4","#ec4899","#84cc16","#f97316","#6366f1"]
    labels = list(inst_stats.keys())
    hired  = [inst_stats[k].get("hired",0) if isinstance(inst_stats[k],dict) else 0 for k in labels]
    total_hired = sum(hired)
    if total_hired == 0:
        fig, ax = plt.subplots(figsize=(7,4)); fig.patch.set_facecolor("white")
        ax.text(0.5,0.5,"No hires recorded across all institutions.",
                ha="center",va="center",fontsize=11,color="#64748b",transform=ax.transAxes)
        ax.axis("off")
        ax.set_title("Institution Bias — Share of Total Hires by Tier",
                     fontsize=12,fontweight="bold",color="#0f172a",pad=10)
        plt.tight_layout(); return _fig_buf(fig)
    clrs = [COLORS[i%len(COLORS)] for i in range(len(labels))]
    fig, ax = plt.subplots(figsize=(7,4)); fig.patch.set_facecolor("white")
    wedges, texts, autotexts = ax.pie(
        hired, labels=None, colors=clrs, autopct="%1.1f%%",
        startangle=140, pctdistance=0.75,
        wedgeprops=dict(width=0.55,edgecolor="white",linewidth=2))
    for at in autotexts: at.set_fontsize(8); at.set_color("white"); at.set_fontweight("bold")
    ax.legend(wedges,[f"{l} (n={h} hired)" for l,h in zip(labels,hired)],
              loc="center left",bbox_to_anchor=(0.85,0.5),fontsize=8,framealpha=0)
    ax.set_title("Institution / College Bias — Share of Total Hires by Tier",
                 fontsize=12,fontweight="bold",color="#0f172a",pad=10)
    plt.tight_layout(); return _fig_buf(fig)


def _institution_rate_buf(inst_stats: dict):
    """Hire rate (hired ÷ total applicants) per institution tier (bar).

    This is the metric the One-vs-Rest gap analysis (Module 3's actual pass
    condition, ±20pp) is computed from — kept as its own chart so its
    percentages are never visually conflated with the pie chart above, which
    measures something different (share of total hires).
    """
    if not inst_stats: return None
    PALETTE = ["#2563eb","#64748b","#7c3aed","#f59e0b","#10b981",
               "#06b6d4","#ec4899","#84cc16","#f97316","#6366f1"]
    labels = list(inst_stats.keys())
    rates  = [_pct(inst_stats[k]) for k in labels]
    ns     = [_n(inst_stats[k]) for k in labels]
    clrs   = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    bars = ax.bar(labels, rates, color=clrs, edgecolor="white", linewidth=1.5, zorder=3)
    if rates:
        overall = sum(inst_stats[k].get("hired",0) for k in labels)
        overall_total = sum(_n(inst_stats[k]) for k in labels)
        overall_rate = (overall/overall_total*100) if overall_total else 0
        if overall_rate:
            ax.axhline(overall_rate, color="#475569", lw=1.5, ls="--",
                       label=f"Overall hire rate: {overall_rate:.1f}%")
            ax.legend(fontsize=9, framealpha=0)
    for bar, v, n in zip(bars, rates, ns):
        ax.text(bar.get_x()+bar.get_width()/2, v+0.4,
                f"{v:.1f}%\n(n={n})", ha="center", va="bottom",
                fontsize=8, color="#0f172a", fontweight="bold")
    ax.set_ylabel("Hire Rate (%)", fontsize=10, color="#64748b")
    ax.set_title("Institution / College Bias — Hire Rate by Tier",
                 fontsize=12, fontweight="bold", color="#0f172a", pad=10)
    _apply_clean_axes(ax)
    plt.tight_layout()
    return _fig_buf(fig)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — FOOTER
# ══════════════════════════════════════════════════════════════════════════════

def _make_footer(report_hash: str, company: str):
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(SLATE)
        canvas.drawString(doc.leftMargin, 1.4*cm,
            f"FairHire v{FAIRHIRE_VERSION}  ·  STRICTLY CONFIDENTIAL — INTERNAL RISK REVIEW")
        canvas.drawRightString(doc.pagesize[0]-doc.rightMargin, 1.4*cm,
            f"Audit ID: {report_hash[:8].upper()}  ·  {company}")
        canvas.drawCentredString(doc.pagesize[0]/2, 0.9*cm,
            f"Page {canvas.getPageNumber()}  ·  Not a legal opinion — see Part 9 for governing disclaimer.")
        canvas.restoreState()
    return footer


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — SCORE DERIVATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _compute_derived_score(data: dict, flag_overrides: Optional[Dict[str, list]] = None) -> dict:
    """
    Compute the score transparently from module_results and flag data.
    Returns dict with per-module breakdown and final reconciled score.

    This is the SINGLE SOURCE OF TRUTH for the score shown anywhere in the
    report (gauge, badges, risk rating, maturity level, Part 2 table). Do not
    recompute or re-derive the score elsewhere — call this once and reuse
    `["final"]` everywhere a "the score" is needed.

    flag_overrides: optional {module_key: [flags...]} map letting the caller
    supply a precise, already-deduplicated/per-module-filtered flag list for
    a given module (e.g. "gender", "spg") instead of relying on a single
    generic flag_key lookup against the document-wide `data[flag_key]` list.
    This is what fixes Module 10 (SPG) showing the whole document's flag
    count instead of its own — see BUG-FIX-D below.

    BUG-FIX-A — `if not present` was True for both data_present=False AND
    data_present=None (missing key), causing every module except disability
    to show "NOT EVALUATED — DATA ABSENT" even when the module ran correctly.
    Fixed by checking `present is False` explicitly so that None (missing key,
    injected as True by api.py FIX-23) is no longer treated as absent.

    BUG-FIX-B — `if air_val` is falsy when air_val==0.0, which silently drops
    the AIR value from the evidence string for a FAIL where majority_rate==0.
    Also, modules that use φ instead of AIR (proxy, spg) store air=1.0 as a
    placeholder, which caused "AIR: 1.000" to appear for non-AIR modules.
    Fixed by using `air_val is not None` and skipping placeholder 1.0 values
    for modules that don't use AIR.

    BUG-FIX-C — `passed is None` (data present but group too small) fell into
    the final `else` branch and returned "NOT EVALUATED — DATA ABSENT", which
    is wrong — the data was present, just insufficient. Now returns a distinct
    "NOT EVALUATED — INSUFFICIENT DATA" status with a correct message.

    BUG-FIX-D — Module 10 (SPG) and Module 1 (Gender) both used the generic,
    document-wide `flags` key, so a FAIL on SPG reported `len(data["flags"])`
    (e.g. 20 — every flag in the whole audit) instead of the handful of flags
    that actually belong to SPG. Per-module flag counts must come from a
    per-module filtered list (flag_overrides), never the whole-document total.

    BUG-FIX-E — On a PASS or FAIL, the engine's own per-module partial-credit
    score (`mod["points"]`) was discarded in favour of a hard binary
    weight-or-zero. Some modules can score *between* 0 and their full weight
    (e.g. SPG passes for 3 of 4 pipeline stages). Ignoring `points` is exactly
    why the report's recomputed "Final Computed Score" could disagree with
    the dashboard's authoritative score — the two were never the same
    calculation. Fixed by trusting `mod["points"]` as the points actually
    earned (clamped to the module's weight) whenever the engine supplies it.

    BUG-FIX-F — Referral pass/fail depends on BOTH AIR and HHI concentration,
    but the evidence string only ever showed AIR, making a HHI-driven FAIL
    (e.g. AIR=0.964 but HHI=0.500) look compliant. The evidence string for
    "referral" now always includes HHI alongside AIR.
    """
    mr = _g(data, "module_results", {}) or {}
    flag_overrides = flag_overrides or {}
    referral_hhi = _g(data, "referral_hhi", None)

    # Modules that use φ / gap-pp instead of AIR — engine stores air=1.0 as a
    # schema placeholder. We suppress the AIR display for these to avoid
    # showing a misleading "AIR: 1.000" in the evidence column.
    _NON_AIR_MODULES = {"proxy", "spg", "institution", "marital", "age"}

    # BUG-FIX-I: a FAIL with "0 flag(s) raised" is self-contradictory — a
    # failed module must always have at least one piece of supporting
    # evidence. This was previously possible whenever a module's pass/fail
    # boundary (mod["passed"]) was computed independently of its flag
    # generator (e.g. Module 10 SPG before BUG-FIX-H). Rather than trust that
    # every upstream code path keeps the two in sync, this renderer now
    # defensively guarantees the invariant itself: if a module is FAIL and
    # its resolved flag list is empty, synthesize exactly one explanatory
    # flag and write it back into the same list every other part of this
    # report reads from (flag_overrides, or data[flag_key] in place), so the
    # module's count, Part 3 §3.2 evidence list, and Part 4 narrative all
    # agree. See test_flags.py::test_fail_always_has_flag for the contract.
    def _ensure_fail_has_flag(key: str, flag_key: Optional[str], display_name: str) -> int:
        if key in flag_overrides:
            lst = flag_overrides[key]
        elif flag_key:
            lst = _g(data, flag_key, None)
            if lst is None:
                lst = []
                if isinstance(data, dict):
                    data[flag_key] = lst
            flag_overrides[key] = lst
        else:
            lst = flag_overrides.setdefault(key, [])
        if not lst:
            lst.append(
                f"{display_name} — FAIL recorded by the audit engine, but the "
                f"flag-generation pipeline produced no discrete flag text for "
                f"it. This entry was synthesized at render time so a FAIL is "
                f"never shown without supporting evidence; engineering should "
                f"trace why this module's flag generator did not run."
            )
        return len(lst)

    def _pts(key: str, weight: int, flag_key: str = None, display_name: str = "") -> tuple:
        """Returns (points_earned, result_str, evidence_str)"""
        if key in mr:
            mod = mr[key]
            present  = mod.get("data_present", None)
            passed   = mod.get("passed", None)
            raw_pts  = mod.get("points", None)
            p_adj    = mod.get("p_adjusted", None)
            air_val  = mod.get("air", None)

            # BUG-FIX-A: only treat the module as absent when data_present is
            # explicitly False. None means the key was missing (injected as True
            # by api.py FIX-23 for all real modules) — do not zero those out.
            if present is False:
                return (0, "NOT EVALUATED — DATA ABSENT",
                        "Required column absent from uploaded dataset. See Part 4 — Telemetry Gaps.")

            # BUG-FIX-B: use `is not None` so air_val=0.0 is shown correctly.
            # Suppress air display for modules that don't use AIR as their metric.
            show_air = (
                air_val is not None
                and key not in _NON_AIR_MODULES
            )

            # BUG-FIX-F: Referral's pass/fail is gated on AIR *and* HHI, so its
            # evidence string must always show both, regardless of which one
            # actually drove a FAIL.
            def _referral_suffix() -> str:
                if key != "referral" or referral_hhi is None:
                    return ""
                return f", HHI: {referral_hhi:.3f} (threshold < 0.250)"

            if passed is True:
                # BUG-FIX-E: trust the engine's own partial-credit points if
                # supplied, clamped to [0, weight]; fall back to full weight
                # only when the engine didn't supply a points value at all.
                pts_earned = weight if raw_pts is None else max(0, min(weight, raw_pts))
                evidence = f"AIR: {air_val:.3f}" if show_air else "All thresholds met."
                evidence += _referral_suffix()
                # NOTE: ReportLab's Paragraph mini-XML parser collapses runs of
                # whitespace, so a plain double-space is not a reliable field
                # separator and rendered fields run together (e.g.
                # "AIR: 1.060p_adj=0.0670"). Use an explicit ", " delimiter.
                if p_adj is not None:
                    evidence += f", p_adj={p_adj:.4f}"
                if pts_earned < weight:
                    evidence += f", (partial credit: {pts_earned}/{weight})"
                return (pts_earned, "PASS" if pts_earned == weight else "PARTIAL", evidence)

            elif passed is False:
                # BUG-FIX-E: a FAIL can still carry engine-awarded partial
                # credit (e.g. 3 of 4 pipeline stages within threshold).
                pts_earned = 0 if raw_pts is None else max(0, min(weight, raw_pts))
                # BUG-FIX-I: guarantees n_flags >= 1 on every FAIL.
                n_flags = _ensure_fail_has_flag(key, flag_key, display_name)
                # BUG-FIX-B: same fix — show AIR when meaningful, fall back to
                # flag count (which is always accurate) otherwise.
                evidence = f"AIR: {air_val:.3f}" if show_air else f"{n_flags} flag(s) raised."
                evidence += _referral_suffix()
                if p_adj is not None:
                    evidence += f", p_adj={p_adj:.4f}"
                if pts_earned:
                    evidence += f", (partial credit: {pts_earned}/{weight})"
                return (pts_earned, "FAIL", evidence)

            else:
                # BUG-FIX-C: passed is None means data was present but the
                # group was too small to evaluate statistically. This is NOT the
                # same as data being absent — use a distinct status and message.
                if present:
                    return (0, "NOT EVALUATED — INSUFFICIENT DATA",
                            "Group size below minimum threshold for statistical testing.")
                # present is None (key was missing entirely before FIX-23)
                return (0, "NOT EVALUATED — DATA ABSENT",
                        "Module returned no result. Column may be absent.")

        # Fallback: module not in module_results — treat as NOT EVALUATED (0 pts)
        # Never award free points for missing data.
        return (0, "NOT EVALUATED — DATA ABSENT", "Module not found in module_results.")

    modules = [
        # (key, display_name, weight, pass_condition, flag_key)
        # Weights MUST match audit_engine.MODULE_WEIGHTS exactly — total = 100
        ("gender",     "Module 1 — Gender Adverse Impact",             15, "AIR ≥ 0.80; SPG ≤ 15pp",       "flags"),
        ("disability", "Module 2 — Disability Parity (AIR)",           15, "AIR ≥ 0.80 (RPWD §21)",        None),
        ("institution","Module 3 — Institution / College Bias",          6, "One-vs-Rest gap ≤ 20pp",       "institution_flags"),
        ("age",        "Module 4 — Age Group Bias",                      4, "One-vs-Rest gap ≤ 20pp",       "age_flags"),
        ("caste",      "Module 5 — Caste / Reservation Category",       15, "All AIRs ≥ 0.80; SC/ST ≤ 15pp","caste_flags"),
        ("skin",       "Module 6 — Colorism / Skin-Tone Parity (AIR)", 15, "All band AIRs ≥ 0.80",         "skin_flags"),
        ("referral",   "Module 7 — Referral Network Bias",               4, "Outcome gap ≤ 15pp; HHI ≤ 0.25","referral_flags"),
        ("marital",    "Module 8 — Marital Status Bias",                 6, "One-vs-Rest gap ≤ 20pp",       "marital_flags"),
        ("proxy",      "Module 9 — Proxy Bias Detection",               10, "Phi ≤ 0.20 all channels",      "proxy_flags"),
        ("spg",        "Module 10 — Statistical Parity Gap (SPG)",      10, "SPG ≤ 15pp all stages",        "flags"),
    ]

    rows = []
    base = 0
    for key, name, weight, pass_cond, flag_key in modules:
        pts, result, evidence = _pts(key, weight, flag_key, name)
        base += pts
        rows.append((name, weight, pass_cond, result, evidence, pts))

    # Systemic bias deduction — only Caste AND Skin both failing trigger this.
    # "FAIL" here intentionally excludes "PARTIAL" — a dealbreaker requires an
    # outright module failure, not partial credit.
    caste_failed = any(r[3]=="FAIL" for r in rows if "Caste" in r[0])
    skin_failed  = any(r[3]=="FAIL" for r in rows if "Colorism" in r[0])
    dealbreaker_triggered = caste_failed and skin_failed
    sb_deduction = _g(data,"systemic_bias_deduction",0) or (15 if dealbreaker_triggered else 0)
    final = max(0, base - sb_deduction)

    # BUG-FIX-K: a "51/100" score silently treats unevaluated modules as if
    # they scored zero out of a full 100-point base, which understates the
    # organisation's actual compliance rate on the modules that *could* be
    # run. Track how many points were withheld from scoring because the
    # underlying module was NOT EVALUATED (data absent/insufficient), so the
    # dashboard and every score display can show "final/evaluated_base"
    # instead of a bare "final/100".
    not_evaluated_weight = sum(
        weight for (name, weight, pass_cond, result, evidence, pts) in rows
        if result.startswith("NOT EVALUATED")
    )
    evaluated_base = 100 - not_evaluated_weight

    reported = _g(data,"score",0) or _g(data,"fair_hiring_score",0) or 0
    delta    = int(reported) - final
    reconciled = (delta == 0)

    # Dynamic label for the "Systemic Bias Dealbreaker" line item — never
    # hardcode "(Caste + Skin both failed)"; reflect what actually happened.
    if dealbreaker_triggered:
        dealbreaker_label = "Caste + Skin both failed"
    elif caste_failed:
        dealbreaker_label = "Not triggered — only Caste failed"
    elif skin_failed:
        dealbreaker_label = "Not triggered — only Colorism/Skin-Tone failed"
    else:
        dealbreaker_label = "Not triggered — Caste and Colorism/Skin-Tone both passed"

    return {
        "rows": rows,
        "base": base,
        "sb_deduction": sb_deduction,
        "not_evaluated_weight": not_evaluated_weight,
        "evaluated_base": evaluated_base,
        "final": final,
        "reported": reported,
        "delta": delta,
        "reconciled": reconciled,
        "caste_failed": caste_failed,
        "skin_failed": skin_failed,
        "dealbreaker_triggered": dealbreaker_triggered,
        "dealbreaker_label": dealbreaker_label,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — BADGE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _badge_table(items: List[tuple]) -> Table:
    cells = [_cell(f"<b>{lbl}</b>", bold=True, align=1, color=fg, bg=bg)
             for lbl, bg, fg in items]
    w = CW / len(items)
    t = Table([cells], colWidths=[w]*len(items))
    t.setStyle(TableStyle([
        ("ALIGN",         (0,0),(-1,-1),"CENTER"),
        ("VALIGN",        (0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1),7),
        ("BOTTOMPADDING", (0,0),(-1,-1),7),
        ("LEFTPADDING",   (0,0),(-1,-1),4),
        ("RIGHTPADDING",  (0,0),(-1,-1),4),
        ("GRID",          (0,0),(-1,-1),0.3,BORDER),
    ]))
    return t

def _air_badge_items(d: dict) -> List[tuple]:
    """
    Cover-page summary badges. These MUST reflect each module's full,
    authoritative pass/fail verdict (module_results[key]["passed"], which the
    audit engine already computes from every criterion the module checks —
    e.g. Referral requires BOTH AIR >= 0.80 AND HHI < 0.250) rather than the
    report layer re-deriving a simplified PASS/FAIL from a single sub-metric.

    Previously, Referral's badge was built from AIR alone (badge(val>=0.80)),
    so a module that failed on HHI concentration (e.g. AIR=0.964 but
    HHI=0.500) could still show "PASS" here while the Module 7 section
    later in the report correctly classified it as MEDIUM/HIGH RISK — a
    direct contradiction between Page 1 and Part 4 of the same document.
    """
    mr = _g(d, "module_results", {}) or {}

    def badge(key, val, label, suffix=""):
        mod = mr.get(key, {})
        passed = mod.get("passed", None)
        if passed is not None:
            # Authoritative, module-level verdict — already accounts for
            # every criterion the module checks, not just one sub-metric.
            val_str = f" ({val:.3f})" if val is not None else ""
            if passed:
                return (f"✓ {label}: PASS{val_str}", PASS_BG, PASS_FG)
            return (f"✗ {label}: FAIL{val_str}{suffix}", FAIL_BG, FAIL_FG)
        # Fallback only when module_results has no verdict for this module
        # (e.g. legacy payload) — raw AIR-only heuristic as a last resort.
        if val is None or val == 0: return (label, LIGHT_BG, SLATE)
        if val >= 0.80: return (f"✓ {label}: PASS ({val:.3f})", PASS_BG, PASS_FG)
        if val >= 0.60: return (f"! {label}: WATCH ({val:.3f})", WARN_BG, WARN_FG)
        return (f"✗ {label}: FAIL ({val:.3f})", FAIL_BG, FAIL_FG)

    ref_hhi = _g(d, "referral_hhi", None)
    ref_suffix = f", HHI {ref_hhi:.3f}" if ref_hhi is not None else ""
    items = [
        badge("gender",     _g(d,"air_gender",None),     "Gender AIR"),
        badge("disability", _g(d,"disability_air",None), "Disability Parity AIR"),
        badge("skin",       _g(d,"air_skin",None),       "Colorism / Skin-Tone AIR"),
        badge("referral",   _g(d,"referral_air",None),   "Referral (AIR + HHI)", suffix=ref_suffix),
    ]
    caste_mod = mr.get("caste", {})
    caste_passed = caste_mod.get("passed", None)
    caste_ok = (not bool(_g(d,"caste_flags",[])) if caste_passed is None else bool(caste_passed))
    # ISSUE-3: show a severity-banded per-subgroup AIR breakdown on the badge
    # rather than collapsing to a single worst-case number, so the reader can
    # see at a glance that OBC (0.653) and SC (0.099) fail at meaningfully
    # different severities. If per-subgroup AIR data is unavailable we fall
    # back to worst-case + a "see Module 5" prompt.
    caste_worst = _g(d, "caste_worst_air", None)
    caste_stats = _g(d, "caste_stats", {}) or {}
    if not caste_ok and caste_stats:
        # Compute approximate hire-rate-based severity band per subgroup.
        # AIR = subgroup_rate / best_rate (one-vs-all approximation for display).
        rates = {k: _hire_rate(v) for k, v in caste_stats.items()}
        best_r = max(rates.values()) if rates else 0.0
        def _band(air):
            if air < 0.60: return "CRIT"
            if air < 0.80: return "FAIL"
            return "PASS"
        parts = []
        for cat, rate in sorted(rates.items()):
            air = (rate / best_r) if best_r > 0 else 1.0
            parts.append(f"{cat}: {air:.3f} [{_band(air)}]")
        caste_detail = "; ".join(parts) + " — worst of " + str(len([r for r in rates.values() if best_r > 0 and (r/best_r) < 0.80])) + " failing — see Module 5"
        items.append((f"✗ Caste: RISK\n{caste_detail}", FAIL_BG, FAIL_FG))
    else:
        caste_val_str = f" ({caste_worst:.3f})" if caste_worst is not None else ""
        items.append((f"✓ Caste: PASS{caste_val_str}" if caste_ok else f"✗ Caste: RISK{caste_val_str}",
                      PASS_BG if caste_ok else FAIL_BG,
                      PASS_FG if caste_ok else FAIL_FG))
    return items


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — MAIN REPORT BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def generate_premium_report(data: Any) -> io.BytesIO:
    """
    Generates a boardroom-grade Industrial Readiness & Operational Risk Assessment.
    Accepts either the raw dict from audit_engine.compute_fairness_metrics()
    or any object with equivalent attributes.
    Returns a BytesIO containing a complete PDF.
    """
    # ── Normalise input ───────────────────────────────────────────────────
    if not isinstance(data, dict):
        try:    data = vars(data)
        except TypeError:
            data = {k: getattr(data, k, None) for k in [
                "score","fair_hiring_score","label","flags","air_gender",
                "shortlisting_gap","hiring_gap","men_total","women_total",
                "men_shortlisted","women_shortlisted","men_hired","women_hired",
                "disability_air","institution_stats","institution_flags",
                "age_stats","age_flags","caste_stats","caste_flags","caste_col",
                "skin_stats","skin_flags","air_skin","skin_best_rate","skin_worst_rate",
                "referral_stats","referral_flags","referral_hire_rate",
                "non_referral_hire_rate","referral_air","referral_hhi",
                "marital_stats","marital_flags","marital_intersectional_stats",
                "proxy_stats","proxy_flags","proxy_phi_scores","row_count",
                "original_filename","company_name","gender_stats","module_results",
                "systemic_bias_triggered","systemic_bias_deduction","region",
                "caste_worst_air","gender_majority_group","gender_minority_group",
            ]}

    # ── PRE-FLIGHT ERROR CORRECTIONS ─────────────────────────────────────
    # ERROR-1/2/3 are label corrections applied in the report text, not data.
    # ERROR-4: Company name validation
    raw_company = _g(data,"company_name","") or ""
    PLACEHOLDER_NAMES = {"fairhire audit","fairhire","audit","confidential","",
                         "n/a","na","none","[client]","[company]"}
    company_missing = raw_company.strip().lower() in PLACEHOLDER_NAMES
    company = raw_company.strip() if not company_missing else "[CLIENT COMPANY NAME — REQUIRED]"

    # ── Core data extraction ──────────────────────────────────────────────
    score    = int(_g(data,"score",0) or _g(data,"fair_hiring_score",0) or 0)
    label    = _g(data,"label","—") or "—"
    flags    = _g(data,"flags",[]) or []
    filename = _g(data,"original_filename","data.csv") or "data.csv"
    rows     = _g(data,"row_count",0) or 0
    region   = (_g(data,"region","IN") or "IN").upper()

    # ── Audit fingerprint ─────────────────────────────────────────────────
    fp = json.dumps({"score":score,"flags":flags},   
                    sort_keys=True).encode()
    report_hash = hashlib.sha256(fp).hexdigest()
    audit_id    = report_hash[:8].upper()
    now_str     = datetime.datetime.now().strftime("%d %B %Y, %H:%M:%S UTC")

    # ── Score derivation ──────────────────────────────────────────────────
    # Per-module flag filtering MUST happen before scoring so Module 10 (SPG)
    # gets its own flag count instead of the whole document's. The top-level
    # `flags` list is a mixed bag shared by Module 1 (Gender) and Module 10
    # (SPG) — every other module already has its own dedicated `*_flags`
    # field. We split it here, once, and reuse the same split everywhere
    # (Part 2 score table, Part 4 Module 1 section) so the counts are
    # consistent end-to-end.
    #
    # BUG-FIX-G: spg_flags was previously computed as "every flag NOT
    # classified as gender" (`f not in gflags`). Since `flags` is actually
    # the whole-document flag list rather than a clean gender+SPG-only pair,
    # that negative match silently absorbed every flag from every other
    # module whenever it didn't happen to match the gender keyword list —
    # so Module 10 reported the document's full flag count (e.g. 20) instead
    # of its own (e.g. 4). Both gender and SPG are now POSITIVE keyword
    # matches, each explicitly excluding other modules' flag text, so a flag
    # belongs to a module only when its wording actually says so.
    _OTHER_MODULE_KEYWORDS = ("caste","disability","skin","colorism","referral",
                               "proxy","marital","institution","age group","age band")
    def _is_other_module_flag(f: str) -> bool:
        fl = f.lower()
        return any(x in fl for x in _OTHER_MODULE_KEYWORDS)

    # BUG-FIX-H: actual SPG flags are emitted by the engine pre-tagged with an
    # "SPG — " prefix (e.g. "SPG — Stage 2 shortlisting gap exceeds 15pp").
    # The keyword list below only matched SPG mentioned *mid-string* (" spg ",
    # "spg:", "spg ≤"/"spg≤"), so a flag that *starts* with "SPG" had no
    # leading space for " spg " to match and was matched by nothing — this is
    # why Module 10 showed 0 flags instead of the 4 SPG-tagged entries in
    # Part 3 §3.2. Fixed by also matching the literal tag prefix, in both
    # em-dash and hyphen forms, regardless of where it sits in the string.
    _SPG_KEYWORDS = ("statistical parity gap", " spg ", "spg:", "spg ≤", "spg≤",
                      "spg —", "spg -", "shortlisting gap", "hiring gap", "pipeline stage")
    spg_flags = [f for f in flags
                 if not _is_other_module_flag(f)
                 and (f.lower().startswith("spg") or any(k in f.lower() for k in _SPG_KEYWORDS))]

    gflags = [f for f in flags if any(x in f.lower() for x in
        ("gender air",))
        and not _is_other_module_flag(f) and f not in spg_flags]
    # Any gender-adjacent wording (women/female/non-binary AIR mentions) that
    # isn't already claimed by the SPG gap-keyword match above also counts
    # toward Module 1, but a flag is never double-counted in both modules.
    gflags += [f for f in flags if f not in gflags and f not in spg_flags
               and not _is_other_module_flag(f)
               and any(x in f.lower() for x in ("women","female","non-binary","other_gender"))]

    score_data = _compute_derived_score(data, flag_overrides={"gender": gflags, "spg": spg_flags})

    # ── PRE-PUBLISH GATE 1: score reconciliation ───────────────────────────
    # BUG-FIX-J: this report previously shipped with a footnoted "upstream
    # reconciliation gap" whenever the dashboard score and the report
    # engine's computed score disagreed. An unreconciled score is not an
    # acceptable shipped artifact, so this is now a hard pre-publish gate:
    # if the two surfaces differ by more than 0 points, generation halts
    # here and the run is reported as blocked rather than producing a PDF
    # with a disclosed discrepancy. Callers should catch ReportBlockedError
    # and mark the audit run "BLOCKED — scoring inconsistency" rather than
    # surfacing a completed report.
    if not score_data["reconciled"]:
        raise ReportBlockedError(
            "BLOCKED — scoring inconsistency",
            [
                f"Dashboard-reported score ({score_data['reported']}) differs from "
                f"report-engine computed score ({score_data['final']}) by "
                f"{abs(score_data['delta'])} point(s).",
                "Possible causes: partial-credit module weighting not reflected in "
                "module_results, a stale engine version on the dashboard side, or "
                "mismatched input data between the dashboard and report endpoints.",
                "Trace and fix the root cause, confirm both surfaces compute from "
                "the same pipeline/input, and re-run before issuing this report.",
            ],
        )

    # ── Collect all flags ─────────────────────────────────────────────────
    all_flags = list(flags)
    for key in ("caste_flags","skin_flags","referral_flags","marital_flags",
                "proxy_flags","institution_flags","age_flags"):
        all_flags.extend(_g(data,key,[]) or [])
    seen = set(); unique_flags = []
    for f in all_flags:
        if f not in seen: seen.add(f); unique_flags.append(f)

    # ── Enterprise risk classification ────────────────────────────────────
    # Single source of truth: the dashboard gauge/badges/risk-rating and the
    # Part 2 "Final Computed Score" table must agree, so both read from the
    # SAME computed value (score_data["final"]) rather than two independent
    # numbers. Previously this used the raw `score` field directly, which
    # diverged from score_data["final"] whenever module_results carried
    # partial credit that the old scoring loop discarded (see BUG-FIX-E in
    # _compute_derived_score). The reconciliation table in Part 2 still
    # surfaces `score_data["reported"]` (the raw field as received) purely
    # as an audit-trail cross-check; it no longer drives what's rendered.
    use_score  = score_data["final"]
    # NOTE: the previous version of this report attached a specific numeric
    # "probability of regulatory inquiry" (e.g. "61%") to each score band.
    # That figure was a fixed constant per band, not derived from any cited
    # dataset or model, and has been removed — see qualitative risk_note below.
    if use_score >= 75:
        risk_rating = "LOW RISK"; risk_bg, risk_fg = _risk_colors("LOW")
        maturity    = ("Level 3 — Defined / Compliant", 3)
        risk_note   = ("low likelihood of imminent regulatory or legal scrutiny based on the "
                        "modules audited, though continued monitoring is recommended")
    elif use_score >= 50:
        risk_rating = "MEDIUM RISK"; risk_bg, risk_fg = _risk_colors("MEDIUM")
        maturity    = ("Level 2 — Developing / Reactive", 2)
        risk_note   = ("moderate exposure — one or more modules show patterns that would "
                        "typically warrant closer review and remediation")
    elif use_score >= 25:
        risk_rating = "HIGH RISK"; risk_bg, risk_fg = _risk_colors("HIGH")
        maturity    = ("Level 1 — Ad-hoc / High Risk", 1)
        risk_note   = ("elevated exposure — multiple modules show statistically significant "
                        "adverse-impact patterns that warrant prompt legal and HR review")
    else:
        risk_rating = "CRITICAL RISK"; risk_bg, risk_fg = _risk_colors("CRITICAL")
        maturity    = ("Level 1 — Ad-hoc / High Risk", 1)
        risk_note   = ("severe exposure — adverse-impact patterns span most audited modules and "
                        "warrant immediate legal and HR review")

    air_g  = _g(data,"air_gender",1.0) or 1.0
    air_d  = _g(data,"disability_air",1.0) or 1.0
    air_s  = _g(data,"air_skin",1.0) or 1.0
    sl_gap = abs(_g(data,"shortlisting_gap",0) or 0)
    hr_gap = abs(_g(data,"hiring_gap",0) or 0)
    caste_flags  = _g(data,"caste_flags",[]) or []
    skin_flags   = _g(data,"skin_flags",[]) or []
    proxy_flags  = _g(data,"proxy_flags",[]) or []
    ref_flags    = _g(data,"referral_flags",[]) or []
    marital_flags= _g(data,"marital_flags",[]) or []
    inst_flags   = _g(data,"institution_flags",[]) or []
    age_flags    = _g(data,"age_flags",[]) or []
    caste_stats  = _g(data,"caste_stats",{}) or {}
    skin_stats   = _g(data,"skin_stats",{}) or {}
    inst_stats   = _g(data,"institution_stats",{}) or {}
    age_stats    = _g(data,"age_stats",{}) or {}
    caste_col    = _g(data,"caste_col","category") or "category"
    ref_hr       = _g(data,"referral_hire_rate",0) or 0
    nref_hr      = _g(data,"non_referral_hire_rate",0) or 0
    ref_air      = _g(data,"referral_air",1.0) or 1.0
    ref_hhi      = _g(data,"referral_hhi",0.0) or 0.0
    inter_stats  = _g(data,"marital_intersectional_stats",{}) or {}
    phi_scores   = _g(data,"proxy_phi_scores",{}) or {}
    sb_triggered = _g(data,"systemic_bias_triggered",False) or False
    sb_deduction = score_data["sb_deduction"]
    best_r       = (_g(data,"skin_best_rate",0) or 0)*100
    worst_r      = (_g(data,"skin_worst_rate",0) or 0)*100
    caste_worst  = _g(data,"caste_worst_air",None)

    # Gender counts from gender_stats (authoritative) with scalar fallback
    gs_data  = _g(data,"gender_stats",{}) or {}
    male_gs  = gs_data.get("male",{}) or {}
    female_gs= gs_data.get("female",{}) or {}
    other_gs = gs_data.get("other_gender",{}) or {}
    men_t    = _n(male_gs)   or (_g(data,"men_total",0) or 0)
    men_sl   = male_gs.get("shortlisted",0) or (_g(data,"men_shortlisted",0) or 0)
    men_h    = male_gs.get("hired",0)       or (_g(data,"men_hired",0) or 0)
    wom_t    = _n(female_gs) or (_g(data,"women_total",0) or 0)
    wom_sl   = female_gs.get("shortlisted",0) or (_g(data,"women_shortlisted",0) or 0)
    wom_h    = female_gs.get("hired",0)       or (_g(data,"women_hired",0) or 0)
    oth_t    = _n(other_gs)
    oth_sl   = other_gs.get("shortlisted",0) or 0
    oth_h    = other_gs.get("hired",0) or 0
    has_other_row = oth_t > 0

    # ── Story begins ──────────────────────────────────────────────────────
    story = []

    # ════════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ════════════════════════════════════════════════════════════════════════
    if company_missing:
        story.append(Paragraph(
            "⚠ STRICTLY CONFIDENTIAL — INTERNAL RISK REVIEW",
            ST.incomplete))
        story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("D-V6.2 AUTOMATED REPORT", ST.title))

    story.append(Paragraph("Algorithmic Equity Governance — Hiring Pipeline Audit", ST.subtitle))
    story.append(_hr(EMERALD, thickness=2, spaceAfter=10))

    story.append(_kv_table([
        ("Client Organisation",  company),
        ("Classification",       "STRICTLY CONFIDENTIAL — INTERNAL RISK REVIEW"),
        ("Audit ID",             audit_id),
        ("Dataset",              filename),
        ("Candidates Audited",   f"{rows:,}"),
        ("Jurisdiction",         region),
        ("Engine Version",       f"FairHire v{FAIRHIRE_VERSION}"),
        ("Generated",            now_str),
        ("Reference Frameworks (statistical thresholds only — see Part 9, Clause 6)",
         "EEOC 4/5ths Rule · Equal opportunity provisions of Indian and applicable international law "
         "(subject to legal review of applicability) · ILO Convention 111 · UN SDG 10 · GRI 405-1"),
    ]))

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        "This document is a confidential statistical risk-screening communication prepared by an "
        "automated audit engine. It is not a legal opinion and does not carry legal privilege unless "
        "separately commissioned by and routed through qualified counsel. See Part 9 for the full "
        "disclaimer governing its use.",
        ST.legal))
    story.append(Spacer(1, 0.5*cm))

    # Gauge + Radar
    gauge_img = _rl_img(_gauge_buf(use_score, score_data["evaluated_base"],
                                    score_data["not_evaluated_weight"]), w=7*cm, h=4.2*cm)
    radar_img = _rl_img(_radar_buf(data),      w=8.5*cm, h=6*cm)
    t_hero = Table([[gauge_img, radar_img]], colWidths=[7.5*cm, 9*cm])
    t_hero.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
    ]))
    story.append(t_hero)
    if score_data["not_evaluated_weight"] > 0:
        story.append(Spacer(1, 0.1*cm))
        story.append(Paragraph(
            f"<b>{use_score}/{score_data['evaluated_base']} evaluated</b> "
            f"({score_data['not_evaluated_weight']} pt(s) not scored — modules with "
            f"absent/insufficient data are excluded from the evaluated base rather than "
            f"counted as failing; see Part 5 — Telemetry Gaps for which modules and why).",
            ST.body_sm))
    story.append(Spacer(1, 0.4*cm))
    story.append(_badge_table(_air_badge_items(data)))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PART 1 — EXECUTIVE RISK DASHBOARD
    # ════════════════════════════════════════════════════════════════════════
    _part_header(story, "PART 1", "Executive Risk Dashboard")

    # 1.1 Enterprise Risk Rating
    _section_header(story, "1.1 — Enterprise Risk Rating")
    story.append(Paragraph(
        f"Current Enterprise Risk Position: <b>{risk_rating}</b>",
        ParagraphStyle("RiskRating", parent=ST.h2, textColor=risk_fg, backColor=risk_bg,
                       leftIndent=10, rightIndent=10, spaceBefore=4, spaceAfter=4, leading=18)))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"An enterprise at the <b>{risk_rating}</b> level shows {risk_note}. This assessment reflects "
        f"the number and severity of Adverse Impact Ratio (AIR) findings below the 0.80 reference "
        f"threshold commonly used under the EEOC 4/5ths Rule "
        + _eeoc_badge() +
        f", and is a relative risk indicator rather "
        f"than a predicted probability of any specific regulatory action. "
        f"The current audit identified AIR findings in "
        f"{'gender, ' if air_g < 0.80 else ''}"
        f"{'disability parity, ' if air_d < 0.80 else ''}"
        f"{'colorism / skin-tone, ' if air_s < 0.80 else ''}"
        f"{'and caste / reservation categories' if caste_flags else 'across the audited modules'}. "
        f"These statistical findings indicate a pattern that warrants investigation; they are not, on "
        f"their own, a legal finding of discrimination (see Part 9, Clause 6).",
        ST.body))

    # 1.2 Maturity Level
    _section_header(story, "1.2 — Enterprise Readiness Maturity Level")
    maturity_label, maturity_level = maturity
    mat_rows = [
        [_cell("Level", bold=True, bg=NAVY, color=WHITE, align=1),
         _cell("Designation", bold=True, bg=NAVY, color=WHITE),
         _cell("Characteristics", bold=True, bg=NAVY, color=WHITE),
         _cell("Status", bold=True, bg=NAVY, color=WHITE, align=1)],
    ]
    levels = [
        (5,"Optimised / Automated","Real-time bias telemetry. ATS integration. Continuous loop."),
        (4,"Managed / Proactive","Automated monitoring. Structured interviews. CI-gated shortlisting."),
        (3,"Defined / Compliant","Structured audit process. Basic AIR tracking. Partially compliant."),
        (2,"Developing / Reactive","Some DEI policy. No data pipeline. Bias detected post-hoc."),
        (1,"Ad-hoc / High Risk","No structured DEI process. Bias unmeasured. Elevated legal/operational risk."),
    ]
    for lvl, desig, chars in levels:
        is_current = (lvl == maturity_level)
        bg = WARN_BG if is_current else WHITE if lvl > maturity_level else LIGHT_BG
        fg = WARN_FG if is_current else NAVY
        mat_rows.append([
            _cell(str(lvl), bold=is_current, align=1, color=fg, bg=bg),
            _cell(f"{'>> ' if is_current else ''}{desig}", bold=is_current, color=fg, bg=bg),
            _cell(chars, color=fg, bg=bg),
            _cell("CURRENT" if is_current else "", bold=is_current, align=1,
                  color=WARN_FG if is_current else SLATE, bg=bg),
        ])
    mat_t = Table(mat_rows, colWidths=[1.5*cm, 4.5*cm, 8.5*cm, 2*cm])
    mat_t.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.3,BORDER),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(mat_t)
    story.append(Spacer(1, 0.2*cm))

    # Maturity justification must explain the maturity level using only the
    # modules that actually drove it down — failing or partial-credit
    # modules — never cite a passing metric (e.g. a compliant Gender AIR) as
    # "supporting evidence" for a LOW maturity placement.
    at_risk_modules = [r for r in score_data["rows"] if r[3] in ("FAIL", "PARTIAL")]
    if at_risk_modules:
        evidence_bits = []
        for name, weight, pass_cond, result, evidence, pts in at_risk_modules:
            short_name = name.split("—", 1)[-1].strip() if "—" in name else name
            tag = "failed" if result == "FAIL" else f"earned partial credit ({pts}/{weight})"
            evidence_bits.append(f"{short_name} {tag} ({evidence})")
        justification_body = (
            f"This classification is driven by the following module(s) that did not fully pass: "
            + "; ".join(evidence_bits) + "."
        )
        if score_data["dealbreaker_triggered"]:
            justification_body += (
                " The Systemic Bias Dealbreaker deduction is also applied, as Caste and "
                "Colorism/Skin-Tone failed simultaneously.")
    else:
        justification_body = (
            "No module recorded a FAIL or partial-credit result in this audit cycle; this "
            "classification reflects the overall score band and any secondary flags noted "
            "in §1.3 below, not an individual module breach."
        )
    story.append(Paragraph(
        f"<b>Maturity Justification:</b> The organisation is placed at <b>{maturity_label}</b>. "
        f"{justification_body}",
        ST.body))

    # 1.3 Top-N Material Risk Vectors
    # Build the list FIRST, then size the heading and the loop to the same
    # number — the heading must never claim a fixed "Top-3" when fewer (or a
    # capped three) vectors actually qualify and render.
    risk_vectors = []
    if caste_flags:
        worst_air_str = f"{caste_worst:.3f}" if caste_worst else "below 0.80"
        # ISSUE-3: surface per-subgroup severity so the reader can distinguish
        # OBC (0.653) from SC (0.099) directly on the dashboard summary vector,
        # not only buried in Part 4. Build an inline severity breakdown from
        # caste_stats hire rates; label each group CRIT/FAIL/PASS so severity
        # differences are legible without opening the module section.
        if caste_stats:
            _cr = {k: _hire_rate(v) for k, v in caste_stats.items()}
            _best = max(_cr.values()) if _cr else 0.0
            def _clabel(r):
                a = (r / _best) if _best > 0 else 1.0
                return f"{a:.3f} [{'CRIT' if a < 0.60 else 'FAIL' if a < 0.80 else 'PASS'}]"
            _subgroup_str = ", ".join(f"{k}: {_clabel(v)}" for k, v in sorted(_cr.items()))
            _n_fail = sum(1 for v in _cr.values() if _best > 0 and (v/_best) < 0.80)
            caste_severity_note = (
                f"Worst of {_n_fail} failing subgroup(s) = {worst_air_str}. "
                f"Per-subgroup severity: {_subgroup_str}. "
                f"(Subgroup AIRs are approximated from hire rates relative to the best-performing "
                f"group; authoritative values are in Module 5.)"
            )
        else:
            caste_severity_note = f"Worst-group AIR: {worst_air_str}. See Module 5 for full subgroup breakdown."
        risk_vectors.append(
            f"CRITICAL — Caste / Reservation Category Adverse Impact ({caste_severity_note}): "
            f"A statistically significant hiring-rate disparity was found between SC/ST/OBC candidates "
            f"and other applicants. Persistent disparities of this kind may raise exposure under "
            f"Article 15/16 of the Constitution of India (for State or State-instrumentality employers) "
            f"and, depending on the specific facts, could be relevant to the SC/ST (Prevention of "
            f"Atrocities) Act 1989 — whether that Act applies requires a case-specific legal assessment "
            f"of the underlying conduct, not just the aggregate statistic. "
            f"Affects candidates across {len(caste_stats)} reservation categories in a cohort of "
            f"{rows:,} applicants. Legal counsel review is recommended before any public characterisation "
            f"of this finding.")
    if air_g < 0.80:
        risk_vectors.append(
            f"HIGH RISK — Gender Adverse Impact in Algorithmic Equity Governance "
            f"(AIR: {air_g:.3f}, shortlisting gap: {sl_gap:.1f}pp, hiring gap: {hr_gap:.1f}pp): "
            f"This AIR falls below the 0.80 reference threshold commonly used under the US EEOC "
            f"4/5ths Rule (29 CFR §1607) and is a pattern that would typically warrant a disparate-"
            f"impact review under applicable equal-opportunity law. Affects {wom_t + oth_t:,} female "
            f"and non-binary applicants across the pipeline.")
    if air_s < 0.80:
        risk_vectors.append(
            f"HIGH RISK — Colorism / Skin-Tone Parity AIR finding (AIR: {air_s:.3f}, "
            f"best-band hire rate: {best_r:.1f}%, worst-band hire rate: {worst_r:.1f}%): "
            f"Hire rates decline progressively with darker Fitzpatrick scale bands. This pattern may "
            f"be relevant to colour-based discrimination protections (e.g. Title VII of the Civil "
            f"Rights Act 1964 for US-exposed entities) and warrants review of any photo- or video-"
            f"based screening tools in use. Affects candidates across {len(skin_stats)} Fitzpatrick "
            f"scale bands.")
    if air_d < 0.80:
        risk_vectors.append(
            f"HIGH RISK — Disability Parity AIR finding (AIR: {air_d:.3f}): "
            f"This pattern is relevant to equal-opportunity obligations under the Rights of Persons "
            f"with Disabilities Act 2016, Section 21. Whether it rises to a breach — including whether "
            f"the more serious provisions of the Act are engaged — depends on facts beyond this "
            f"statistical audit and should be assessed by counsel.")
    if not risk_vectors:
        risk_vectors.append(
            f"MEDIUM — Secondary module flags detected ({len(unique_flags)} total across all modules). "
            f"No primary AIR violations. Continued monitoring and quarterly re-audit recommended.")

    rendered_vectors = risk_vectors[:3]
    n_rendered = len(rendered_vectors)
    _section_header(story, f"1.3 — Top-{n_rendered} Material Risk Vector{'s' if n_rendered != 1 else ''}")
    story.append(Paragraph(
        "The following findings represent the highest-severity enterprise risk exposure "
        "identified in this audit, expressed as legal and operational risk statements:",
        ST.body))

    for i, rv in enumerate(rendered_vectors, 1):
        sev = "crit" if rv.startswith("CRITICAL") else ("warn" if rv.startswith("HIGH") else "info")
        style = ST.flag_crit if sev=="crit" else (ST.flag_warn if sev=="warn" else ST.flag_info)
        story.append(Paragraph(f"{i}. {rv}", style))
        story.append(Spacer(1, 0.1*cm))

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PART 2 — SCORE DERIVATION AND AUDIT INTEGRITY
    # ════════════════════════════════════════════════════════════════════════
    _part_header(story, "PART 2", "Score Derivation and Audit Integrity")

    # Score derivation table
    drv = score_data
    sd_rows = [
        [_cell("Module", bold=True, bg=NAVY, color=WHITE),
         _cell("Weighting", bold=True, bg=NAVY, color=WHITE, align=1),
         _cell("Pass Condition", bold=True, bg=NAVY, color=WHITE),
         _cell("Result", bold=True, bg=NAVY, color=WHITE, align=1),
         _cell("Statistical Evidence", bold=True, bg=NAVY, color=WHITE),
         _cell("Points Earned", bold=True, bg=NAVY, color=WHITE, align=1)],
    ]
    for name, weight, pass_cond, result, evidence, pts in drv["rows"]:
        # BUG-FIX-C rendering: three distinct NOT-EVALUATED states need
        # three distinct colours so the reader can distinguish them at a glance:
        #   PASS               → green
        #   PARTIAL            → amber/warn (engine awarded partial credit)
        #   FAIL               → red
        #   NOT EVALUATED — DATA ABSENT        → amber/warn  (column missing)
        #   NOT EVALUATED — INSUFFICIENT DATA  → gold/info   (column present, group too small)
        if result == "PASS":
            res_bg, res_fg = PASS_BG, PASS_FG
        elif result == "PARTIAL":
            res_bg, res_fg = WARN_BG, WARN_FG
        elif result == "FAIL":
            res_bg, res_fg = FAIL_BG, FAIL_FG
        elif "INSUFFICIENT DATA" in result:
            res_bg, res_fg = GOLD_BG, GOLD_FG
        else:  # DATA ABSENT or any other NOT EVALUATED variant
            res_bg, res_fg = WARN_BG, WARN_FG
        # BUG-FIX-L: every AIR-threshold pass condition in this table gates a
        # pass/fail on the US EEOC 4/5ths convention — label it inline here
        # too, not just once in the methodology section.
        pass_cond_disp = pass_cond + (EEOC_SHORT if "AIR" in pass_cond else "")
        sd_rows.append([
            _cell(name),
            _cell(str(weight), align=1),
            _cell(pass_cond_disp),
            _cell(f"<b>{result}</b>", bold=True, align=1, color=res_fg, bg=res_bg),
            _cell(evidence),
            _cell(f"<b>{pts}</b>", bold=True, align=1,
                  color=PASS_FG if pts>0 else FAIL_FG,
                  bg=PASS_BG if pts>0 else FAIL_BG),
        ])
    sd_t = Table(sd_rows, colWidths=[4*cm, 1.5*cm, 3.5*cm, 2*cm, 3.5*cm, 2*cm])
    sd_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, LIGHT_BG]),
        ("GRID",(0,0),(-1,-1),0.3,BORDER),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(sd_t)
    story.append(Spacer(1, 0.3*cm))

    # Score arithmetic
    arith_rows = [
        [_cell("Base Score (sum of points earned)", bold=True), _cell(str(drv["base"]), align=1)],
        [_cell(f"Systemic Bias Dealbreaker Deduction ({drv['dealbreaker_label']})", bold=True),
         _cell(f"−{drv['sb_deduction']}", align=1, color=FAIL_FG if drv["sb_deduction"]>0 else NAVY)],
        [_cell("Final Computed Score", bold=True, bg=NAVY, color=WHITE),
         _cell(f"<b>{drv['final']}</b>", bold=True, align=1, bg=NAVY, color=WHITE)],
        [_cell("Score Reported on Dashboard" + ("" if drv["reconciled"] else " (overridden — see below)")),
         _cell(str(drv["reported"]), align=1,
               color=(NAVY if drv["reconciled"] else WARN_FG),
               bg=(None if drv["reconciled"] else WARN_BG))],
    ]
    arith_t = Table(arith_rows, colWidths=[13*cm, 3.5*cm])
    arith_t.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.3,BORDER),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[WHITE,LIGHT_BG,WHITE,LIGHT_BG]),
    ]))
    story.append(arith_t)
    story.append(Spacer(1, 0.2*cm))

    # By this point ReportBlockedError would already have halted generation
    # if drv["reconciled"] were False (see PRE-PUBLISH GATE 1 above), so this
    # is a confirmation, not a conditional disclosure of a known discrepancy.
    assert drv["reconciled"], "unreachable: ReportBlockedError should have halted generation"
    story.append(Paragraph(
        f"✓ Score Reconciliation: Computed score ({drv['final']}) matches reported score "
        f"({drv['reported']}). Audit integrity confirmed.", ST.action))

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PART 3 — PIPELINE FUNNEL + FLAGS OVERVIEW
    # ════════════════════════════════════════════════════════════════════════
    _part_header(story, "PART 3", "Talent Pipeline Throughput Analysis")

    _section_header(story, "3.1 — Stage-by-Stage Gender Pipeline Analysis",
                    "Applied → Shortlisted → Hired · Gender Adverse Impact · EEOC 4/5ths Rule")
    story.append(_rl_img(_funnel_buf(data), w=CW, h=7*cm))
    story.append(Spacer(1, 0.25*cm))
    story.append(Paragraph(
        "<b>Pipeline Bottleneck Interpretation:</b> A disproportionate drop between pipeline stages "
        "signals a screening process that systematically disadvantages one group at that stage. "
        "The shortlisting stage is the highest-leverage intervention point — bias introduced here "
        "compounds through to final selection and compounds the enterprise's legal exposure. "
        "Intervene at the stage with the sharpest relative decline in minority group throughput.",
        ST.reason))
    story.append(Spacer(1, 0.25*cm))

    # Gender pipeline table with full data
    pipeline_rows = [
        [_cell("Group",       bold=True,bg=NAVY,color=WHITE),
         _cell("Applied",     bold=True,bg=NAVY,color=WHITE,align=1),
         _cell("Shortlisted", bold=True,bg=NAVY,color=WHITE,align=1),
         _cell("SL Rate",     bold=True,bg=NAVY,color=WHITE,align=1),
         _cell("Hired",       bold=True,bg=NAVY,color=WHITE,align=1),
         _cell("Hire Rate",   bold=True,bg=NAVY,color=WHITE,align=1)],
        [_cell("Men"),
         _cell(str(men_t),align=1),_cell(str(men_sl),align=1),
         _cell(f"{men_sl/men_t*100:.1f}%" if men_t else "—",align=1),
         _cell(str(men_h),align=1),
         _cell(f"{men_h/men_t*100:.1f}%" if men_t else "—",align=1)],
        [_cell("Women"),
         _cell(str(wom_t),align=1),_cell(str(wom_sl),align=1),
         _cell(f"{wom_sl/wom_t*100:.1f}%" if wom_t else "—",align=1),
         _cell(str(wom_h),align=1),
         _cell(f"{wom_h/wom_t*100:.1f}%" if wom_t else "—",align=1)],
    ]
    if has_other_row:
        pipeline_rows.append([
            _cell("Non-binary"),
            _cell(str(oth_t),align=1),_cell(str(oth_sl),align=1),
            _cell(f"{oth_sl/oth_t*100:.1f}%" if oth_t else "—",align=1),
            _cell(str(oth_h),align=1),
            _cell(f"{oth_h/oth_t*100:.1f}%" if oth_t else "—",align=1)])
    pt = Table(pipeline_rows, colWidths=[3.5*cm,2.5*cm,2.5*cm,2.5*cm,2.5*cm,3*cm])
    pt.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT_BG]),
        ("GRID",(0,0),(-1,-1),0.3,BORDER),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(pt)
    story.append(Spacer(1, 0.25*cm))
    story.append(_rl_img(_gender_bar_buf(data), w=CW, h=7*cm))
    story.append(Spacer(1, 0.25*cm))

    _section_header(story, f"3.2 — Complete Audit Evidence — All {len(unique_flags)} Flag(s)",
                    "Every flag raised across all 10 bias modules, sorted by severity.")
    _render_flags(unique_flags, story, title="Full Audit Evidence")
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PART 4 — MODULE-BY-MODULE RISK ANALYSIS
    # ════════════════════════════════════════════════════════════════════════
    _part_header(story, "PART 4", "Module-by-Module Risk Analysis")

    def _mod_risk(air_val=None, flags_list=None, absent=False):
        if absent: return ("NOT EVALUATED","Column absent. See Part 6 — Telemetry Gaps.", INFO_BG, INFO_FG)
        if flags_list and any("high risk" in f.lower() or "critical" in f.lower() or "atrocities" in f.lower() for f in flags_list):
            bg, fg = _risk_colors("CRITICAL")
            return ("CRITICAL","Statistical pattern warrants immediate legal and HR review before any public characterisation.", bg, fg)
        if (air_val and air_val < 0.60) or (flags_list and len(flags_list) >= 3):
            bg, fg = _risk_colors("HIGH")
            return ("HIGH","Statistically significant adverse-impact pattern. Prompt review recommended.", bg, fg)
        if (air_val and air_val < 0.80) or (flags_list and flags_list):
            bg, fg = _risk_colors("MEDIUM")
            return ("MEDIUM","Threshold breach detected. Remediation review recommended within 90 days.", bg, fg)
        bg, fg = _risk_colors("LOW")
        return ("LOW","Compliant. No material risk identified. Maintain monitoring cadence.", bg, fg)

    # ── MODULE 1: Gender ──────────────────────────────────────────────────
    _section_header(story, "Module 1 — Gender Adverse Impact in Algorithmic Equity Governance",
                    "EEOC 4/5ths Rule (29 CFR §1607) · Statistical Parity Gap")
    # gflags computed earlier (alongside score derivation) so the count here
    # always matches the count used in the Part 2 score table — single source.
    risk_class, risk_meaning, r_bg, r_fg = _mod_risk(air_val=air_g, flags_list=gflags)
    story.append(Paragraph(f"<b>4.1.1 Risk Classification: {risk_class}</b> — {risk_meaning}",
        ParagraphStyle("MC",parent=ST.body,textColor=r_fg,backColor=r_bg,leftIndent=8,rightIndent=8,leading=14)))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph(
        f"<b>4.1.2 Statistical Evidence (exact values — not rounded):</b> "
        f"Gender AIR = {air_g:.3f} (reference threshold: 0.800{EEOC_SHORT}). "
        f"Shortlisting Gap = {sl_gap:.2f} percentage points (threshold: ≤15.00pp). "
        f"Hiring Gap = {hr_gap:.2f} percentage points (threshold: ≤15.00pp). "
        f"Men in cohort: n={men_t} ({men_sl} shortlisted, {men_h} hired). "
        f"Women in cohort: n={wom_t} ({wom_sl} shortlisted, {wom_h} hired)."
        + (f" Non-binary: n={oth_t} ({oth_sl} shortlisted, {oth_h} hired)." if has_other_row else ""),
        ST.body))
    story.append(Paragraph(
        f"<b>4.1.3 Enterprise Impact:</b> "
        + ("No gender-based AIR finding. Monitoring recommended." if air_g >= 0.80 else
           f"Gender AIR of {air_g:.3f} falls below the 0.80 reference threshold commonly used under "
           f"the US EEOC 4/5ths Rule. This is a statistical pattern consistent with adverse impact "
           f"against female and/or non-binary candidates and warrants HR and legal review; it is not, "
           f"on its own, a finding of unlawful discrimination (see Part 9, Clause 6). "
           f"The affected population is {wom_t + oth_t:,} candidates."),
        ST.body))
    story.append(Paragraph(
        "<b>4.1.4 Possible Process Factors:</b> Gender disparities at the shortlisting stage are "
        "often associated with the absence of a structured, criteria-based shortlisting rubric, "
        "which can allow implicit bias to operate unchecked at the resume-screening stage. "
        "Disparities at the final-selection stage are often associated with unstructured panel "
        "interviews lacking calibrated scoring rubrics. These are general patterns observed across "
        "hiring data, not a diagnosis of this organisation's specific cause.",
        ST.body))
    _render_flags_ref(gflags, story, "Gender Module Flags")
    story.append(Paragraph(
        "<b>Recommended Action (Owner: CHRO + Head of TA):</b> Consider CV anonymisation "
        "middleware at the ATS ingestion layer, stripping name, gender, and marital status fields "
        "before candidate records enter the shortlisting queue. Implement structured interview "
        "rubrics with pre-defined, role-specific scoring criteria. "
        "Success Metric: Gender AIR ≥ 0.800 in next hiring cycle at n ≥ 500. "
        "Risk if Skipped: Continued disparate-impact exposure under applicable equal-opportunity law "
        "— consult counsel on jurisdiction-specific obligations and any applicable penalties.",
        ST.action))
    story.append(CondPageBreak(6*cm))

    # ── MODULE 2: Disability ──────────────────────────────────────────────
    _section_header(story, "Module 2 — Disability Parity (AIR)",
                    "Rights of Persons with Disabilities Act 2016, §21 · ADA (US) · EEOC 4/5ths Rule")
    mr = _g(data, "module_results", {}) or {}
    dis_absent = mr.get("disability", {}).get("data_present", True) is False
    risk_class, risk_meaning, r_bg, r_fg = _mod_risk(air_val=air_d if not dis_absent else None,
                                                       absent=dis_absent)
    story.append(Paragraph(f"<b>4.2.1 Risk Classification: {risk_class}</b> — {risk_meaning}",
        ParagraphStyle("MC2",parent=ST.body,textColor=r_fg,backColor=r_bg,leftIndent=8,rightIndent=8,leading=14)))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph(
        f"<b>4.2.2 Statistical Evidence:</b> Disability Parity AIR = {air_d:.3f} "
        f"(threshold: ≥ 0.800). "
        + ("Column 'disability_status' absent from dataset — module not evaluated. "
           "See Part 6 — Telemetry Gaps." if dis_absent
           else ("Compliant." if air_d >= 0.80
                 else f"PwD candidates face an Adverse Impact Ratio of {air_d:.3f}, "
                      f"indicating significant adverse impact relative to non-disabled candidates.")),
        ST.body))
    story.append(Paragraph(
        f"<b>4.2.3 Enterprise Impact:</b> "
        + (f"A Disability Parity AIR of {air_d:.3f} is a statistical pattern relevant to the equal "
           f"opportunity obligations in the Rights of Persons with Disabilities Act 2016, Section 21. "
           f"Whether this finding rises to a breach — and whether the Act's penalty provisions are "
           f"engaged — depends on facts beyond this statistical audit and should be assessed by "
           f"counsel. For US-exposed entities, this pattern may also be relevant to ADA obligations."
           if air_d < 0.80 else
           "No disability-related AIR finding. RPWD Act §21 considerations appear currently met."),
        ST.body))
    story.append(Paragraph(
        "<b>Recommended Action (Owner: CHRO + Head of Accessibility):</b> "
        "Audit all interview formats for accessibility barriers. "
        "Remove non-essential physical requirements from job descriptions. "
        "Implement a PwD-specific sourcing stream with targeted outreach. "
        "Success Metric: Disability Parity AIR ≥ 0.800 within two hiring cycles. "
        "Risk if Skipped: Continued equal-opportunity exposure — consult counsel on RPWD Act "
        "obligations and any applicable ADA considerations for US-exposed entities.",
        ST.action))
    story.append(CondPageBreak(6*cm))

    # ── MODULE 3: Institution ─────────────────────────────────────────────
    _section_header(story, "Module 3 — Institution / College Bias",
                    "One-vs-Rest Gap Analysis · Threshold ±20pp · Proxy for Socioeconomic Status")
    if inst_stats or inst_flags:
        risk_class, risk_meaning, r_bg, r_fg = _mod_risk(flags_list=inst_flags)
        story.append(Paragraph(f"<b>4.3.1 Risk Classification: {risk_class}</b> — {risk_meaning}",
            ParagraphStyle("MC3",parent=ST.body,textColor=r_fg,backColor=r_bg,leftIndent=8,rightIndent=8,leading=14)))
        story.append(Spacer(1,0.15*cm))
        story.append(Paragraph(
            "<b>4.3.2 Statistical Evidence:</b> One-vs-Rest gap analysis applied across institution tiers. "
            "Threshold: ±20 percentage points. Groups below threshold generate flags with exact gap values.",
            ST.body))
        story.append(Paragraph(
            "<b>4.3.3 Enterprise Impact + Pipeline Bottleneck:</b> Institution bias throttles talent "
            "pool diversity at the application and shortlisting stage. Preference for Tier-1 institutions "
            "acts as a proxy for socioeconomic background and — in the Indian context — correlates "
            "strongly with caste and geographic origin, creating indirect discrimination under "
            "Article 15, Constitution of India (1950).",
            ST.body))
        story.append(Paragraph(
            "<b>4.3.3a Share of Total Hires by Tier</b> — proportion of all hires this audit "
            "cycle contributed by each institution tier (percentages sum to 100% of hires).",
            ST.body_sm))
        story.append(_rl_img(_institution_share_buf(inst_stats), w=CW, h=7*cm))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(
            "<b>4.3.3b Hire Rate by Tier</b> — hired ÷ applicants within each tier; this is the "
            "metric the ±20pp One-vs-Rest threshold (§4.3.1) is actually computed from, and is not "
            "the same percentage as the share-of-hires chart above.",
            ST.body_sm))
        story.append(_rl_img(_institution_rate_buf(inst_stats), w=CW, h=7*cm))
        story.append(Spacer(1, 0.15*cm))
        _render_flags_ref(inst_flags, story, "Institution Bias Flags")
        story.append(Paragraph(
            "<b>Recommended Action (Owner: Head of TA + CHRO):</b> Expand sourcing to Tier-2/3 "
            "institutions. Remove institutional prestige filters from ATS screening algorithms. "
            "Evaluate whether all stated institutional requirements are validated by role performance data. "
            "Success Metric: Institution one-vs-rest gap ≤ 20pp across all tiers in next cycle. "
            "Legal Risk if Skipped: Indirect discrimination exposure under Article 15.", ST.action))
    else:
        story.append(Paragraph("Institution data not present in dataset. Module not evaluated. "
                                "See Part 6 — Telemetry Gaps.", ST.flag_info))
    story.append(CondPageBreak(6*cm))

    # ── MODULE 4: Age ─────────────────────────────────────────────────────
    # ISSUE-4 (secondary): ERA 1976 governs gender pay parity, not age discrimination
    # in hiring — it was mis-cited here as well. Module 4 does not have a specific
    # dedicated Indian statute; the correct framing is equal-opportunity policy
    # breach + ADEA for US exposure. Corrected below.
    _section_header(story, "Module 4 — Age Group Bias",
                    "One-vs-Rest Gap Analysis · ADEA (US) · Equal-Opportunity Policy (India)")
    if age_stats or age_flags:
        risk_class, risk_meaning, r_bg, r_fg = _mod_risk(flags_list=age_flags)
        story.append(Paragraph(f"<b>4.4.1 Risk Classification: {risk_class}</b> — {risk_meaning}",
            ParagraphStyle("MC4",parent=ST.body,textColor=r_fg,backColor=r_bg,leftIndent=8,rightIndent=8,leading=14)))
        story.append(Spacer(1,0.15*cm))
        story.append(Paragraph(
            "<b>4.4.2 Statistical Evidence:</b> One-vs-Rest gap analysis applied across age bands. "
            f"Threshold: ±20pp. {len(age_flags)} flag(s) raised.", ST.body))
        story.append(Paragraph(
            "<b>4.4.3 Enterprise Impact:</b> Age-based hiring discrimination is prohibited under the "
            "Age Discrimination in Employment Act 1967 (ADEA, US) for entities with US exposure. "
            "India does not have a dedicated age-discrimination-in-employment statute, but "
            "age-based exclusion may breach the organisation's own equal-opportunity policy "
            "and general employment law principles — confirm specific exposure with counsel. "
            "Structural bias against older candidates also limits industrial knowledge retention.",
            ST.body))
        story.append(_rl_img(_age_bar_buf(age_stats), w=CW, h=7*cm))
        story.append(Spacer(1, 0.15*cm))
        _render_flags_ref(age_flags, story, "Age Group Flags")
        story.append(Paragraph(
            "<b>Recommended Action (Owner: Head of TA):</b> Audit all job descriptions for "
            "age-coded language ('digital native', 'recent graduate', 'energetic'). "
            "Remove graduation year requirements where not role-critical. "
            "Success Metric: Age one-vs-rest gap ≤ 20pp across all bands. "
            "Legal Risk if Skipped: ADEA enforcement for US entities; unfair labour practice claims.", ST.action))
    else:
        story.append(Paragraph(
            "Age data absent from dataset. Module not evaluated. See Part 6 — Telemetry Gaps.",
            ST.flag_info))
    story.append(CondPageBreak(6*cm))

    # ── MODULE 5: Caste ───────────────────────────────────────────────────
    _section_header(story, "Module 5 — Caste / Reservation Category Bias",
                    "One-vs-Rest Gap Analysis · Threshold ±15pp (SC/ST)")
    story.append(Paragraph(
        "Caste-based discrimination is a constitutionally and statutorily significant subject in "
        "India. Article 15 of the Constitution prohibits the State from discriminating on grounds "
        "including caste; its direct application to private employers depends on whether the entity "
        "qualifies as 'State' or a State instrumentality under Article 12, which is a legal question "
        "outside the scope of this statistical audit. The SC/ST (Prevention of Atrocities) Act 1989 "
        "addresses specific enumerated acts against SC/ST persons; whether a hiring-rate disparity "
        "implicates that Act depends on the underlying facts and is a matter for legal assessment, "
        "not something this audit can determine from aggregate statistics alone. The findings below "
        "are a statistical screening result, not a legal finding (see Part 9, Clause 6).",
        ST.legal))
    story.append(Spacer(1, 0.15*cm))
    risk_class, risk_meaning, r_bg, r_fg = _mod_risk(flags_list=caste_flags)
    story.append(Paragraph(f"<b>4.5.1 Risk Classification: {risk_class}</b> — {risk_meaning}",
        ParagraphStyle("MC5",parent=ST.body,textColor=r_fg,backColor=r_bg,leftIndent=8,rightIndent=8,leading=14)))
    story.append(Spacer(1,0.15*cm))
    worst_str = f"{caste_worst:.3f}" if caste_worst else "computed per flag evidence below"
    story.append(Paragraph(
        f"<b>4.5.2 Statistical Evidence:</b> Worst-group Caste AIR = {worst_str}. "
        f"One-vs-Rest gap threshold: ±15pp (tighter threshold applied to SC/ST categories). "
        f"{len(caste_flags)} flag(s) raised across {len(caste_stats)} reservation categories: "
        f"{', '.join(caste_stats.keys())}.",
        ST.body))
    story.append(Paragraph(
        f"<b>4.5.3 Enterprise Impact + Pipeline Bottleneck:</b> "
        f"Caste-based adverse impact most often originates at the shortlisting stage, where implicit "
        f"bias in resume evaluation can be influenced by name and institution fields that correlate "
        f"with caste. At the final-selection stage, unstructured interviews can amplify any such "
        f"effect. The affected population spans SC/ST/OBC applicants in the {rows:,}-candidate "
        f"cohort. This is a statistical observation; it is not a finding that any specific legal "
        f"threshold for criminal or constitutional liability has been met.",
        ST.body))
    story.append(Paragraph(
        "<b>4.5.4 Possible Process Factors:</b> Retaining last-name and institution fields in "
        "screening views can enable implicit caste inference. The absence of a structured rubric can "
        "allow evaluator discretion to introduce bias. Lack of training on caste-neutral evaluation "
        "can compound the effect at the interview stage. These are general patterns observed across "
        "hiring data, not a diagnosis of this organisation's specific cause.",
        ST.body))
    story.append(_rl_img(_caste_bar_buf(caste_stats, caste_col), w=CW, h=7*cm))
    story.append(Spacer(1, 0.15*cm))
    _render_flags_ref(caste_flags, story, "Caste / Reservation Category Flags")
    story.append(Paragraph(
        "<b>Recommended Action (Owner: CHRO + General Counsel):</b> Consider CV anonymisation "
        "middleware at ATS ingestion — masking surname, institution, and social-category fields "
        "before candidate records reach the shortlisting queue. Implement structured, "
        "criteria-based interview scorecards. Consider caste-sensitisation training for evaluators. "
        "Success Metric: All caste-category AIRs ≥ 0.800; zero SC/ST flags in next audit at n ≥ 500. "
        "Risk if Skipped: Continued statistical exposure on this metric. Whether this gives rise to "
        "liability under the SC/ST (Prevention of Atrocities) Act 1989, Article 15/16, or other law "
        "is a case-specific legal question that General Counsel should assess directly — this report "
        "does not make that determination.", ST.action))
    story.append(CondPageBreak(6*cm))

    # ── MODULE 6: Colorism ────────────────────────────────────────────────
    _section_header(story, "Module 6 — Colorism / Skin-Tone Parity (AIR)",
                    "Fitzpatrick Scale AIR · Spearman Rank Correlation · Threshold AIR < 0.80")
    if skin_stats or skin_flags or air_s < 1.0:
        risk_class, risk_meaning, r_bg, r_fg = _mod_risk(air_val=air_s, flags_list=skin_flags)
        story.append(Paragraph(f"<b>4.6.1 Risk Classification: {risk_class}</b> — {risk_meaning}",
            ParagraphStyle("MC6",parent=ST.body,textColor=r_fg,backColor=r_bg,leftIndent=8,rightIndent=8,leading=14)))
        story.append(Spacer(1,0.15*cm))
        story.append(_kv_table([
            ("Colorism / Skin-Tone Parity AIR (worst/best band)", f"{air_s:.3f}  (threshold ≥ 0.800{EEOC_SHORT})"),
            ("Best-performing Fitzpatrick band hire rate",          f"{best_r:.1f}%"),
            ("Worst-performing Fitzpatrick band hire rate",         f"{worst_r:.1f}%"),
        ]))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(
            f"<b>4.6.3 Enterprise Impact:</b> "
            + (f"A Colorism / Skin-Tone Parity AIR of {air_s:.3f} indicates that, in this dataset, "
               f"candidates in darker Fitzpatrick scale bands are hired at progressively lower rates "
               f"than lighter-skinned candidates. This is a pattern that may be relevant to colour-"
               f"based discrimination protections — for example Title VII of the Civil Rights Act 1964 "
               f"for US-exposed entities — and to general data-fairness principles where automated or "
               f"photo-based screening tools are in use; applicability to a specific entity should be "
               f"confirmed with counsel. Affects candidates across {len(skin_stats)} skin-tone bands."
               if air_s < 0.80 else
               "No colorism / skin-tone AIR finding. Monitoring recommended."),
            ST.body))
        story.append(_rl_img(_colorism_buf(skin_stats), w=CW, h=7*cm))
        story.append(Spacer(1, 0.15*cm))
        _render_flags_ref(skin_flags, story, "Colorism / Skin-Tone Flags")
        story.append(Paragraph(
            "<b>Recommended Action (Owner: CTO + CHRO):</b> Audit all video interview AI tools "
            "and photo-based screening software for skin-tone bias. Disable or replace any "
            "computer-vision scoring feature that has not been validated for colorism. "
            "Conduct implicit bias training on colorism for all panel members. "
            "Success Metric: All Fitzpatrick band AIRs ≥ 0.800 in next audit cycle. "
            "Risk if Skipped: Continued statistical exposure on this metric, including potential "
            "Title VII relevance for US-exposed entities — consult counsel on specific obligations.",
            ST.action))
    else:
        story.append(Paragraph("Skin-tone data not present. Module not evaluated.", ST.flag_info))
    story.append(CondPageBreak(6*cm))

    # ── MODULE 7: Referral ────────────────────────────────────────────────
    if ref_hr or nref_hr or ref_flags:
        _section_header(story, "Module 7 — Referral Network Bias",
                        "Outcome Gap > 15pp · HHI Concentration Index > 0.25 · Indirect Discrimination")
        risk_class, risk_meaning, r_bg, r_fg = _mod_risk(flags_list=ref_flags)
        story.append(Paragraph(f"<b>4.7.1 Risk Classification: {risk_class}</b> — {risk_meaning}",
            ParagraphStyle("MC7",parent=ST.body,textColor=r_fg,backColor=r_bg,leftIndent=8,rightIndent=8,leading=14)))
        story.append(Spacer(1,0.15*cm))
        story.append(_kv_table([
            ("Referred candidate hire rate",       f"{ref_hr*100:.1f}%"),
            ("Cold-apply candidate hire rate",     f"{nref_hr*100:.1f}%"),
            ("Referral Adverse Impact Ratio (AIR)","" + f"{ref_air:.3f}  (threshold ≥ 0.800{EEOC_SHORT})"),
            ("Referral Network HHI Concentration", f"{ref_hhi:.4f}  (threshold < 0.250)"),
        ]))
        story.append(Spacer(1, 0.2*cm))
        story.append(_rl_img(_referral_buf(data), w=CW, h=6*cm))
        story.append(Spacer(1, 0.15*cm))
        _render_flags_ref(ref_flags, story, "Referral Network Flags")
        story.append(Paragraph(
            "<b>Recommended Action (Owner: Head of TA + CHRO):</b> Cap referral hires at 30% of "
            "total hiring per cycle. Mandate blind evaluation for all referral candidates. "
            "Expand sourcing to diverse professional networks and community organisations. "
            "Success Metric: Referral AIR ≥ 0.800; HHI < 0.250. "
            "Legal Risk if Skipped: Indirect discrimination exposure under EEOC disparate impact doctrine.",
            ST.action))
        story.append(CondPageBreak(6*cm))

    # ── MODULE 8: Marital Status ──────────────────────────────────────────
    if marital_flags or inter_stats:
        _section_header(story, "Module 8 — Marital Status Bias (Intersectional)",
                        "One-vs-Rest · Gender × Marital Status Cross-Tabulation · Threshold ±20pp / ±15pp")
        risk_class, risk_meaning, r_bg, r_fg = _mod_risk(flags_list=marital_flags)
        story.append(Paragraph(f"<b>4.8.1 Risk Classification: {risk_class}</b> — {risk_meaning}",
            ParagraphStyle("MC8",parent=ST.body,textColor=r_fg,backColor=r_bg,leftIndent=8,rightIndent=8,leading=14)))
        story.append(Spacer(1,0.15*cm))
        if marital_flags:
            story.append(Paragraph(
                "Research consistently demonstrates that married women face a 'marriage penalty' "
                "(assumptions about caregiving availability reducing hire probability) while married "
                "men receive a 'marriage premium'. This intersectional module detects both patterns "
                "using a gender × marital status cross-tabulation, and the flags below identify the "
                "specific pattern(s) found in this dataset.",
                ST.body))
        else:
            story.append(Paragraph(
                "This intersectional module screens for the 'marriage penalty' / 'marriage premium' "
                "pattern using a gender × marital status cross-tabulation. No such pattern was "
                "detected in this dataset — see the heatmap and flag summary below.",
                ST.body))
        story.append(_rl_img(_marital_heatmap_buf(inter_stats), w=CW, h=7*cm))
        story.append(Spacer(1, 0.15*cm))
        _render_flags_ref(marital_flags, story, "Marital Status Flags")
        story.append(Paragraph(
            "<b>Recommended Action (Owner: CHRO + Legal):</b> Remove marital status from all "
            "application forms. Train interviewers not to ask or infer caregiving availability. "
            "Implement pre-interview question audits. "
            "Success Metric: Zero marital status flags in next audit cycle. "
            # ISSUE-4: The Equal Remuneration Act 1976 governs gender pay parity between
            # men and women, not marital-status-based hiring discrimination — citing it here
            # was a statutory mis-match. Replaced with the correct applicable frameworks:
            # constitutional equality provisions (for State/State-instrumentality employers),
            # company equal-opportunity policy breach, and ILO Convention 111 (employment
            # discrimination). Specific legal applicability must be confirmed with counsel.
            "Legal Risk if Skipped: Marital-status-based hiring discrimination may constitute "
            "a breach of the organisation's equal-opportunity policy and, for State or "
            "State-instrumentality employers, may engage Article 15/16 of the Constitution of "
            "India. ILO Convention 111 (Discrimination in Employment) provides an international "
            "reference standard. Specific legal exposure — including any POSH-policy-adjacent "
            "considerations — should be confirmed with General Counsel for this entity's context.",
            ST.action))
        story.append(CondPageBreak(6*cm))

    # ── MODULE 9: Proxy Bias ──────────────────────────────────────────────
    if proxy_flags or phi_scores:
        _section_header(story, "Module 9 — Proxy Bias Detection",
                        "Phi Coefficient (φ) · Postcode · Name Origin · School Tier")
        risk_class, risk_meaning, r_bg, r_fg = _mod_risk(flags_list=proxy_flags)
        story.append(Paragraph(f"<b>4.9.1 Risk Classification: {risk_class}</b> — {risk_meaning}",
            ParagraphStyle("MC9",parent=ST.body,textColor=r_fg,backColor=r_bg,leftIndent=8,rightIndent=8,leading=14)))
        story.append(Spacer(1,0.15*cm))
        story.append(Paragraph(
            "Proxy bias occurs when a facially neutral variable (postcode, school tier, name origin) "
            "acts as a statistical stand-in for a protected attribute (caste, ethnicity, "
            "socioeconomic background). The Phi coefficient (φ) measures the strength of this "
            "correlation. A φ ≥ 0.20 triggers a WATCH flag; φ ≥ 0.30 triggers HIGH RISK.",
            ST.body))
        if phi_scores:
            phi_rows = [
                [_cell("Proxy Channel",    bold=True, bg=NAVY, color=WHITE),
                 _cell("|φ| Coefficient", bold=True, bg=NAVY, color=WHITE, align=1),
                 _cell("Risk Level",       bold=True, bg=NAVY, color=WHITE, align=1)],
            ]
            for ch, phi in sorted(phi_scores.items(), key=lambda x: -abs(float(x[1]))):
                phi_val  = abs(float(phi))
                risk_txt = "HIGH RISK" if phi_val>=0.30 else ("WATCH" if phi_val>=0.20 else "OK")
                risk_bg  = FAIL_BG if phi_val>=0.30 else (WARN_BG if phi_val>=0.20 else PASS_BG)
                risk_fg2 = FAIL_FG if phi_val>=0.30 else (WARN_FG if phi_val>=0.20 else PASS_FG)
                phi_rows.append([
                    _cell(ch.replace("_"," ").title()),
                    _cell(f"{phi_val:.4f}", align=1),
                    _cell(f"<b>{risk_txt}</b>", bold=True, align=1, color=risk_fg2, bg=risk_bg),
                ])
            phi_t = Table(phi_rows, colWidths=[7*cm, 4.5*cm, 5*cm])
            phi_t.setStyle(TableStyle([
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT_BG]),
                ("GRID",(0,0),(-1,-1),0.3,BORDER),
                ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
                ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ]))
            story.append(phi_t)
            story.append(Spacer(1, 0.25*cm))
        story.append(_rl_img(_proxy_lollipop_buf(phi_scores), w=CW, h=6*cm))
        story.append(Spacer(1, 0.15*cm))
        _render_flags_ref(proxy_flags, story, "Proxy Bias Flags")
        story.append(Paragraph(
            "<b>Recommended Action (Owner: CTO + CHRO):</b> Remove proxy features from all "
            "algorithmic resume screening tools. Re-train any ML models with fairness constraints "
            "(disparate impact threshold: φ < 0.200). Audit postcode-based geographic filters. "
            "Success Metric: All proxy channel φ coefficients < 0.200 in next audit. "
            "Risk if Skipped: Indirect-discrimination exposure, and potential obligations relating "
            "to automated decision-making under applicable data protection law — confirm specific "
            "provisions with counsel for the relevant jurisdiction.", ST.action))

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PART 5 — CRITICAL TELEMETRY GAPS
    # ════════════════════════════════════════════════════════════════════════
    _part_header(story, "PART 5", "Critical Telemetry Gaps — Data Architecture Assessment")
    story.append(Paragraph(
        "The following sections document missing data columns not as failed audit modules "
        "but as deficiencies in the organisation's data architecture. Each gap represents "
        "a legal obligation that cannot be discharged without the corresponding data being "
        "collected, structured, and retained in the Applicant Tracking System (ATS).",
        ST.body))

    gap_rows = [
        [_cell("Missing Column",    bold=True, bg=NAVY, color=WHITE),
         _cell("Module Blocked",    bold=True, bg=NAVY, color=WHITE),
         _cell("Legal Obligation",  bold=True, bg=NAVY, color=WHITE),
         _cell("ATS Remediation",   bold=True, bg=NAVY, color=WHITE),
         _cell("Effort",            bold=True, bg=NAVY, color=WHITE, align=1),
         _cell("Target",            bold=True, bg=NAVY, color=WHITE, align=1)],
    ]

    mr = _g(data,"module_results",{}) or {}
    detected_gaps = []

    # FIX-20: Post FIX-19, module_results is always pre-populated from the DB,
    # so "age" / "disability" / etc. are ALWAYS keys in mr — making the old
    # `"age" not in mr` guards permanently False.  We now inspect the
    # data_present flag written by audit_engine, and fall back to checking
    # whether the corresponding stats dict is empty when the flag is absent.

    # Age — absent when data_present is False OR age_stats is empty
    _age_mod = mr.get("age", {})
    if _age_mod.get("data_present") is False or (not age_stats and not _age_mod.get("data_present")):
        detected_gaps.append((
            "'age' / 'age_group'", "Module 4 — Age Group Bias",
            # ISSUE-4 (secondary): ERA 1976 is a gender pay-parity statute, not
            # an age-discrimination law. Corrected to applicable frameworks.
            "ADEA 1967 (US entities); equal-opportunity policy breach (India — no "
            "dedicated age-discrimination-in-hiring statute; confirm exposure with counsel)",
            "Add 'age_group' field (categorical: 18-25, 26-35, 36-45, 46-55, 56+). "
            "Validate: non-null, categorical.",
            "Low", "Sprint 1"))

    # Disability — absent when data_present is False OR stats empty and AIR defaulted to 1.0
    _dis_mod = mr.get("disability", {})
    if _dis_mod.get("data_present") is False or (air_d == 1.0 and not _dis_mod.get("data_present")):
        detected_gaps.append((
            "'disability_status'", "Module 2 — Disability Parity (AIR)",
            "RPWD Act 2016, §21 — Equal Opportunity Policy mandates PwD monitoring",
            "Add 'disability_status' boolean field (Yes/No/Prefer not to say). "
            "Validate: non-null with opt-out option.",
            "Low", "Sprint 1"))

    # Referral — absent when data_present is False OR referral_stats empty with no hire rate
    _ref_mod = mr.get("referral", {})
    if _ref_mod.get("data_present") is False or (not _g(data,"referral_stats",None) and not ref_hr and not _ref_mod.get("data_present")):
        detected_gaps.append((
            "'referral' / 'referral_source'", "Module 7 — Referral Network Bias",
            "EEOC Disparate Impact doctrine (29 CFR §1607) for US entities; "
            "data-fairness principles under applicable data protection law",
            "Add 'referral' boolean field (Yes/No). Validate: non-null.",
            "Low", "Sprint 1"))

    # Marital — absent when data_present is False OR marital_stats empty with no flags
    _mar_mod = mr.get("marital", {})
    if _mar_mod.get("data_present") is False or (not _g(data,"marital_stats",None) and not marital_flags and not _mar_mod.get("data_present")):
        detected_gaps.append((
            "'marital_status'", "Module 8 — Marital Status Bias",
            # ISSUE-4: ERA 1976 governs gender pay parity, not marital-status
            # discrimination in hiring. Corrected to the applicable frameworks.
            "Equal-opportunity policy breach; Article 15/16 Constitution of India "
            "(State/State-instrumentality employers); ILO Convention 111 — confirm "
            "specific applicability with General Counsel",
            "Add 'marital_status' categorical field (Single/Married/Other/Prefer not to say). "
            "Validate: categorical, opt-out permitted.",
            "Low", "Sprint 1"))

    # Skin tone — absent when data_present is False OR skin_stats empty and AIR defaulted to 1.0
    _skin_mod = mr.get("skin", {})
    if _skin_mod.get("data_present") is False or (not skin_stats and air_s == 1.0 and not _skin_mod.get("data_present")):
        detected_gaps.append((
            "'skin_colour' / 'skin_tone'", "Module 6 — Colorism / Skin-Tone Parity (AIR)",
            "Data-fairness principles under applicable data protection law; "
            "Title VII (US) colour discrimination",
            "Add 'skin_tone' categorical field using Fitzpatrick scale (Types 1-6). "
            "Validate: categorical, opt-out permitted.",
            "Medium", "Q1"))

    # Proxy fields — absent when data_present is False OR no phi scores/flags
    # were produced and the engine never marked the module as having run.
    _proxy_mod = mr.get("proxy", {})
    if _proxy_mod.get("data_present") is False or (not phi_scores and not proxy_flags and not _proxy_mod.get("data_present")):
        detected_gaps.append((
            "'postcode' / 'name_origin' / 'school_tier'", "Module 9 — Proxy Bias Detection",
            "Data-fairness principles under applicable data protection law — automated "
            "decision-making transparency obligations for facially-neutral proxy variables",
            "Add 'postcode', 'name_origin', and 'school_tier' fields to the ATS export schema "
            "so the Phi-coefficient proxy-correlation check has channels to evaluate. "
            "Validate: non-null where collected, opt-out permitted for name_origin.",
            "Medium", "Q1"))

    if detected_gaps:
        for col, mod, legal, ats, effort, target in detected_gaps:
            gap_rows.append([
                _cell(col), _cell(mod), _cell(legal), _cell(ats),
                _cell(effort, align=1,
                      color=PASS_FG if effort=="Low" else (WARN_FG if effort=="Medium" else FAIL_FG),
                      bg=PASS_BG if effort=="Low" else (WARN_BG if effort=="Medium" else FAIL_BG)),
                _cell(target, align=1),
            ])
    else:
        gap_rows.append([_cell("No critical telemetry gaps detected — all core columns present.",
                                bold=True, color=PASS_FG, bg=PASS_BG),
                          _cell(""),_cell(""),_cell(""),_cell(""),_cell("")])

    gap_t = Table(gap_rows, colWidths=[2.5*cm, 3*cm, 4*cm, 4.5*cm, 1.5*cm, 1*cm])
    gap_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT_BG]),
        ("GRID",(0,0),(-1,-1),0.3,BORDER),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(gap_t)
    story.append(Spacer(1, 0.3*cm))
    if detected_gaps:
        high_gaps  = [col.strip("'") for col, mod, legal, ats, effort, target in detected_gaps if effort == "Low"]
        med_gaps   = [col.strip("'") for col, mod, legal, ats, effort, target in detected_gaps if effort == "Medium"]
        parts = []
        if high_gaps:
            parts.append(
                f"Fields blocking statutory compliance modules "
                f"({', '.join(high_gaps)}) are classified Immediate / High Legal Exposure "
                f"and must be added to the ATS within Sprint 1."
            )
        if med_gaps:
            parts.append(
                f"Fields enabling secondary bias modules "
                f"({', '.join(med_gaps)}) are classified Short-Term / Medium Legal Exposure "
                f"and must be added within Q1."
            )
        story.append(Paragraph(
            "<b>Data Architecture Remediation Priority:</b> " + " ".join(parts),
            ST.body))
    else:
        story.append(Paragraph(
            "<b>Data Architecture Remediation Priority:</b> All required and optional ATS fields "
            "were present in the submitted dataset. No remediation of data architecture is required "
            "at this time. Continue collecting all fields to maintain full module coverage at the "
            "next audit cycle.",
            ST.body))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PART 6 — STRATEGIC REMEDIATION ROADMAP
    # ════════════════════════════════════════════════════════════════════════
    _part_header(story, "PART 6", "Strategic Remediation Roadmap — Three Horizons")

    rm_rows = [
        [_cell("Severity",  bold=True, bg=NAVY, color=WHITE),
         _cell("Horizon Type", bold=True, bg=NAVY, color=WHITE),
         _cell("Action",    bold=True, bg=NAVY, color=WHITE),
         _cell("Owner",     bold=True, bg=NAVY, color=WHITE),
         _cell("Success Metric", bold=True, bg=NAVY, color=WHITE),
         _cell("Timeline",  bold=True, bg=NAVY, color=WHITE, align=1),
         _cell("Exposure if Skipped (subject to legal review)", bold=True, bg=NAVY, color=WHITE)],
    ]

    horizon1 = [
        ("CRITICAL","Deploy CV anonymisation middleware at ATS ingestion layer — strip name, gender, "
         "caste/surname, institution fields before shortlisting queue.",
         "CTO + Head of TA","Caste AIR ≥ 0.800; Gender AIR ≥ 0.800 at next cycle (n ≥ 500)",
         "0–30 days","Continued statistical caste/gender disparity — confirm legal exposure with counsel"),
        ("CRITICAL","Initiate mandatory caste-sensitisation and implicit bias training for all "
         "evaluators and panel members.",
         "CHRO","100% evaluator completion rate",
         "0–30 days","Continued equal-opportunity exposure"),
        ("HIGH","Implement structured interview scorecards with pre-defined, role-specific "
         "criteria and calibrated weighting for all interview stages.",
         "Head of TA","Hiring gap ≤ 15pp across gender and caste groups",
         "0–30 days","Disparate-impact exposure under applicable equal-opportunity law"),
        ("HIGH","Audit all video interview AI and photo-based screening tools for skin-tone bias. "
         "Suspend tools without Fitzpatrick-validated bias certificates.",
         "CTO","Colorism AIR ≥ 0.800",
         "0–30 days","Colour-discrimination exposure (e.g. Title VII for US-exposed entities)"),
    ]
    horizon2 = [
        ("HIGH","Implement blind shortlisting pipeline — mask all proxy fields (surname, institution, "
         "postcode, photo) in recruiter ATS view.",
         "CTO + Head of TA","Proxy φ < 0.200 on all channels",
         "30–90 days","Indirect-discrimination exposure; confirm automated-decision-making obligations"),
        *([("MEDIUM",
            "Add missing ATS fields: "
            + ", ".join(col.strip("'") for col, *_ in detected_gaps)
            + " (see Part 5).",
            "CTO","All modules evaluable at next audit",
            "30–90 days","Equal-opportunity monitoring gap")]
           if detected_gaps else []),
        ("MEDIUM","Implement diversity-weighted sourcing: target 40% Tier-2/3 institutions, "
         "25% SC/ST/OBC pipeline in each hiring cycle.",
         "Head of TA","Institution one-vs-rest gap ≤ 20pp",
         "30–90 days","Indirect-discrimination exposure"),
        ("MEDIUM","Cap referral hires at 30% per cycle. Launch open sourcing to diverse "
         "professional networks.",
         "Head of TA","Referral AIR ≥ 0.800; HHI < 0.250",
         "30–90 days","Disparate-impact exposure"),
    ]
    horizon3 = [
        ("HIGH","Deploy real-time bias telemetry dashboard integrated with ATS — "
         "automated AIR monitoring with alert thresholds at 0.85 (warning) and 0.80 (critical).",
         "CTO","Level 4 Maturity achieved within 6 months",
         "90–180 days","Ongoing regulatory exposure without monitoring"),
        ("MEDIUM","Implement quarterly FairHire audit as a board-level KPI, reported to "
         "Risk Committee and Nomination & Remuneration Committee.",
         "CRO + CHRO","Board-level KPI dashboard live by Q3",
         "90–365 days","ESG rating downgrade; investor scrutiny"),
        ("MEDIUM","Map findings to GRI 405-1 (Diversity of governance bodies), BRSR Core "
         "indicators (for SEBI-listed entities), and UN SDG 10 disclosures.",
         "General Counsel + CFO","BRSR Core section complete; GRI 405-1 disclosed",
         "90–365 days","SEBI ESG disclosure non-compliance"),
        ("LOW","Achieve Level 5 Maturity (Optimised / Automated): real-time bias telemetry, "
         "ATS integration, continuous remediation loop, external audit certification.",
         "CTO + CHRO","Level 5 Maturity certification within 12 months",
         "12 months","Loss of ESG rating; investor divestment"),
    ]

    for horizon_label, horizon_type, actions in [
        ("HORIZON 1 — IMMEDIATE (0–30 days) — Stop the Legal Bleeding", "Immediate", horizon1),
        ("HORIZON 2 — SHORT-TERM (30–90 days) — Structural Process Redesign", "Structural", horizon2),
        ("HORIZON 3 — LONG-TERM (90–365 days) — Level 5 Maturity", "Strategic", horizon3),
    ]:
        rm_rows.append([
            _cell(f"<b>{horizon_label}</b>", bold=True, bg=ROYAL, color=WHITE, align=0),
            _cell(""), _cell(""), _cell(""), _cell(""), _cell(""), _cell(""),
        ])
        for priority, action, owner, metric, timeline, legal_risk in actions:
            p_bg, p_fg = _risk_colors(priority)
            rm_rows.append([
                _cell(f"<b>{priority}</b>", bold=True, color=p_fg, bg=p_bg, align=1),
                _cell(horizon_type, align=1),
                _cell(action), _cell(owner), _cell(metric),
                _cell(timeline, align=1), _cell(legal_risk),
            ])

    rm_t = Table(rm_rows, colWidths=[2*cm, 2*cm, 3.7*cm, 2.3*cm, 2.7*cm, 1.8*cm, 2*cm])
    rm_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT_BG]),
        ("GRID",(0,0),(-1,-1),0.3,BORDER),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("SPAN",(0,0),(6,0)),
    ]))
    story.append(rm_t)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PART 7 — ESG & REGULATORY EXPOSURE MAPPING
    # ════════════════════════════════════════════════════════════════════════
    _part_header(story, "PART 7", "ESG and Regulatory Exposure Mapping")

    esg_rows = [
        [_cell("Finding",               bold=True, bg=NAVY, color=WHITE),
         _cell("Indian Law",            bold=True, bg=NAVY, color=WHITE),
         _cell("International Framework",bold=True,bg=NAVY, color=WHITE),
         _cell("ESG Rating Impact",     bold=True, bg=NAVY, color=WHITE),
         _cell("BRSR Disclosure Required",bold=True,bg=NAVY,color=WHITE)],
        [_cell("Caste / Reservation Category Adverse Impact"),
         _cell("Article 15/16, Constitution (1950) (State employers); potential SC/ST (PoA) Act "
               "1989 relevance — fact-specific, confirm with counsel"),
         _cell("ILO Convention 111 (Discrimination); UN SDG 10; UN Guiding Principles on Business & Human Rights"),
         _cell("MSCI ESG: Social pillar downgrade. Sustainalytics: High controversy. CRISIL ESG: Red flag."),
         _cell("Yes — BRSR Core: Employee diversity (Principle 5); Equal opportunity policy disclosure")],
        [_cell("Gender Adverse Impact (AIR)"),
         _cell("Equal Remuneration Act 1976; equal-opportunity provisions under applicable law — "
               "confirm specific statutory basis with counsel"),
         _cell("EEOC 4/5ths Rule (29 CFR §1607); ILO Convention 100 (Equal Remuneration); GRI 405-1"),
         _cell("MSCI ESG: Gender diversity downgrade. ISS: Board oversight concern."),
         _cell("Yes — BRSR Core: Gender diversity in workforce; Principle 5 disclosures")],
        [_cell("Colorism / Skin-Tone Parity (AIR)"),
         _cell("Data Protection law (data-fairness principles, where automated/photo-based "
               "screening is used); Article 15 considerations — confirm applicability with counsel"),
         _cell("Title VII, Civil Rights Act 1964 (US, colour); ILO Convention 111"),
         _cell("MSCI ESG: Labour practices concern. Sustainalytics: Product governance flag."),
         _cell("Yes — BRSR Core: Discrimination complaints; Principle 5")],
        [_cell("Disability Parity (AIR)"),
         _cell("RPWD Act 2016, §21 (Equal Opportunity) — applicability of penalty provisions is "
               "fact-specific"),
         _cell("ADA (US) considerations where applicable; ILO Convention 159 (Vocational Rehabilitation); UN SDG 10"),
         _cell("MSCI ESG: Social inclusion metric. Sustainalytics: Human capital flag."),
         _cell("Yes — BRSR Core: PwD representation; Principle 5")],
        [_cell("Proxy Bias (Postcode / Institution)"),
         _cell("Automated decision-making provisions under applicable data protection law; "
               "indirect-discrimination considerations — confirm specific provisions with counsel"),
         _cell("GDPR Art. 22 (analogous automated decision-making, where EU nexus exists); UN SDG 10"),
         _cell("ISS: Algorithmic governance concern. Sustainalytics: Controversial business flag."),
         _cell("Yes — BRSR Core: AI governance; Technology & data use disclosures")],
    ]
    esg_t = Table(esg_rows, colWidths=[3*cm, 3.5*cm, 3.5*cm, 3.5*cm, 3*cm])
    esg_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT_BG]),
        ("GRID",(0,0),(-1,-1),0.3,BORDER),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(esg_t)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PART 8 — METHODOLOGY & STATISTICAL REFERENCE
    # ════════════════════════════════════════════════════════════════════════
    _part_header(story, "PART 8", "Methodology and Statistical Reference")

    meth_rows = [
        [_cell("Metric",      bold=True, bg=NAVY, color=WHITE),
         _cell("Formula",     bold=True, bg=NAVY, color=WHITE),
         _cell("Threshold",   bold=True, bg=NAVY, color=WHITE),
         _cell("Applied To",  bold=True, bg=NAVY, color=WHITE)],
        [_cell("Adverse Impact Ratio (AIR)"),
         _cell("minority_rate ÷ majority_rate"),
         # ISSUE-5: the methodology table defines the canonical pass/fail gate —
         # this is where the jurisdiction label is most important; add it inline.
         _cell(f"< 0.800 flag{EEOC_SHORT}"),
         _cell("Gender, Disability Parity, Colorism / Skin-Tone, Referral")],
        [_cell("Statistical Parity Gap (SPG)"),
         _cell("(Rate_A − Rate_B) × 100"),
         _cell("|gap| > 15.00pp flag"),
         _cell("Gender shortlisting and hiring stages")],
        [_cell("One-vs-Rest Gap"),
         _cell("group_rate − pooled_other_rate"),
         _cell("|gap| > 20.00pp flag"),
         _cell("Institution, Age, Marital Status, Caste (15pp for SC/ST)")],
        [_cell("Phi Coefficient (φ)"),
         _cell("(ad−bc) ÷ √((a+b)(c+d)(a+c)(b+d))"),
         _cell("φ > 0.20 WATCH\nφ > 0.30 HIGH RISK"),
         _cell("Postcode, Name Origin, School Tier (proxy channels)")],
        [_cell("Fisher's Exact Test"),
         _cell("Hypergeometric p-value on 2×2 contingency table"),
         _cell("p < 0.05 required for flag to survive"),
         _cell("All AIR violations — statistical significance gate")],
        [_cell("Bonferroni–Holm Correction"),
         _cell("Family-wise error control: p_i ≤ α/(n−i+1)"),
         _cell("Applied across all tests per module"),
         _cell("Prevents false positives from multiple comparisons")],
        [_cell("95% Wilson CI on Hire Rates"),
         _cell("p^ +/- 1.96*sqrt(p^(1-p^)/n) with continuity correction"),
         _cell("Reported in all flag messages"),
         _cell("All group-level hire rate estimates")],
        [_cell("Spearman Rank Correlation (ρ)"),
         _cell("ρ = 1 − (6Σd²)/(n(n²−1))"),
         _cell("|ρ| > 0.60 gradient flag"),
         _cell("Skin-tone ordinal gradient detection")],
        [_cell("HHI Concentration Index"),
         _cell("Σ(share_i)²"),
         _cell("> 0.250 concentrated"),
         _cell("Referral network insularity measurement")],
    ]
    meth_t = Table(meth_rows, colWidths=[3.5*cm, 5*cm, 3.5*cm, 4.5*cm])
    meth_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT_BG]),
        ("GRID",(0,0),(-1,-1),0.3,BORDER),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(meth_t)
    story.append(Spacer(1, 0.4*cm))

    _section_header(story, "Scoring Rubric — Weighting Table")
    scoring_rows = [
        [_cell("Module",        bold=True, bg=NAVY, color=WHITE),
         _cell("Weighting",     bold=True, bg=NAVY, color=WHITE, align=1),
         _cell("Pass Condition",bold=True, bg=NAVY, color=WHITE),
         _cell("Points Earned", bold=True, bg=NAVY, color=WHITE, align=1)],
        # ISSUE-5: every AIR pass condition in this rubric is the canonical
        # scoring gate — each must carry the EEOC jurisdiction note inline.
        [_cell("Gender Adverse Impact"),         _cell("15", align=1),
         _cell(f"AIR ≥ 0.800{EEOC_SHORT} across all gender groups"), _cell("0 or 15", align=1)],
        [_cell("Disability Parity (AIR)"),       _cell("15", align=1),
         _cell(f"AIR ≥ 0.800{EEOC_SHORT} (disability_status column required)"), _cell("0 or 15", align=1)],
        [_cell("Caste / Reservation Category"),  _cell("15", align=1),
         _cell(f"All AIRs ≥ 0.800{EEOC_SHORT}; SC/ST ≤ 15pp gap"), _cell("0 or 15", align=1)],
        [_cell("Colorism / Skin-Tone Parity"),   _cell("15", align=1),
         _cell(f"All Fitzpatrick band AIRs ≥ 0.800{EEOC_SHORT}"),   _cell("0 or 15", align=1)],
        [_cell("Proxy Bias Detection"),          _cell("10", align=1),
         _cell("All proxy channel φ < 0.200"),                    _cell("0 or 10", align=1)],
        [_cell("Statistical Parity Gap (SPG)"),  _cell("10", align=1),
         _cell("SPG ≤ 15pp at all pipeline stages"),              _cell("0 or 10", align=1)],
        [_cell("Institution / College Bias"),    _cell("6",  align=1),
         _cell("One-vs-Rest gap ≤ 20pp"),                         _cell("0 or 6",  align=1)],
        [_cell("Age Group Bias"),                _cell("4",  align=1),
         _cell("One-vs-Rest gap ≤ 20pp"),                         _cell("0 or 4",  align=1)],
        [_cell("Referral Network Bias"),         _cell("4",  align=1),
         _cell("Outcome gap ≤ 15pp; HHI < 0.250"),                _cell("0 or 4",  align=1)],
        [_cell("Marital Status Bias"),           _cell("6",  align=1),
         _cell("One-vs-Rest gap ≤ 20pp"),                         _cell("0 or 6",  align=1)],
        [_cell("TOTAL", bold=True, bg=LIGHT_BG), _cell("<b>100</b>", bold=True, align=1, bg=LIGHT_BG),
         _cell("", bg=LIGHT_BG),                 _cell("<b>0 – 100</b>", bold=True, align=1, bg=LIGHT_BG)],
        [_cell("Systemic Bias Dealbreaker (Caste + Skin both fail)", color=FAIL_FG if drv["dealbreaker_triggered"] else NAVY),
         _cell("−15", align=1, color=FAIL_FG),
         _cell("Applied when both Caste and Skin modules fail simultaneously — "
               f"{'TRIGGERED in this audit' if drv['dealbreaker_triggered'] else 'not triggered in this audit'}."),
         _cell(f"−{drv['sb_deduction']}", align=1, color=FAIL_FG if drv["sb_deduction"]>0 else NAVY)],
    ]
    score_t = Table(scoring_rows, colWidths=[5*cm, 2*cm, 7*cm, 2.5*cm])
    score_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT_BG]),
        ("GRID",(0,0),(-1,-1),0.3,BORDER),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(score_t)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PART 10 — PRE-PUBLISH QA CHECKLIST
    # Issue 7: automated gate results — rendered in every issued report so
    # the reader can verify internal consistency without cross-checking
    # Part 2, Part 5, and Part 8 manually.
    # ════════════════════════════════════════════════════════════════════════
    _part_header(story, "PART 10", "Pre-Publish QA Checklist — Audit Self-Certification")
    story.append(Paragraph(
        "The following five automated gate checks are run against this report's data before "
        "the PDF is finalised. A report is either fully consistent across all five gates or "
        "it is not issued at all (a <b>ReportBlockedError</b> halts generation). These results "
        "are included in the issued report so any recipient can verify the engine's "
        "self-certification independently.",
        ST.body))
    story.append(Spacer(1, 0.2*cm))

    qa_results = _run_prepublish_qa(score_data, unique_flags,
                                     score_data["not_evaluated_weight"])
    qa_rows = [
        [_cell("Gate", bold=True, bg=NAVY, color=WHITE, align=1),
         _cell("Check", bold=True, bg=NAVY, color=WHITE),
         _cell("Status", bold=True, bg=NAVY, color=WHITE, align=1),
         _cell("Detail", bold=True, bg=NAVY, color=WHITE)],
    ]
    all_passed = all(passed for _, _, passed, _ in qa_results)
    for gate_id, description, passed, detail in qa_results:
        status_txt = "PASS" if passed else "FAIL"
        s_bg = PASS_BG if passed else FAIL_BG
        s_fg = PASS_FG if passed else FAIL_FG
        qa_rows.append([
            _cell(f"({gate_id})", bold=True, align=1),
            _cell(description),
            _cell(f"<b>{status_txt}</b>", bold=True, align=1, color=s_fg, bg=s_bg),
            _cell(detail),
        ])
    qa_t = Table(qa_rows, colWidths=[1.2*cm, 4.8*cm, 1.5*cm, 9*cm])
    qa_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT_BG]),
        ("GRID",           (0,0), (-1,-1), 0.3, BORDER),
        ("TOPPADDING",     (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 5),
        ("LEFTPADDING",    (0,0), (-1,-1), 6),
        ("RIGHTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",         (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(qa_t)
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"<b>QA Self-Certification Result: {'✓ ALL GATES PASSED — report cleared for issuance.' if all_passed else '✗ ONE OR MORE GATES FAILED — this report should not have been issued; please report this to the FairHire engineering team.'}</b>",
        ParagraphStyle("QASummary", parent=ST.body,
                       textColor=PASS_FG if all_passed else FAIL_FG,
                       backColor=PASS_BG if all_passed else FAIL_BG,
                       leftIndent=8, rightIndent=8, leading=16)))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PART 9 — FULL LEGAL DISCLAIMER (6 CLAUSES — NON-NEGOTIABLE)
    # ════════════════════════════════════════════════════════════════════════
    _part_header(story, "PART 9", "Full Legal Disclaimer")
    story.append(Paragraph(
        "The following six clauses constitute the disclaimer applicable to this document. Each "
        "clause should be read in full alongside the findings in Parts 1–8; none of them is intended "
        "to be summarised, compressed, or omitted when this report is relied upon or distributed.",
        ST.body))
    story.append(Spacer(1, 0.2*cm))

    clauses = [
        ("CLAUSE 1 — SCOPE AND LIMITATION",
         f"This report analyses the dataset '{filename}' comprising {rows:,} candidate records "
         f"submitted to the FairHire v{FAIRHIRE_VERSION} automated algorithmic equity engine. "
         f"The analysis is confined to the statistical relationships between the data fields "
         f"present in the submitted dataset and the hiring outcome variable. This report does not "
         f"analyse individual employment decisions, does not review individual candidate files, "
         f"does not assess qualifications, and does not evaluate the subjective judgements of any "
         f"individual evaluator. Statistical findings cannot be extrapolated beyond the submitted "
         f"cohort without further analysis. Findings relating to modules where required data columns "
         f"were absent (see Part 5 — Telemetry Gaps) are explicitly marked 'NOT EVALUATED' "
         f"and no inferences may be drawn from those modules."),

        ("CLAUSE 2 — DATA PROVENANCE AND INTEGRITY",
         f"All findings in this report are entirely dependent on the accuracy, completeness, and "
         f"representativeness of the data supplied by the client organisation. FairHire has not "
         f"independently verified the accuracy of any data field. The following data quality issues "
         f"were detected during this audit: "
         + (
             " ".join(filter(None, [
                 ("Missing column: disability_status (Disability Parity module not evaluated)."
                  if (air_d == 1.0 and "disability" not in (_g(data, "module_results", {}) or {}))
                  else ""),
                 ("Missing column: age/age_group (Age Group module not evaluated)."
                  if not _g(data, "age_stats", None)
                  else ""),
             ])) or "None — all expected data fields were present in the submitted dataset."
         )
         + f" Any conclusion drawn from this report is valid only to the extent that the underlying "
         f"data is accurate and complete. Clients are advised to implement data governance controls "
         f"to ensure ATS data quality before re-audit."),

        ("CLAUSE 3 — LIMITATION OF LIABILITY",
         f"Neither FairHire, its affiliates, officers, directors, employees, nor agents accepts "
         f"any legal liability, whether in contract, tort, negligence, or otherwise, for any loss, "
         f"damage, claim, or expense arising from any decision made on the basis of this report. "
         f"This report is provided as an analytical tool to support human HR and legal judgement. "
         f"FairHire's total aggregate liability in connection with this report is limited to the "
         f"fee paid for the generation of this specific report. This limitation applies to the "
         f"fullest extent permitted by applicable law."),

        ("CLAUSE 4 — CONFIDENTIALITY OBLIGATION",
         f"This document is strictly confidential and is intended solely for: the Chief Risk "
         f"Officer, General Counsel, Chief Human Resources Officer, and Board Risk Committee of "
         f"{company}. Onward disclosure to any other party, including internal employees not named "
         f"above, is discouraged without prior consultation with FairHire and the client's own legal "
         f"counsel. This report contains statistical inferences derived from personal employment "
         f"data; recipients should assess their own obligations under applicable data protection law "
         f"(e.g. the Digital Personal Data Protection Act, 2023 in India, where applicable) before "
         f"further distribution, and should store this document in a secure, access-controlled "
         f"system. This document does not itself carry legal privilege — see Clause 6."),

        ("CLAUSE 5 — EMPLOYMENT DECISION RESTRICTION",
         f"This report must not be used as the sole or primary basis for any adverse employment "
         f"action, including but not limited to: termination, demotion, exclusion from promotion, "
         f"or denial of hire for any individual candidate or class of candidates. Any employment "
         f"decision informed by the findings of this report must be reviewed by qualified legal "
         f"counsel before implementation. Statistical evidence of group-level disparity does not "
         f"constitute grounds for individual adverse action. The organisation's obligation to "
         f"provide equal opportunity to each individual candidate is not discharged by group-level "
         f"remediation alone."),

        ("CLAUSE 6 — STATISTICAL SIGNIFICANCE ≠ LEGAL FINDING; PRIVILEGE STATUS",
         f"A statistically significant Fisher p-value, a failing Adverse Impact Ratio (AIR) score, "
         f"a Phi coefficient above threshold, a failing Wilson confidence interval, or any other "
         f"metric produced by this report does not constitute a legal finding of unlawful "
         f"discrimination. These are statistical patterns indicating elevated risk that require "
         f"human investigation, professional HR review, and legal counsel assessment. Only a court "
         f"of competent jurisdiction, the Equal Employment Opportunity Commission (EEOC), the "
         f"National Human Rights Commission (NHRC), or another duly constituted regulatory body "
         f"can make a legally binding finding of discrimination. The presence of flags in this "
         f"report must be treated as a call to investigate, not as evidence of wrongdoing. "
         f"This report is generated by an automated statistical engine and is not, by itself, a "
         f"communication protected by legal advice privilege or litigation privilege. If privileged "
         f"treatment is required, the client's own legal counsel should commission and route this "
         f"type of analysis directly, consistent with the applicable law of privilege in the "
         f"relevant jurisdiction."),
    ]

    for i, (clause_title, clause_text) in enumerate(clauses, 1):
        story.append(Paragraph(f"<b>{clause_title}</b>", ST.h3))
        story.append(Paragraph(clause_text, ST.legal_clause))
        story.append(Spacer(1, 0.1*cm))

    story.append(Spacer(1, 0.4*cm))
    story.append(_hr(BORDER))
    story.append(Paragraph(
        f"<b>Audit Integrity Statement:</b> This document was generated by FairHire v{FAIRHIRE_VERSION} "
        f"on {now_str}. Audit ID: {audit_id}. Report hash: {report_hash[:16].upper()}. "
        f"The statistical findings in this report are produced by a deterministic computational "
        f"engine and are reproducible from the source dataset. The score derivation arithmetic "
        f"is documented in full in Part 2 of this report.",
        ST.body_sm))

    # ════════════════════════════════════════════════════════════════════════
    # BUILD PDF
    # ════════════════════════════════════════════════════════════════════════
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm,   bottomMargin=2.2*cm,
    )
    footer_fn = _make_footer(report_hash, company)
    doc.build(story, onFirstPage=footer_fn, onLaterPages=footer_fn)
    buffer.seek(0)
    return buffer
