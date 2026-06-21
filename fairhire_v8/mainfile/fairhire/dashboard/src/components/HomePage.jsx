import React, { useState, useEffect, useRef } from 'react'

/* ==========================================================================
   FAIRHIRE HOME — Editorial audit-report aesthetic
   Fraunces (serif display) + Inter (UI) + JetBrains Mono (data/schema)
   Signature element: live fairness Scorecard in the hero — a miniature
   preview of the actual audit output, not a generic illustration.
   ========================================================================== */
const AUDIT_OVERRIDE_ID = 'fairhire-light-minimal-theme'
const AUDIT_TEMPLATE_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

  /* ══════════════════════════════════════════════════════════════════
     TOKENS
     ══════════════════════════════════════════════════════════════════ */
  .hp-wrapper {
    --ink:        #0B1220;
    --paper:      #F7F9FC;
    --paper-2:    #FFFFFF;
    --forest:     #2F6F4E;
    --forest-d:   #20503A;
    --forest-l:   #E8F2EC;
    --clay:       #C2542F;
    --clay-l:     #FBEAE2;
    --slate:      #5B6472;
    --slate-l:    #8A93A3;
    --line:       #E3E8F0;
    --line-soft:  #ECEFF4;

    font-family: 'Inter', sans-serif;
    color: var(--ink);
    min-height: 100vh;
    overflow-x: hidden;
    position: relative;
    -webkit-font-smoothing: antialiased;
    background: var(--paper);
  }

  .hp-wrapper *, .hp-wrapper *::before, .hp-wrapper *::after {
    box-sizing: border-box;
  }

  .hp-serif {
    font-family: 'Fraunces', serif;
  }

  .hp-mono {
    font-family: 'JetBrains Mono', monospace;
  }

  .hp-wrapper a { text-decoration: none; color: inherit; }
  .hp-wrapper button { font-family: inherit; }
  .hp-wrapper ul { list-style: none; }

  /* focus visibility */
  .hp-wrapper button:focus-visible,
  .hp-wrapper a:focus-visible,
  .hp-wrapper input:focus-visible {
    outline: 2px solid var(--forest);
    outline-offset: 2px;
  }

  @media (prefers-reduced-motion: reduce) {
    .hp-wrapper * { animation-duration: 0.001ms !important; transition-duration: 0.001ms !important; }
  }

  /* ══════════════════════════════════════════════════════════════════
     NAVBAR
     ══════════════════════════════════════════════════════════════════ */
  .hp-nav {
    position: sticky;
    top: 0;
    z-index: 50;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 48px;
    background: rgba(247, 249, 252, 0.85);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--line);
  }

  .hp-nav-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 1.25rem;
    color: var(--ink);
    letter-spacing: -0.01em;
  }

  .hp-nav-mark {
    width: 32px;
    height: 32px;
    border-radius: 9px;
    background: var(--ink);
    color: var(--paper);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    flex-shrink: 0;
  }

  .hp-nav-links {
    display: flex;
    align-items: center;
    gap: 36px;
  }

  .hp-nav-link {
    font-size: 0.92rem;
    font-weight: 500;
    color: var(--slate);
    cursor: pointer;
    position: relative;
    padding: 4px 0;
  }

  .hp-nav-link:hover { color: var(--ink); }

  .hp-nav-actions {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .hp-nav-login {
    font-size: 0.92rem;
    font-weight: 600;
    color: var(--ink);
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px 4px;
  }

  .hp-nav-cta {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--paper);
    background: var(--ink);
    border: none;
    padding: 10px 20px;
    border-radius: 100px;
    cursor: pointer;
    white-space: nowrap;
  }

  .hp-nav-cta:hover { background: var(--forest-d); }

  .hp-nav-burger {
    display: none;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--ink);
    font-size: 1.4rem;
  }

  /* ══════════════════════════════════════════════════════════════════
     HERO
     ══════════════════════════════════════════════════════════════════ */
  .hp-hero {
    position: relative;
    padding: 88px 48px 64px;
    display: grid;
    grid-template-columns: 1.05fr 0.95fr;
    gap: 56px;
    align-items: center;
    max-width: 1320px;
    margin: 0 auto;
  }

  .hp-hero-blob {
    position: absolute;
    top: -120px;
    right: -160px;
    width: 620px;
    height: 620px;
    border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, rgba(47,111,78,0.16), rgba(47,111,78,0) 70%);
    z-index: 0;
    pointer-events: none;
  }

  .hp-hero-bg-image {
    position: absolute;
    top: -60px;
    right: -120px;
    width: 760px;
    height: auto;
    max-width: none;
    opacity: 0.22;
    z-index: -1;
    pointer-events: none;
    -webkit-mask-image: radial-gradient(circle at 65% 35%, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.5) 55%, rgba(0,0,0,0) 80%);
    mask-image: radial-gradient(circle at 65% 35%, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.5) 55%, rgba(0,0,0,0) 80%);
  }

  .hp-hero-left {
    position: relative;
    z-index: 1;
  }

  .hp-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--paper-2);
    border: 1px solid var(--line);
    padding: 7px 14px 7px 8px;
    border-radius: 100px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--slate);
    letter-spacing: 0.01em;
    margin-bottom: 28px;
  }

  .hp-eyebrow-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--forest);
    flex-shrink: 0;
    position: relative;
  }

  .hp-eyebrow-dot::after {
    content: '';
    position: absolute;
    inset: -3px;
    border-radius: 50%;
    border: 1px solid var(--forest);
    opacity: 0.5;
    animation: hp-pulse-ring 2.2s ease-out infinite;
  }

  @keyframes hp-pulse-ring {
    0% { transform: scale(0.8); opacity: 0.6; }
    100% { transform: scale(1.8); opacity: 0; }
  }

  .hp-hero h1 {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 3.6rem;
    line-height: 1.05;
    letter-spacing: -0.02em;
    margin: 0 0 22px 0;
    color: var(--ink);
    max-width: 560px;
  }

  .hp-hero h1 em {
    font-style: italic;
    color: var(--forest-d);
    font-weight: 500;
  }

  .hp-hero-desc {
    font-size: 1.08rem;
    line-height: 1.65;
    color: var(--slate);
    max-width: 480px;
    margin: 0 0 36px 0;
  }

  .hp-hero-actions {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 44px;
    flex-wrap: wrap;
  }

  .hp-btn-primary {
    font-size: 0.96rem;
    font-weight: 600;
    color: var(--paper);
    background: var(--ink);
    border: none;
    padding: 15px 26px;
    border-radius: 100px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
  }

  .hp-btn-primary:hover { background: var(--forest-d); }

  .hp-btn-secondary {
    font-size: 0.96rem;
    font-weight: 600;
    color: var(--ink);
    background: transparent;
    border: 1.5px solid var(--line);
    padding: 15px 24px;
    border-radius: 100px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }

  .hp-btn-secondary:hover { border-color: var(--ink); background: var(--paper-2); }

  .hp-hero-proof {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .hp-proof-avatars {
    display: flex;
  }

  .hp-proof-avatar {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    border: 2px solid var(--paper);
    margin-left: -10px;
    background: var(--line);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--slate);
  }

  .hp-proof-avatar:first-child { margin-left: 0; }

  .hp-proof-text {
    font-size: 0.85rem;
    color: var(--slate);
    line-height: 1.4;
  }

  .hp-proof-text strong { color: var(--ink); }
  /* ══════════════════════════════════════════════════════════════════
     HERO RIGHT — LIVE SCORECARD (signature element)
     ══════════════════════════════════════════════════════════════════ */
  .hp-hero-right {
    position: relative;
    z-index: 1;
    padding: 28px 28px 22px 8px;
  }

  .hp-scorecard {
    background: var(--paper-2);
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 28px;
    box-shadow: 0 24px 60px -20px rgba(11, 18, 32, 0.12);
    position: relative;
    margin: 26px 0 24px;
  }

  .hp-scorecard-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 22px;
  }

  .hp-scorecard-title {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--slate-l);
  }

  .hp-scorecard-live {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--forest-d);
    background: var(--forest-l);
    padding: 4px 10px;
    border-radius: 100px;
  }

  .hp-scorecard-live span.hp-live-dot {
    width: 6px; height: 6px; border-radius: 50%; background: var(--forest);
  }

  .hp-scorecard-body {
    display: flex;
    align-items: center;
    gap: 24px;
    padding-bottom: 22px;
    border-bottom: 1px dashed var(--line);
    margin-bottom: 20px;
  }

  .hp-score-ring {
    position: relative;
    width: 108px;
    height: 108px;
    flex-shrink: 0;
  }

  .hp-score-ring svg { transform: rotate(-90deg); }

  .hp-score-ring-track {
    fill: none;
    stroke: var(--line-soft);
    stroke-width: 10;
  }

  .hp-score-ring-fill {
    fill: none;
    stroke: var(--forest);
    stroke-width: 10;
    stroke-linecap: round;
    transition: stroke-dashoffset 1.1s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .hp-score-ring-num {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }

  .hp-score-ring-num strong {
    font-family: 'Fraunces', serif;
    font-size: 1.9rem;
    font-weight: 600;
    color: var(--ink);
    line-height: 1;
  }

  .hp-score-ring-num span {
    font-size: 0.65rem;
    color: var(--slate-l);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 2px;
  }

  .hp-score-summary h4 {
    font-family: 'Fraunces', serif;
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--ink);
    margin: 0 0 6px 0;
  }

  .hp-score-summary p {
    font-size: 0.86rem;
    color: var(--slate);
    line-height: 1.5;
    margin: 0;
  }

  .hp-scorecard-rows {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .hp-score-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 11px 14px;
    border-radius: 10px;
    background: var(--paper);
    border: 1px solid var(--line-soft);
  }

  .hp-score-row-label {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--ink);
    min-width: 0;
  }

  .hp-row-icon {
    width: 22px;
    height: 22px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.72rem;
    flex-shrink: 0;
  }

  .hp-row-icon.ok { background: var(--forest-l); color: var(--forest-d); }
  .hp-row-icon.flag { background: var(--clay-l); color: var(--clay); }

  .hp-score-row-status {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    flex-shrink: 0;
  }

  .hp-score-row-status.ok { color: var(--forest-d); }
  .hp-score-row-status.flag { color: var(--clay); }

  .hp-scorecard-foot {
    margin-top: 18px;
    font-size: 0.78rem;
    color: var(--slate-l);
    text-align: center;
  }

  .hp-scorecard-foot code {
    font-family: 'JetBrains Mono', monospace;
    background: var(--paper);
    border: 1px solid var(--line-soft);
    padding: 2px 6px;
    border-radius: 4px;
    color: var(--slate);
  }

  .hp-float-chip {
    position: absolute;
    background: var(--paper-2);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 10px 14px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--ink);
    box-shadow: 0 12px 30px -10px rgba(11,18,32,0.15);
    display: flex;
    align-items: center;
    gap: 8px;
    z-index: 2;
    white-space: nowrap;
  }

  .hp-float-chip.c1 { top: 0; left: -4px; }
  .hp-float-chip.c2 { bottom: 0; right: -4px; }
  /* ══════════════════════════════════════════════════════════════════
     SHARED SECTION HELPERS
     ══════════════════════════════════════════════════════════════════ */
  .hp-section {
    max-width: 1320px;
    margin: 0 auto;
    padding: 88px 48px;
  }

  .hp-section-tight { padding-top: 0; }

  .hp-kicker {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--forest-d);
    margin-bottom: 14px;
  }

  .hp-kicker::before {
    content: '';
    width: 16px;
    height: 1.5px;
    background: var(--forest);
  }

  .hp-section-head {
    max-width: 620px;
    margin-bottom: 52px;
  }

  .hp-section-head.center { margin-left: auto; margin-right: auto; text-align: center; }

  .hp-section-head h2 {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 2.4rem;
    line-height: 1.15;
    letter-spacing: -0.01em;
    color: var(--ink);
    margin: 0 0 14px 0;
  }

  .hp-section-head p {
    font-size: 1.02rem;
    line-height: 1.6;
    color: var(--slate);
    margin: 0;
  }

  /* ══════════════════════════════════════════════════════════════════
     LOGO / TRUST STRIP
     ══════════════════════════════════════════════════════════════════ */
  .hp-trust-strip {
    max-width: 1320px;
    margin: 0 auto;
    padding: 0 48px 64px;
    display: flex;
    align-items: center;
    gap: 32px;
  }

  .hp-trust-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--slate-l);
    white-space: nowrap;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .hp-trust-logos {
    display: flex;
    align-items: center;
    gap: 40px;
    flex-wrap: wrap;
    opacity: 0.6;
  }

  .hp-trust-logos span {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 1.05rem;
    color: var(--slate);
  }

  /* ══════════════════════════════════════════════════════════════════
     STATS BAND
     ══════════════════════════════════════════════════════════════════ */
  .hp-stats-band {
    background: var(--ink);
    border-radius: 28px;
    max-width: 1320px;
    margin: 0 auto 0;
    padding: 56px 48px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0;
    position: relative;
    overflow: hidden;
  }

  .hp-stats-glow {
    position: absolute;
    top: -100px;
    left: 50%;
    width: 500px;
    height: 300px;
    background: radial-gradient(circle, rgba(47,111,78,0.35), transparent 70%);
    transform: translateX(-50%);
    pointer-events: none;
  }

  .hp-stat-item {
    position: relative;
    z-index: 1;
    padding: 0 28px;
    border-right: 1px solid rgba(255,255,255,0.1);
  }

  .hp-stat-item:last-child { border-right: none; }

  .hp-stat-num {
    font-family: 'Fraunces', serif;
    font-size: 2.6rem;
    font-weight: 600;
    color: #ffffff;
    line-height: 1;
    margin-bottom: 10px;
    letter-spacing: -0.02em;
  }

  .hp-stat-num span {
    color: #7FBF9E;
  }

  .hp-stat-label {
    font-size: 0.88rem;
    color: rgba(255,255,255,0.6);
    line-height: 1.45;
  }
  /* ══════════════════════════════════════════════════════════════════
     FEATURE GRID
     ══════════════════════════════════════════════════════════════════ */
  .hp-features-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
  }

  .hp-feature-card {
    background: var(--paper-2);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 30px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    transition: transform 0.3s cubic-bezier(0.16,1,0.3,1), box-shadow 0.3s cubic-bezier(0.16,1,0.3,1), border-color 0.3s;
  }

  .hp-feature-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 44px -16px rgba(11,18,32,0.12);
    border-color: #D7DEE8;
  }

  .hp-feature-icon {
    width: 46px;
    height: 46px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    background: var(--forest-l);
    color: var(--forest-d);
  }

  .hp-feature-card h3 {
    font-family: 'Fraunces', serif;
    font-size: 1.18rem;
    font-weight: 600;
    color: var(--ink);
    margin: 0;
  }

  .hp-feature-card p {
    font-size: 0.92rem;
    line-height: 1.6;
    color: var(--slate);
    margin: 0;
  }

  /* ══════════════════════════════════════════════════════════════════
     RISK CONSOLE
     ══════════════════════════════════════════════════════════════════ */
  .hp-console {
    background: var(--paper-2);
    border: 1px solid var(--line);
    border-radius: 24px;
    padding: 48px;
  }

  .hp-console-grid {
    display: grid;
    grid-template-columns: 270px 1fr;
    gap: 36px;
    margin-top: 36px;
  }

  .hp-console-menu {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .hp-console-item {
    font-family: inherit;
    background: transparent;
    color: var(--slate);
    border: 1px solid transparent;
    padding: 13px 16px;
    border-radius: 10px;
    cursor: pointer;
    text-align: left;
    font-size: 0.92rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: space-between;
    text-transform: capitalize;
  }

  .hp-console-item:hover {
    color: var(--ink);
    background: var(--paper);
  }

  .hp-console-item.is-selected {
    background: var(--forest-l);
    color: var(--forest-d);
    border-color: rgba(47,111,78,0.25);
  }

  .hp-console-arrow {
    opacity: 0;
    transform: translateX(-4px);
    transition: opacity 0.2s, transform 0.2s;
  }

  .hp-console-item.is-selected .hp-console-arrow {
    opacity: 1;
    transform: translateX(0);
  }

  .hp-console-view {
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 32px;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  .hp-console-view-label {
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--slate-l);
    font-weight: 700;
    margin: 0 0 6px 0;
  }

  .hp-console-view-title {
    font-family: 'Fraunces', serif;
    font-size: 1.3rem;
    font-weight: 600;
    color: var(--ink);
    margin: 0 0 4px 0;
  }

  .hp-console-view-sub {
    font-size: 0.92rem;
    color: var(--forest-d);
    font-weight: 600;
    margin: 0;
  }

  .hp-console-rule-text {
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--slate);
    margin: 0;
  }

  .hp-alert-banner {
    background: var(--clay-l);
    border: 1px solid #F0CCB8;
    border-radius: 10px;
    padding: 14px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    color: #8A3A1F;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    line-height: 1.5;
  }

  .hp-token-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .hp-token {
    font-family: 'JetBrains Mono', monospace;
    background: var(--paper-2);
    border: 1px solid var(--line);
    color: var(--slate);
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 0.78rem;
  }

  /* ══════════════════════════════════════════════════════════════════
     SPEC SUMMARY STRIP
     ══════════════════════════════════════════════════════════════════ */
  .hp-spec-summary {
    display: flex;
    align-items: center;
    gap: 28px;
    margin-bottom: 28px;
    padding: 20px 28px;
    background: var(--forest-l);
    border: 1px solid #CDE3D6;
    border-radius: 16px;
  }

  .hp-spec-summary-stat {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }

  .hp-spec-summary-stat strong {
    font-family: 'Fraunces', serif;
    font-size: 1.7rem;
    font-weight: 600;
    color: var(--forest-d);
    line-height: 1;
  }

  .hp-spec-summary-stat span {
    font-size: 0.84rem;
    color: var(--ink);
    font-weight: 600;
  }

  .hp-spec-summary-divider {
    width: 1px;
    height: 28px;
    background: #CDE3D6;
  }

  /* ══════════════════════════════════════════════════════════════════
     SCHEMA TABLE
     ══════════════════════════════════════════════════════════════════ */
  .hp-table-frame {
    overflow-x: auto;
    border-radius: 18px;
    border: 1px solid var(--line);
    background: var(--paper-2);
    box-shadow: 0 1px 2px rgba(11,18,32,0.03);
  }

  .hp-schema-table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 0.9rem;
    min-width: 760px;
  }

  .hp-schema-table th {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    background: var(--paper);
    color: var(--slate-l);
    padding: 16px 20px;
    font-weight: 700;
    border-bottom: 1px solid var(--line);
  }

  .hp-schema-table th:first-child { padding-left: 24px; width: 44px; }

  .hp-schema-table td {
    padding: 18px 20px;
    border-bottom: 1px solid var(--line-soft);
    color: var(--ink);
    vertical-align: top;
    line-height: 1.5;
  }

  .hp-schema-table td:first-child { padding-left: 24px; }

  .hp-schema-table tr:last-child td { border-bottom: none; }
  .hp-schema-table tr:hover td { background: var(--paper); }

  .hp-schema-table td p { margin: 0; color: var(--slate); font-size: 0.88rem; }

  .hp-row-index {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 7px;
    background: var(--forest-l);
    color: var(--forest-d);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.74rem;
    font-weight: 700;
  }

  .hp-pill-required {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: var(--forest-l);
    color: var(--forest-d);
    border: 1px solid #CDE3D6;
    padding: 4px 10px 4px 8px;
    border-radius: 100px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    white-space: nowrap;
  }

  .hp-pill-required::before {
    content: '✓';
    font-size: 0.7rem;
  }

  .hp-code {
    font-family: 'JetBrains Mono', monospace;
    background: var(--paper);
    padding: 2px 6px;
    border-radius: 4px;
    color: var(--forest-d);
    font-size: 0.84rem;
    border: 1px solid var(--line-soft);
  }
  /* ══════════════════════════════════════════════════════════════════
     PRICING
     ══════════════════════════════════════════════════════════════════ */
  .hp-pricing-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
    align-items: stretch;
  }

  .hp-price-card {
    position: relative;
    border-radius: 22px;
    padding: 36px 32px;
    display: flex;
    flex-direction: column;
    background: var(--paper-2);
    border: 1.5px solid var(--line);
    transition: transform 0.3s cubic-bezier(0.16,1,0.3,1), box-shadow 0.3s cubic-bezier(0.16,1,0.3,1);
  }

  .hp-price-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 24px 50px -18px rgba(11,18,32,0.14);
  }

  .hp-price-card.featured {
    background: var(--ink);
    border-color: var(--ink);
    color: var(--paper);
  }

  .hp-price-card.featured .hp-plan-name,
  .hp-price-card.featured .hp-price-amount,
  .hp-price-card.featured .hp-price-currency { color: #ffffff; }

  .hp-price-card.featured .hp-plan-sub,
  .hp-price-card.featured .hp-price-unit,
  .hp-price-card.featured .hp-capacity-note { color: rgba(255,255,255,0.6); }

  .hp-price-card.featured .hp-price-divider { border-color: rgba(255,255,255,0.12); }
  .hp-price-card.featured .hp-feature-list li { color: rgba(255,255,255,0.82); }
  .hp-price-card.featured .hp-feat-tick { color: #7FBF9E; }

  .hp-plan-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.74rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--slate-l);
    margin-bottom: 16px;
  }

  .hp-price-card.featured .hp-plan-chip { color: #7FBF9E; }

  .hp-popular-tag {
    position: absolute;
    top: 24px;
    right: 24px;
    background: var(--forest);
    color: #ffffff;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 5px 11px;
    border-radius: 100px;
  }

  .hp-soon-tag {
    position: absolute;
    top: 24px;
    right: 24px;
    background: var(--paper);
    color: var(--slate);
    border: 1px solid var(--line);
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 5px 11px;
    border-radius: 100px;
  }

  .hp-plan-name {
    font-family: 'Fraunces', serif;
    font-size: 1.3rem;
    font-weight: 600;
    color: var(--ink);
    margin: 0 0 6px 0;
  }

  .hp-plan-sub {
    font-size: 0.88rem;
    color: var(--slate);
    line-height: 1.5;
    margin: 0 0 22px 0;
    min-height: 42px;
  }

  .hp-price-block {
    display: flex;
    align-items: flex-start;
    gap: 2px;
  }

  .hp-price-currency {
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--ink);
    margin-top: 6px;
  }

  .hp-price-amount {
    font-family: 'Fraunces', serif;
    font-size: 2.7rem;
    font-weight: 600;
    color: var(--ink);
    line-height: 1;
    letter-spacing: -0.02em;
  }

  .hp-price-unit {
    font-size: 0.84rem;
    color: var(--slate);
    margin: 4px 0 2px 0;
  }

  .hp-capacity-note {
    font-size: 0.8rem;
    color: var(--slate-l);
    margin: 0 0 22px 0;
  }

  .hp-price-divider {
    border-top: 1px solid var(--line);
    margin-bottom: 22px;
  }

  .hp-feature-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin: 0 0 28px 0;
    flex-grow: 1;
  }

  .hp-feature-list li {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    font-size: 0.88rem;
    color: var(--ink);
    line-height: 1.4;
  }

  .hp-feat-tick {
    color: var(--forest-d);
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .hp-price-cta {
    font-size: 0.94rem;
    font-weight: 600;
    color: var(--paper);
    background: var(--ink);
    border: none;
    padding: 14px 20px;
    border-radius: 100px;
    cursor: pointer;
    width: 100%;
    text-align: center;
  }

  .hp-price-cta:hover { background: var(--forest-d); }

  .hp-price-card.featured .hp-price-cta {
    background: var(--forest);
    color: #ffffff;
  }

  .hp-price-card.featured .hp-price-cta:hover { background: #3A8362; }

  .hp-price-cta:disabled {
    background: var(--line);
    color: var(--slate-l);
    cursor: not-allowed;
  }

  /* ══════════════════════════════════════════════════════════════════
     CLOSING CTA BAND
     ══════════════════════════════════════════════════════════════════ */
  .hp-cta-band {
    max-width: 1320px;
    margin: 0 auto;
    padding: 0 48px 96px;
  }

  .hp-cta-inner {
    background: linear-gradient(135deg, #14301F 0%, var(--ink) 60%);
    border-radius: 28px;
    padding: 72px 56px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }

  .hp-cta-inner::before {
    content: '';
    position: absolute;
    top: -80px;
    right: -80px;
    width: 360px;
    height: 360px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(127,191,158,0.35), transparent 70%);
  }

  .hp-cta-inner h2 {
    font-family: 'Fraunces', serif;
    font-size: 2.5rem;
    font-weight: 600;
    color: #ffffff;
    margin: 0 0 14px 0;
    letter-spacing: -0.01em;
    position: relative;
    z-index: 1;
  }

  .hp-cta-inner p {
    font-size: 1.02rem;
    color: rgba(255,255,255,0.65);
    margin: 0 0 32px 0;
    position: relative;
    z-index: 1;
  }

  .hp-cta-inner .hp-btn-primary {
    background: #ffffff;
    color: var(--ink);
    position: relative;
    z-index: 1;
  }

  .hp-cta-inner .hp-btn-primary:hover { background: #7FBF9E; color: #ffffff; }

  /* ══════════════════════════════════════════════════════════════════
     FOOTER
     ══════════════════════════════════════════════════════════════════ */
  .hp-footer {
    max-width: 1320px;
    margin: 0 auto;
    padding: 0 48px 56px;
  }

  .hp-footer-top {
    display: grid;
    grid-template-columns: 1.4fr 1fr 1fr 1fr;
    gap: 40px;
    padding-bottom: 48px;
    border-bottom: 1px solid var(--line);
  }

  .hp-footer-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 1.15rem;
    color: var(--ink);
    margin-bottom: 14px;
  }

  .hp-footer-about {
    font-size: 0.88rem;
    color: var(--slate);
    line-height: 1.6;
    max-width: 280px;
  }

  .hp-footer-col h5 {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--slate-l);
    margin: 0 0 16px 0;
  }

  .hp-footer-col ul {
    display: flex;
    flex-direction: column;
    gap: 11px;
  }

  .hp-footer-col a {
    font-size: 0.9rem;
    color: var(--slate);
    cursor: pointer;
  }

  .hp-footer-col a:hover { color: var(--ink); }

  .hp-footer-bottom {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 28px;
    font-size: 0.84rem;
    color: var(--slate-l);
  }

  .hp-footer-bottom-links {
    display: flex;
    gap: 24px;
  }

  /* ══════════════════════════════════════════════════════════════════
     RESPONSIVE
     ══════════════════════════════════════════════════════════════════ */
  @media (max-width: 1080px) {
    .hp-hero { grid-template-columns: 1fr; padding: 64px 32px 40px; }
    .hp-hero h1 { font-size: 2.8rem; max-width: 100%; }
    .hp-hero-desc { max-width: 100%; }
    .hp-hero-blob { display: none; }
    .hp-hero-bg-image { display: none; }
    .hp-stats-band { grid-template-columns: repeat(2, 1fr); gap: 32px 0; border-radius: 20px; }
    .hp-stat-item { border-right: none !important; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 24px; }
    .hp-features-grid { grid-template-columns: 1fr; }
    .hp-console-grid { grid-template-columns: 1fr; }
    .hp-console-menu { flex-direction: row; overflow-x: auto; gap: 8px; padding-bottom: 4px; }
    .hp-console-item { white-space: nowrap; }
    .hp-pricing-grid { grid-template-columns: 1fr; }
    .hp-footer-top { grid-template-columns: 1fr 1fr; gap: 32px; }
    .hp-section { padding: 64px 32px; }
    .hp-nav { padding: 16px 24px; }
    .hp-nav-links { display: none; }
  }

  @media (max-width: 640px) {
    .hp-hero { padding: 48px 20px 32px; }
    .hp-hero h1 { font-size: 2.2rem; }
    .hp-section { padding: 48px 20px; }
    .hp-section-head h2 { font-size: 1.8rem; }
    .hp-stats-band { padding: 36px 24px; grid-template-columns: 1fr; }
    .hp-stat-item { border-right: none !important; }
    .hp-console { padding: 28px 20px; }
    .hp-cta-inner { padding: 48px 24px; }
    .hp-cta-inner h2 { font-size: 1.8rem; }
    .hp-footer-top { grid-template-columns: 1fr; }
    .hp-footer-bottom { flex-direction: column; gap: 14px; align-items: flex-start; }
    .hp-trust-strip { flex-direction: column; align-items: flex-start; gap: 16px; padding-bottom: 40px; }
    .hp-nav-actions .hp-nav-login { display: none; }
    .hp-hero-actions { flex-direction: column; align-items: stretch; }
    .hp-hero-actions .hp-btn-primary, .hp-hero-actions .hp-btn-secondary { justify-content: center; }
    .hp-spec-summary { flex-wrap: wrap; gap: 16px; padding: 18px 20px; }
    .hp-spec-summary-divider { display: none; }
  }
`

const NAV_LINKS = [
  { label: 'Safeguards', target: 'safeguards' },
  { label: 'Risk Console', target: 'compliance-console' },
  { label: 'Data Spec', target: 'data-spec' },
  { label: 'Pricing', target: 'pricing' },
]

const MODULES_DATA = {
  gender: {
    title: 'Gender Pipeline Parity',
    framework: 'Equal Opportunity & Labour Equity Standards',
    rule: 'Compares shortlist and offer rates between genders at every stage of the pipeline to surface statistically significant drop-off.',
    flag: 'FLAG [GENDER-V3]: Offer rate for women is 31% lower than men at the technical-interview stage — outside the accepted variance band.',
    vars: ['gender', 'shortlisted', 'hired'],
    status: 'flag',
  },
  caste: {
    title: 'Caste & Social Category Parity',
    framework: 'Constitutional Equality Provisions & Reservation Mandates',
    rule: 'Checks shortlisting and conversion rates across caste and social-category groups against statutory representation expectations.',
    flag: 'FLAG [CASTE-V3]: Conversion rate for reserved-category applicants drops 18 points between application and shortlist.',
    vars: ['caste_category', 'shortlisted', 'hired'],
    status: 'flag',
  },
  disability: {
    title: 'Disability Access Parity',
    framework: 'Equal Access & Reasonable Accommodation Statutes',
    rule: 'Tracks candidates with disclosed disabilities through every funnel stage to catch accessibility-related drop-off early.',
    flag: 'CLEAR [DISABILITY-V3]: No statistically significant gap detected this audit cycle. Continue monitoring.',
    vars: ['disability_status', 'shortlisted', 'hired'],
    status: 'ok',
  },
  skin: {
    title: 'Appearance Bias Scan',
    framework: 'Anti-Discrimination & Equal Representation Codes',
    rule: 'Screens for correlation between recorded appearance attributes and outcomes in remote, photo-based evaluation rounds.',
    flag: 'FLAG [APPEARANCE-V3]: Weak but consistent correlation detected between skin-tone field and first-round rejection.',
    vars: ['skin_tone_group', 'shortlisted', 'hired'],
    status: 'flag',
  },
  proxy: {
    title: 'Proxy Variable Detection',
    framework: 'Indirect Discrimination Safeguards',
    rule: 'Scans neutral-looking fields — postal code, school name — for hidden correlation with protected demographic attributes.',
    flag: 'FLAG [PROXY-V3]: Postal code field reconstructs gender with 86% accuracy — treat as a sensitive proxy field.',
    vars: ['postal_code', 'location_category', 'hired'],
    status: 'flag',
  },
  funnel: {
    title: 'Multi-Stage Funnel Tracker',
    framework: 'Full-Lifecycle Process Fairness Review',
    rule: 'Breaks the hiring funnel into individual gates — screen, assessment, interview, offer — to isolate exactly where imbalance enters.',
    flag: 'FLAG [FUNNEL-V3]: 92% of the disparity originates at the technical-assessment gate, not later interview rounds.',
    vars: ['assessment_score', 'interview_status', 'hired'],
    status: 'flag',
  },
  institution: {
    title: 'Sourcing Concentration Scan',
    framework: 'Open Talent Access & Anti-Elitism Benchmarks',
    rule: 'Measures how dependent your hires are on a narrow band of universities or past employers, which can quietly exclude qualified talent.',
    flag: 'CLEAR [INSTITUTION-V3]: Hires this cycle draw from 41 distinct institutions — within healthy diversity range.',
    vars: ['university_tier', 'source_channel', 'hired'],
    status: 'ok',
  },
  marital: {
    title: 'Intersectional Outcome Scan',
    framework: 'Multi-Category Fairness Cross-Check',
    rule: 'Combines two or more candidate attributes at once to catch compounding disadvantage that single-variable checks miss.',
    flag: 'FLAG [INTERSECT-V3]: Married women candidates convert 22% lower than every other group combination.',
    vars: ['marital_status', 'gender', 'hired'],
    status: 'flag',
  },
  age: {
    title: 'Age Demographics Parity',
    framework: 'Career-Stage Protection & Lifecycle Fairness Rules',
    rule: 'Confirms that junior, mid-career, and senior age brackets are evaluated against comparable funnel gates and pass rates.',
    flag: 'CLEAR [AGE-V3]: Pass-through rates are within 4 points across all age brackets this cycle.',
    vars: ['age_bracket', 'dob', 'hired'],
    status: 'ok',
  },
  referral: {
    title: 'Referral Network Guard',
    framework: 'Sourcing Transparency & Anti-Nepotism Standards',
    rule: 'Measures how much of your hiring volume comes through internal referrals versus open channels, to catch network monopolisation.',
    flag: 'FLAG [REFERRAL-V3]: 61% of senior hires came through internal referral — above the recommended 40% ceiling.',
    vars: ['referral_source', 'application_mode', 'hired'],
    status: 'flag',
  },
}

export default function HomePage({ isGuest = true, onStartApp }) {
  const [activeTab, setActiveTab] = useState('gender')
  const [scoreAnimated, setScoreAnimated] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const scoreRef = useRef(null)

  useEffect(() => {
    const existingTag = document.getElementById(AUDIT_OVERRIDE_ID)
    if (!existingTag) {
      const styleTag = document.createElement('style')
      styleTag.id = AUDIT_OVERRIDE_ID
      styleTag.type = 'text/css'
      styleTag.innerHTML = AUDIT_TEMPLATE_CSS
      document.head.appendChild(styleTag)
    }
    return () => {
      const tag = document.getElementById(AUDIT_OVERRIDE_ID)
      if (tag) tag.remove()
    }
  }, [])

  // Trigger the score-ring fill animation once, shortly after mount
  useEffect(() => {
    const t = setTimeout(() => setScoreAnimated(true), 250)
    return () => clearTimeout(t)
  }, [])

  const currentModule = MODULES_DATA[activeTab] || MODULES_DATA.gender

  const scrollTo = (id) => {
    setMobileNavOpen(false)
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
  }

  // Scorecard ring math — 0..100 score mapped to a 264px circumference (r=42)
  const SCORE = 74
  const RADIUS = 42
  const CIRC = 2 * Math.PI * RADIUS
  const offset = CIRC - (scoreAnimated ? (SCORE / 100) * CIRC : 0)

  return (
    <div className="hp-wrapper">

      {/* ── NAVBAR ── */}
      <header className="hp-nav">
        <div className="hp-nav-brand">
          <span className="hp-nav-mark">⚖</span>
          FairHire
        </div>
        <nav className="hp-nav-links">
          {NAV_LINKS.map((l) => (
            <span key={l.target} className="hp-nav-link" onClick={() => scrollTo(l.target)}>
              {l.label}
            </span>
          ))}
        </nav>
        <div className="hp-nav-actions">
          {isGuest ? (
            <>
              <button className="hp-nav-login" onClick={onStartApp}>Log in</button>
              <button className="hp-nav-cta" onClick={onStartApp}>Start free audit</button>
            </>
          ) : (
            <button className="hp-nav-cta" onClick={onStartApp}>Open workspace</button>
          )}
        </div>
      </header>

      {/* ── HERO ── */}
      <section className="hp-hero">
        <img
          className="hp-hero-bg-image"
          src="https://s3.ap-south-1.amazonaws.com/wp-media.yellowchalk.com/wp-content/uploads/2023/09/14092926/Frame-19-1024x512.png"
          alt=""
          aria-hidden="true"
        />
        <div className="hp-hero-blob" />

        <div className="hp-hero-left">
          <div className="hp-eyebrow">
            <span className="hp-eyebrow-dot" />
            Audit engine v2.0 — 10 bias modules live
          </div>

          <h1>
            Find out where your <em>hiring pipeline</em> quietly breaks fair.
          </h1>

          <p className="hp-hero-desc">
            Upload your recruitment data and FairHire scans every stage — screening,
            interviews, offers — against gender, caste, disability and seven other
            fairness frameworks. Get a scored report in minutes, not a quarterly audit.
          </p>

          <div className="hp-hero-actions">
            <button className="hp-btn-primary" onClick={onStartApp}>
              {isGuest ? 'Start free audit →' : 'Upload your CSV →'}
            </button>
            <button className="hp-btn-secondary" onClick={() => scrollTo('compliance-console')}>
              See how it scans
            </button>
          </div>

          <div className="hp-hero-proof">
            <div className="hp-proof-avatars">
              <div className="hp-proof-avatar">HR</div>
              <div className="hp-proof-avatar">TA</div>
              <div className="hp-proof-avatar">DEI</div>
            </div>
            <p className="hp-proof-text">
              <strong>Built for</strong> HR, Talent Acquisition &amp; DEI teams running audits before reports go to leadership.
            </p>
          </div>
        </div>

        <div className="hp-hero-right">
          <div className="hp-float-chip c1">📄 Report ready in 6 min</div>
          <div className="hp-float-chip c2">🔒 Data deleted after audit</div>

          <div className="hp-scorecard">
            <div className="hp-scorecard-head">
              <span className="hp-scorecard-title">Fairness Scorecard</span>
              <span className="hp-scorecard-live"><span className="hp-live-dot" />Live preview</span>
            </div>

            <div className="hp-scorecard-body">
              <div className="hp-score-ring">
                <svg viewBox="0 0 100 100" width="108" height="108">
                  <circle className="hp-score-ring-track" cx="50" cy="50" r={RADIUS} />
                  <circle
                    className="hp-score-ring-fill"
                    cx="50" cy="50" r={RADIUS}
                    strokeDasharray={CIRC}
                    strokeDashoffset={offset}
                  />
                </svg>
                <div className="hp-score-ring-num">
                  <strong>{SCORE}</strong>
                  <span>/ 100</span>
                </div>
              </div>
              <div className="hp-score-summary">
                <h4>Needs attention</h4>
                <p>3 of 10 modules flagged a statistically significant gap this cycle.</p>
              </div>
            </div>

            <div className="hp-scorecard-rows">
              <div className="hp-score-row">
                <span className="hp-score-row-label">
                  <span className="hp-row-icon flag">!</span> Gender pipeline parity
                </span>
                <span className="hp-score-row-status flag">Flagged</span>
              </div>
              <div className="hp-score-row">
                <span className="hp-score-row-label">
                  <span className="hp-row-icon ok">✓</span> Disability access parity
                </span>
                <span className="hp-score-row-status ok">Clear</span>
              </div>
              <div className="hp-score-row">
                <span className="hp-score-row-label">
                  <span className="hp-row-icon flag">!</span> Referral concentration
                </span>
                <span className="hp-score-row-status flag">Flagged</span>
              </div>
            </div>

            <div className="hp-scorecard-foot">
              Sample output · run on <code>demo_pipeline.csv</code>
            </div>
          </div>
        </div>
      </section>

      {/* ── TRUST STRIP ── */}
      <div className="hp-trust-strip">
        <span className="hp-trust-label">Frameworks we check against</span>
        <div className="hp-trust-logos">
          <span>EEOC</span>
          <span>ISO 30415</span>
          <span>EU AI Act</span>
          <span>Constitutional Equality Code</span>
          <span>ILO C111</span>
        </div>
      </div>

      {/* ── STATS BAND ── */}
      <section className="hp-section hp-section-tight">
        <div className="hp-stats-band">
          <div className="hp-stats-glow" />
          <div className="hp-stat-item">
            <div className="hp-stat-num"><span>10</span></div>
            <div className="hp-stat-label">Bias detection modules covering gender, caste, disability, age &amp; more</div>
          </div>
          <div className="hp-stat-item">
            <div className="hp-stat-num">6<span>min</span></div>
            <div className="hp-stat-label">Average time from CSV upload to a finished audit report</div>
          </div>
          <div className="hp-stat-item">
            <div className="hp-stat-num">500<span>+</span></div>
            <div className="hp-stat-label">Employee records per audit on the Starter plan, no setup needed</div>
          </div>
          <div className="hp-stat-item">
            <div className="hp-stat-num"><span>0</span></div>
            <div className="hp-stat-label">Raw applicant data retained after your report is generated</div>
          </div>
        </div>
      </section>

      {/* ── SAFEGUARDS ── */}
      <section className="hp-section" id="safeguards">
        <div className="hp-section-head center">
          <div className="hp-kicker" style={{ justifyContent: 'center' }}>Core safeguards</div>
          <h2>Three checks run on every audit, automatically</h2>
          <p>No configuration required — every upload runs through the full safeguard stack before you see a single chart.</p>
        </div>

        <div className="hp-features-grid">
          <div className="hp-feature-card">
            <div className="hp-feature-icon">📊</div>
            <h3>One score, full context</h3>
            <p>A single 0–100 fairness score gives leadership the headline number, while the breakdown underneath shows exactly which stage and group it came from.</p>
          </div>

          <div className="hp-feature-card">
            <div className="hp-feature-icon">🛡️</div>
            <h3>Checked against real frameworks</h3>
            <p>Every module maps to a named legal or regulatory standard — not a generic "bias score" — so findings hold up when you have to explain them.</p>
          </div>

          <div className="hp-feature-card">
            <div className="hp-feature-icon">🧹</div>
            <h3>Noise filtered before flagging</h3>
            <p>Small sample sizes and seasonal hiring swings are filtered out automatically, so a flag in your report means a real, statistically sound gap.</p>
          </div>
        </div>
      </section>

      {/* ── RISK CONSOLE ── */}
      <section className="hp-section" id="compliance-console">
        <div className="hp-console">
          <div className="hp-section-head" style={{ marginBottom: 0 }}>
            <div className="hp-kicker">Risk parameter console</div>
            <h2>Pick a module, see exactly what it checks</h2>
            <p>Every audit runs all ten by default. Click through them here to see the framework, the rule, and a sample flag before you ever upload a file.</p>
          </div>

          <div className="hp-console-grid">
            <div className="hp-console-menu">
              {Object.keys(MODULES_DATA).map((key) => (
                <button
                  key={key}
                  className={`hp-console-item ${activeTab === key ? 'is-selected' : ''}`}
                  onClick={() => setActiveTab(key)}
                >
                  <span>{key === 'funnel' ? 'Multi-stage funnel' : key}</span>
                  <span className="hp-console-arrow">→</span>
                </button>
              ))}
            </div>

            <div className="hp-console-view">
              <div>
                <p className="hp-console-view-label">Module</p>
                <h4 className="hp-console-view-title">{currentModule.title}</h4>
                <p className="hp-console-view-sub">{currentModule.framework}</p>
              </div>

              <div>
                <p className="hp-console-view-label">What it checks</p>
                <p className="hp-console-rule-text">{currentModule.rule}</p>
              </div>

              <div>
                <p className="hp-console-view-label">Sample output</p>
                <div className="hp-alert-banner">
                  <span>{currentModule.status === 'flag' ? '⚠️' : '✅'}</span>
                  <span>{currentModule.flag}</span>
                </div>
              </div>

              <div>
                <p className="hp-console-view-label">Fields it reads</p>
                <div className="hp-token-wrap">
                  {currentModule.vars.map((v, idx) => (
                    <span key={idx} className="hp-token">{v}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── DATA SPEC TABLE ── */}
      <section className="hp-section" id="data-spec">
        <div className="hp-section-head">
          <div className="hp-kicker">Before you upload</div>
          <h2>What your CSV needs to include</h2>
          <p>Every audit reads all 10 fields below. Include them all in your CSV so each bias detection module has the data it needs to run.</p>
        </div>

        <div className="hp-spec-summary">
          <div className="hp-spec-summary-stat">
            <strong>10</strong>
            <span>Required fields</span>
          </div>
          <div className="hp-spec-summary-divider" />
          <div className="hp-spec-summary-stat">
            <strong>10</strong>
            <span>Modules unlocked</span>
          </div>
          <div className="hp-spec-summary-divider" />
          <div className="hp-spec-summary-stat">
            <strong>1</strong>
            <span>CSV upload</span>
          </div>
        </div>

        <div className="hp-table-frame">
          <table className="hp-schema-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Column</th>
                <th>Status</th>
                <th>Accepted values</th>
                <th>What it powers</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><span className="hp-row-index">01</span></td>
                <td><strong>gender</strong></td>
                <td><span className="hp-pill-required">Required</span></td>
                <td><span className="hp-code">Male</span>, <span className="hp-code">Female</span>, <span className="hp-code">Non-binary</span></td>
                <td><p>Gender pipeline parity module</p></td>
              </tr>
              <tr>
                <td><span className="hp-row-index">02</span></td>
                <td><strong>shortlisted</strong></td>
                <td><span className="hp-pill-required">Required</span></td>
                <td><span className="hp-code">0</span> (No) or <span className="hp-code">1</span> (Yes)</td>
                <td><p>Conversion rate at the screening gate</p></td>
              </tr>
              <tr>
                <td><span className="hp-row-index">03</span></td>
                <td><strong>hired</strong></td>
                <td><span className="hp-pill-required">Required</span></td>
                <td><span className="hp-code">0</span> (No) or <span className="hp-code">1</span> (Yes)</td>
                <td><p>End-to-end conversion against the original applicant pool</p></td>
              </tr>
              <tr>
                <td><span className="hp-row-index">04</span></td>
                <td><strong>disability_status</strong></td>
                <td><span className="hp-pill-required">Required</span></td>
                <td><span className="hp-code">Yes</span>, <span className="hp-code">No</span></td>
                <td><p>Disability access parity module</p></td>
              </tr>
              <tr>
                <td><span className="hp-row-index">05</span></td>
                <td><span className="hp-code">caste</span> / <span className="hp-code">category</span> / <span className="hp-code">social_group</span></td>
                <td><span className="hp-pill-required">Required</span></td>
                <td>Free-text category labels</td>
                <td><p>Caste &amp; social category parity module</p></td>
              </tr>
              <tr>
                <td><span className="hp-row-index">06</span></td>
                <td><span className="hp-code">skin_colour</span> / <span className="hp-code">skin_tone</span></td>
                <td><span className="hp-pill-required">Required</span></td>
                <td>Integer tone-scale values</td>
                <td><p>Appearance bias scan</p></td>
              </tr>
              <tr>
                <td><span className="hp-row-index">07</span></td>
                <td><strong>referral</strong></td>
                <td><span className="hp-pill-required">Required</span></td>
                <td>Source labels (e.g. Agency, Employee Referral)</td>
                <td><p>Referral network guard</p></td>
              </tr>
              <tr>
                <td><span className="hp-row-index">08</span></td>
                <td><strong>marital_status</strong></td>
                <td><span className="hp-pill-required">Required</span></td>
                <td><span className="hp-code">Single</span>, <span className="hp-code">Married</span>, <span className="hp-code">Divorced</span></td>
                <td><p>Intersectional outcome scan</p></td>
              </tr>
              <tr>
                <td><span className="hp-row-index">09</span></td>
                <td><strong>institution</strong></td>
                <td><span className="hp-pill-required">Required</span></td>
                <td>University or employer name</td>
                <td><p>Sourcing concentration scan</p></td>
              </tr>
              <tr>
                <td><span className="hp-row-index">10</span></td>
                <td><strong>age</strong> / <strong>dob</strong></td>
                <td><span className="hp-pill-required">Required</span></td>
                <td>Integer age or date</td>
                <td><p>Age demographics parity module</p></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* ── PRICING ── */}
      <section className="hp-section" id="pricing">
        <div className="hp-section-head center">
          <div className="hp-kicker" style={{ justifyContent: 'center' }}>Pricing</div>
          <h2>Simple, transparent pricing</h2>
          <p>Run a one-time audit before your next board review, or keep monitoring continuously. No hidden setup fees either way.</p>
        </div>

        <div className="hp-pricing-grid">

          {/* STARTER */}
          <div className="hp-price-card">
            <div className="hp-plan-chip">📋 Starter</div>
            <h3 className="hp-plan-name">Audit Report</h3>
            <p className="hp-plan-sub">A single deep audit with a full PDF report you can hand straight to leadership.</p>

            <div className="hp-price-block">
              <span className="hp-price-currency">₹</span>
              <span className="hp-price-amount">25K</span>
            </div>
            <p className="hp-price-unit">per audit</p>
            <p className="hp-capacity-note">Up to 500 employees</p>

            <div className="hp-price-divider" />

            <ul className="hp-feature-list">
              <li><span className="hp-feat-tick">✓</span>All 10 bias detection modules</li>
              <li><span className="hp-feat-tick">✓</span>Full PDF audit report</li>
              <li><span className="hp-feat-tick">✓</span>Gender, caste, disability, appearance</li>
              <li><span className="hp-feat-tick">✓</span>Referral &amp; institution analysis</li>
              <li><span className="hp-feat-tick">✓</span>Flag-level remediation notes</li>
            </ul>

            <button className="hp-price-cta" onClick={onStartApp}>Start free audit</button>
          </div>

          {/* PROFESSIONAL */}
          <div className="hp-price-card featured">
            <div className="hp-popular-tag">Most popular</div>
            <div className="hp-plan-chip">🏢 Professional</div>
            <h3 className="hp-plan-name">Monthly Plan</h3>
            <p className="hp-plan-sub">Continuous monitoring with trend tracking and full data exports.</p>

            <div className="hp-price-block">
              <span className="hp-price-currency">₹</span>
              <span className="hp-price-amount">68K</span>
            </div>
            <p className="hp-price-unit">per month</p>
            <p className="hp-capacity-note">Up to 5,000 employees</p>

            <div className="hp-price-divider" />

            <ul className="hp-feature-list">
              <li><span className="hp-feat-tick">✓</span>Everything in Starter</li>
              <li><span className="hp-feat-tick">✓</span>Unlimited monthly audits</li>
              <li><span className="hp-feat-tick">✓</span>JSON data export included</li>
              <li><span className="hp-feat-tick">✓</span>Trend tracking over time</li>
              <li><span className="hp-feat-tick">✓</span>Priority support &amp; SLA</li>
              <li><span className="hp-feat-tick">✓</span>Multi-role team access</li>
            </ul>

            <button className="hp-price-cta" onClick={onStartApp}>Get monthly access</button>
          </div>

          {/* ENTERPRISE */}
          <div className="hp-price-card">
            <div className="hp-soon-tag">Coming soon</div>
            <div className="hp-plan-chip">⚡ Enterprise</div>
            <h3 className="hp-plan-name">API Access</h3>
            <p className="hp-plan-sub">Programmatic access for custom pipelines and internal HR tooling.</p>

            <div className="hp-price-block">
              <span className="hp-price-currency">₹</span>
              <span className="hp-price-amount">1.5L</span>
            </div>
            <p className="hp-price-unit">per month</p>
            <p className="hp-capacity-note">1M token context window</p>

            <div className="hp-price-divider" />

            <ul className="hp-feature-list">
              <li><span className="hp-feat-tick">✓</span>Everything in Professional</li>
              <li><span className="hp-feat-tick">✓</span>Dedicated API keys</li>
              <li><span className="hp-feat-tick">✓</span>Webhook &amp; HRMS integration</li>
              <li><span className="hp-feat-tick">✓</span>Custom module configuration</li>
              <li><span className="hp-feat-tick">✓</span>Dedicated account manager</li>
            </ul>

            <button className="hp-price-cta" disabled>Notify me on launch</button>
          </div>

        </div>
      </section>

      {/* ── CLOSING CTA ── */}
      <section className="hp-cta-band">
        <div className="hp-cta-inner">
          <h2>Run your first audit before your next leadership review</h2>
          <p>Upload a CSV, get a scored report in minutes — no setup, no commitment.</p>
          <button className="hp-btn-primary" onClick={onStartApp}>
            {isGuest ? 'Start free audit →' : 'Open workspace →'}
          </button>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="hp-footer">
        <div className="hp-footer-top">
          <div>
            <div className="hp-footer-brand">
              <span className="hp-nav-mark">⚖</span>
              FairHire
            </div>
            <p className="hp-footer-about">
              FairHire audits recruitment pipelines for bias across gender, caste, disability,
              age and more — so fairness gaps surface before they become legal or reputational risk.
            </p>
          </div>

          <div className="hp-footer-col">
            <h5>Product</h5>
            <ul>
              <li><a onClick={() => scrollTo('safeguards')}>Safeguards</a></li>
              <li><a onClick={() => scrollTo('compliance-console')}>Risk console</a></li>
              <li><a onClick={() => scrollTo('data-spec')}>Data spec</a></li>
              <li><a onClick={() => scrollTo('pricing')}>Pricing</a></li>
            </ul>
          </div>

          <div className="hp-footer-col">
            <h5>Frameworks</h5>
            <ul>
              <li><a>EEOC</a></li>
              <li><a>ISO 30415</a></li>
              <li><a>EU AI Act</a></li>
              <li><a>ILO C111</a></li>
            </ul>
          </div>

          <div className="hp-footer-col">
            <h5>Company</h5>
            <ul>
              <li><a onClick={onStartApp}>Log in</a></li>
              <li><a onClick={onStartApp}>Start an audit</a></li>
              <li><a>Contact</a></li>
            </ul>
          </div>
        </div>

        <div className="hp-footer-bottom">
          <span>© {new Date().getFullYear()} FairHire. All rights reserved.</span>
          <div className="hp-footer-bottom-links">
            <a>Privacy</a>
            <a>Terms</a>
            <a>Security</a>
          </div>
        </div>
      </footer>

    </div>
  )
}
