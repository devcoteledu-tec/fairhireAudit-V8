import React, { useState, useEffect } from 'react'

/* ==========================================================================
   PREMIUM LIGHT-MODE MINIMAL OVERRIDES (Injected safely into Head)
   ========================================================================== */
const AUDIT_OVERRIDE_ID = 'fairhire-light-minimal-theme'
const AUDIT_TEMPLATE_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

  /* ── Structural Layout Core ── */
  .hp-wrapper {
    font-family: 'Plus Jakarta Sans', sans-serif;
    color: #1e293b;
    min-height: 100vh;
    overflow-x: hidden;
    position: relative;
    -webkit-font-smoothing: antialiased;
    background: #ffffff;
    padding: 40px 24px;
  }

  .hp-container {
    max-width: 1440px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 64px;
  }

  /* ── Kinetic Smooth Transitions ── */
  .hp-wrapper *, .hp-wrapper *::before, .hp-wrapper *::after {
    box-sizing: border-box;
    transition: color 0.25s cubic-bezier(0.16, 1, 0.3, 1),
            background-color 0.25s cubic-bezier(0.16, 1, 0.3, 1),
            border-color 0.25s cubic-bezier(0.16, 1, 0.3, 1),
            transform 0.25s cubic-bezier(0.16, 1, 0.3, 1),
            opacity 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  /* ── SECTION A: TEMPLATE HERO STYLING ── */
  .hp-template-hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    background: #ffffff;
    padding: 80px 24px 60px 24px;
    position: relative;
  }

  .hp-badge-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    padding: 6px 16px;
    border-radius: 100px;
    font-family: 'Outfit', sans-serif;
    font-size: 0.8rem;
    font-weight: 600;
    color: #64748b;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 24px;
  }

  .hp-hero-title-group h1 {
    font-family: 'Outfit', sans-serif;
    font-size: 4.2rem;
    font-weight: 800;
    line-height: 1.1;
    margin: 0 auto 24px auto;
    color: #0f172a;
    letter-spacing: -0.03em;
    max-width: 900px;
  }

  .hp-hero-title-group h1 span {
    color: #2563eb;
  }

  .hp-hero-description {
    font-size: 1.2rem;
    line-height: 1.6;
    color: #475569;
    max-width: 720px;
    margin: 0 auto 40px auto;
    font-weight: 400;
  }

  .hp-hero-input-bar {
    display: flex;
    align-items: center;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 100px;
    padding: 8px 12px 8px 24px;
    width: 100%;
    max-width: 640px;
    margin: 0 auto 24px auto;
    box-shadow: 0 10px 25px rgba(15, 23, 42, 0.03);
  }

  .hp-hero-input-bar input {
    border: none;
    outline: none;
    width: 100%;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 1rem;
    color: #0f172a;
    background: transparent;
  }

  .hp-hero-input-bar input::placeholder {
    color: #94a3b8;
  }

  .hp-input-bar-btn {
    font-family: 'Outfit', sans-serif;
    background: #0f172a;
    color: #ffffff;
    border: none;
    padding: 12px 28px;
    border-radius: 100px;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }

  .hp-input-bar-btn:hover {
    background: #1e293b;
  }

  .hp-hero-actions {
    display: flex;
    gap: 16px;
    justify-content: center;
    flex-wrap: wrap;
  }

  .hp-btn-outline-dark {
    font-family: 'Outfit', sans-serif;
    background: #ffffff;
    color: #475569;
    border: 1px solid #e2e8f0;
    padding: 12px 28px;
    border-radius: 100px;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }

  .hp-btn-outline-dark:hover {
    background: #f8fafc;
    color: #0f172a;
    border-color: #cbd5e1;
  }

  /* ── SECTION B: CORE SAFEGUARDS REFACTORED (New Block Color Style) ── */
  .hp-section-wrapper {
    display: flex;
    flex-direction: column;
    gap: 40px;
  }

  .hp-centered-title {
    text-align: center;
  }

  .hp-centered-title h2 {
    font-family: 'Outfit', sans-serif;
    font-size: 2.5rem;
    font-weight: 800;
    margin: 0 0 10px 0;
    color: #0f172a;
    letter-spacing: -0.02em;
  }

  .hp-centered-title p {
    font-size: 1.05rem;
    color: #64748b;
    margin: 0;
  }

  .hp-trio-layout {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
  }

  .hp-feature-node {
    background: #0f172a; /* Deep structural dark fill from design template */
    border: 1px solid #1e293b;
    border-radius: 16px; /* Clean block geometry shapes */
    padding: 32px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    box-shadow: 0 15px 35px rgba(15, 23, 42, 0.08);
    position: relative;
    overflow: hidden;
  }

  .hp-feature-node:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 40px rgba(15, 23, 42, 0.15);
    border-color: #334155;
  }

  .hp-icon-housing {
    width: 44px;
    height: 44px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    color: #ffffff;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  /* Distinct color paths for structural icon badges as requested */
  .hp-icon-housing.blue-badge { background: #2563eb; }
  .hp-icon-housing.emerald-badge { background: #10b981; }
  .hp-icon-housing.purple-badge { background: #8b5cf6; }

  .hp-feature-node h3 {
    font-family: 'Outfit', sans-serif;
    font-size: 1.35rem;
    font-weight: 700;
    margin: 0;
    color: #ffffff; /* High contrast heading title */
    letter-spacing: -0.01em;
  }

  .hp-feature-node p {
    font-size: 0.92rem;
    line-height: 1.6;
    color: #94a3b8; /* Muted modern prose spacing layout text */
    margin: 0;
  }

  /* ── SECTION C: INTERACTIVE RISK CONSOLE HUB ── */
  .hp-glass-mainframe {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 24px;
    padding: 44px;
    box-shadow: 0 8px 30px rgba(15, 23, 42, 0.02);
  }

  .hp-console-split {
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 40px;
    margin-top: 32px;
  }

  .hp-console-menu {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .hp-console-item {
    font-family: 'Outfit', sans-serif;
    background: transparent;
    color: #475569;
    border: 1px solid transparent;
    padding: 14px 18px;
    border-radius: 10px;
    cursor: pointer;
    text-align: left;
    font-size: 0.95rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .hp-console-item:hover {
    color: #0f172a;
    background: #f1f5f9;
  }

  .hp-console-item.is-selected {
    background: #f1f5f9;
    color: #2563eb;
    border: 1px solid #cbd5e1;
  }

  .hp-console-arrow {
    opacity: 0;
    transform: translateX(-4px);
  }

  .hp-console-item.is-selected .hp-console-arrow {
    opacity: 1;
    transform: translateX(0);
  }

  .hp-view-surface {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 36px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .hp-view-surface h4 {
    font-family: 'Outfit', sans-serif;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #475569;
    margin: 0 0 8px 0;
  }

  .hp-surface-body {
    font-size: 1rem;
    line-height: 1.55;
    color: #334155;
    margin: 0;
  }

  .hp-log-banner {
    background: #fef2f2;
    border: 1px solid #fee2e2;
    border-radius: 10px;
    padding: 14px 18px;
    font-family: monospace;
    font-size: 0.88rem;
    color: #991b1b;
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .hp-token-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .hp-token-node {
    font-family: monospace;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    color: #475569;
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 0.82rem;
  }

  /* ── SECTION D: BLUEPRINT DECK WITH IMAGES ── */
  .hp-blueprint-deck {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
  }

  .hp-blueprint-node {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 20px;
    border-radius: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .hp-blueprint-node:hover {
    border-color: #cbd5e1;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
  }

  .hp-blueprint-img-frame {
    width: 100%;
    height: 140px;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
    background: #ffffff;
  }

  .hp-blueprint-img-frame img {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  .hp-blueprint-node h4 {
    font-family: 'Outfit', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    margin: 0;
    color: #0f172a;
  }

  .hp-blueprint-node p {
    font-size: 0.88rem;
    line-height: 1.5;
    color: #475569;
    margin: 0;
  }

  /* ── SECTION E: PRODUCTION SCHEMATIC MATRIX ── */
  .hp-table-frame {
    overflow-x: auto;
    border-radius: 14px;
    border: 1px solid #e2e8f0;
    background: #ffffff;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.005);
  }

  .hp-schematic-grid {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 0.92rem;
  }

  .hp-schematic-grid th {
    font-family: 'Outfit', sans-serif;
    background: #f8fafc;
    color: #0f172a;
    padding: 16px 20px;
    font-weight: 600;
    border-bottom: 1px solid #e2e8f0;
  }

  .hp-schematic-grid td {
    padding: 16px 20px;
    border-bottom: 1px solid #f1f5f9;
    color: #334155;
    vertical-align: top;
    line-height: 1.5;
  }

  .hp-schematic-grid tr:last-child td {
    border-bottom: none;
  }

  .hp-schematic-grid tr:hover td {
    background: #f8fafc;
  }

  .hp-badge-critical {
    background: #fef2f2;
    color: #b91c1c;
    border: 1px solid #fca5a5;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .hp-badge-secondary {
    background: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .hp-code-inline {
    font-family: monospace;
    background: #f1f5f9;
    padding: 2px 6px;
    border-radius: 4px;
    color: #2563eb;
    font-size: 0.85rem;
  }

  /* ── SECTION F: PRICING CARDS ── */
  .hp-pricing-section {
    display: flex;
    flex-direction: column;
    gap: 48px;
    position: relative;
  }

  .hp-pricing-header {
    text-align: center;
  }

  .hp-pricing-header h2 {
    font-family: 'Outfit', sans-serif;
    font-size: 2.6rem;
    font-weight: 800;
    color: #0f172a;
    margin: 0 0 12px 0;
    letter-spacing: -0.03em;
  }

  .hp-pricing-header p {
    font-size: 1.05rem;
    color: #64748b;
    margin: 0;
  }

  .hp-pricing-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
    align-items: stretch;
  }

  /* ── BASE CARD ── */
  .hp-price-card {
    position: relative;
    border-radius: 24px;
    padding: 40px 36px 36px;
    display: flex;
    flex-direction: column;
    gap: 0;
    overflow: hidden;
    transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1),
                box-shadow 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
  }

  .hp-price-card:hover {
    transform: translateY(-6px) !important;
  }

  /* ── STARTER (Audit) ── */
  .hp-price-card.starter {
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    box-shadow: 0 4px 20px rgba(15, 23, 42, 0.06);
  }

  .hp-price-card.starter:hover {
    box-shadow: 0 16px 48px rgba(15, 23, 42, 0.12) !important;
    border-color: #cbd5e1;
  }

  /* ── PROFESSIONAL (Monthly) ── */
  .hp-price-card.professional {
    background: #0f172a;
    border: 1.5px solid #1e293b;
    box-shadow: 0 8px 40px rgba(15, 23, 42, 0.22);
  }

  .hp-price-card.professional:hover {
    box-shadow: 0 20px 60px rgba(15, 23, 42, 0.38) !important;
  }

  /* ── ENTERPRISE (API) ── */
  .hp-price-card.enterprise {
    background: linear-gradient(145deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    border: 1.5px solid rgba(139, 92, 246, 0.35);
    box-shadow: 0 8px 40px rgba(109, 40, 217, 0.18), 0 0 0 1px rgba(139,92,246,0.1);
  }

  .hp-price-card.enterprise:hover {
    box-shadow: 0 20px 60px rgba(109, 40, 217, 0.32), 0 0 0 1px rgba(139,92,246,0.2) !important;
  }

  /* shimmer lines on enterprise */
  .hp-price-card.enterprise::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(167, 139, 250, 0.6), transparent);
  }

  .hp-price-card.enterprise::after {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at 50% -20%, rgba(139, 92, 246, 0.12) 0%, transparent 65%);
    pointer-events: none;
  }

  /* ── PLAN BADGE ── */
  .hp-plan-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 100px;
    font-family: 'Outfit', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 28px;
    width: fit-content;
  }

  .starter .hp-plan-badge {
    background: #f1f5f9;
    color: #475569;
    border: 1px solid #e2e8f0;
  }

  .professional .hp-plan-badge {
    background: rgba(37, 99, 235, 0.15);
    color: #60a5fa;
    border: 1px solid rgba(37, 99, 235, 0.25);
  }

  .enterprise .hp-plan-badge {
    background: rgba(139, 92, 246, 0.18);
    color: #c4b5fd;
    border: 1px solid rgba(139, 92, 246, 0.3);
  }

  /* ── PLAN NAME ── */
  .hp-plan-name {
    font-family: 'Outfit', sans-serif;
    font-size: 1.45rem;
    font-weight: 800;
    margin: 0 0 6px 0;
    letter-spacing: -0.02em;
  }

  .starter .hp-plan-name { color: #0f172a; }
  .professional .hp-plan-name { color: #f1f5f9; }
  .enterprise .hp-plan-name { color: #ede9fe; }

  /* ── PLAN SUBTITLE ── */
  .hp-plan-sub {
    font-size: 0.88rem;
    margin: 0 0 32px 0;
    line-height: 1.5;
  }

  .starter .hp-plan-sub { color: #64748b; }
  .professional .hp-plan-sub { color: #64748b; }
  .enterprise .hp-plan-sub { color: #7c7fa3; }

  /* ── PRICE BLOCK ── */
  .hp-price-block {
    display: flex;
    align-items: baseline;
    gap: 4px;
    margin-bottom: 6px;
  }

  .hp-price-currency {
    font-family: 'Outfit', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    line-height: 1;
  }

  .starter .hp-price-currency { color: #475569; }
  .professional .hp-price-currency { color: #94a3b8; }
  .enterprise .hp-price-currency { color: #7c7fa3; }

  .hp-price-amount {
    font-family: 'Outfit', sans-serif;
    font-size: 3.4rem;
    font-weight: 900;
    line-height: 1;
    letter-spacing: -0.04em;
  }

  .starter .hp-price-amount { color: #0f172a; }
  .professional .hp-price-amount { color: #f8fafc; }
  .enterprise .hp-price-amount { color: #ede9fe; }

  .hp-price-unit {
    font-size: 0.85rem;
    font-weight: 500;
    margin-bottom: 4px;
  }

  .starter .hp-price-unit { color: #94a3b8; }
  .professional .hp-price-unit { color: #475569; }
  .enterprise .hp-price-unit { color: #5c5f7a; }

  /* ── DIVIDER ── */
  .hp-price-divider {
    height: 1px;
    margin: 28px 0;
  }

  .starter .hp-price-divider { background: #f1f5f9; }
  .professional .hp-price-divider { background: #1e293b; }
  .enterprise .hp-price-divider { background: rgba(139, 92, 246, 0.18); }

  /* ── FEATURE LIST ── */
  .hp-feature-list {
    list-style: none;
    padding: 0;
    margin: 0 0 36px 0;
    display: flex;
    flex-direction: column;
    gap: 13px;
    flex-grow: 1;
  }

  .hp-feature-list li {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    font-size: 0.91rem;
    line-height: 1.45;
    transition: none !important;
  }

  .starter .hp-feature-list li { color: #475569; }
  .professional .hp-feature-list li { color: #94a3b8; }
  .enterprise .hp-feature-list li { color: #7c7fa3; }

  .hp-feat-icon {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    flex-shrink: 0;
    margin-top: 1px;
    transition: none !important;
  }

  .starter .hp-feat-icon { background: #dcfce7; color: #16a34a; }
  .professional .hp-feat-icon { background: rgba(37,99,235,0.18); color: #60a5fa; }
  .enterprise .hp-feat-icon { background: rgba(139,92,246,0.2); color: #c4b5fd; }

  /* ── CTA BUTTON ── */
  .hp-price-cta {
    font-family: 'Outfit', sans-serif;
    font-size: 0.95rem;
    font-weight: 700;
    padding: 14px 28px;
    border-radius: 12px;
    border: none;
    cursor: pointer;
    width: 100%;
    text-align: center;
    letter-spacing: 0.01em;
    transition: opacity 0.2s, transform 0.2s !important;
  }

  .hp-price-cta:hover { opacity: 0.88; transform: none !important; }
  .hp-price-cta:active { transform: scale(0.98) !important; }

  .starter .hp-price-cta {
    background: #0f172a;
    color: #ffffff;
    box-shadow: 0 2px 8px rgba(15,23,42,0.15);
  }

  .professional .hp-price-cta {
    background: #2563eb;
    color: #ffffff;
    box-shadow: 0 4px 16px rgba(37,99,235,0.35);
  }

  .enterprise .hp-price-cta {
    background: linear-gradient(135deg, #7c3aed, #6d28d9);
    color: #ffffff;
    box-shadow: 0 4px 20px rgba(109,40,217,0.4);
    cursor: not-allowed;
    opacity: 0.75;
  }

  /* popular chip on professional card */
  .hp-popular-chip {
    position: absolute;
    top: 24px;
    right: 24px;
    background: #2563eb;
    color: #ffffff;
    font-family: 'Outfit', sans-serif;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 4px 10px;
    border-radius: 100px;
  }

  /* ── COMING SOON RIBBON on enterprise ── */
  .hp-coming-soon-ribbon {
    position: absolute;
    top: 20px;
    right: -32px;
    background: linear-gradient(135deg, #7c3aed, #a78bfa);
    color: #ffffff;
    font-family: 'Outfit', sans-serif;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 5px 42px;
    transform: rotate(35deg);
    box-shadow: 0 2px 8px rgba(109,40,217,0.35);
  }

  /* capacity note */
  .hp-capacity-note {
    font-size: 0.78rem;
    margin: 8px 0 0 0;
    font-style: italic;
  }

  .starter .hp-capacity-note { color: #94a3b8; }
  .professional .hp-capacity-note { color: #475569; }
  .enterprise .hp-capacity-note { color: #5c5f7a; }

  /* ── Media Engine Viewports ── */
  @media (max-width: 1200px) {
    .hp-blueprint-deck { grid-template-columns: repeat(2, 1fr); }
  }

  @media (max-width: 1120px) {
    .hp-hero-title-group h1 { font-size: 3.2rem; }
    .hp-trio-layout { grid-template-columns: repeat(2, 1fr); }
    .hp-console-split { grid-template-columns: 1fr; }
    .hp-console-menu { flex-direction: row; overflow-x: auto; padding-bottom: 6px; }
    .hp-console-item { white-space: nowrap; }
    .hp-console-arrow { display: none; }
    .hp-pricing-grid { grid-template-columns: 1fr; max-width: 480px; margin: 0 auto; }
  }

  @media (max-width: 700px) {
    .hp-trio-layout { grid-template-columns: 1fr; }
    .hp-blueprint-deck { grid-template-columns: 1fr; }
    .hp-hero-title-group h1 { font-size: 2.4rem; }
    .hp-hero-input-bar { border-radius: 20px; flex-direction: column; padding: 16px; gap: 12px; }
    .hp-input-bar-btn { width: 100%; border-radius: 12px; }
    .hp-wrapper { padding: 16px; }
    .hp-price-card { padding: 32px 28px 28px; }
  }
`

export default function HomePage({ isGuest = true, onStartApp }) {
  const [activeTab, setActiveTab] = useState('gender')

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

  const modulesData = {
    gender: {
      title: "Gender Imbalance Framework",
      framework: "Statutory Labor Equity Standards & Equal Opportunity Directives",
      rule: "Evaluates pipeline retention rates across technical filters to identify potential drop-off anomalies between applicant tiers.",
      flag: "🚨 PIPELINE METRIC RISK ALERT [V3-GENDER]: Recruitment process speed markers reflect variation outside standard pipeline constraints.",
      vars: ["gender", "shortlisted", "hired"]
    },
    caste: {
      title: "Regional Parity Framework",
      framework: "Constitutional Safety Directives & Regional Diversity Mandates",
      rule: "Cross-checks pipeline onboarding matrices against local structural availability indicators to flag distribution risks.",
      flag: "🚨 SPECIFIC THRESHOLD EXCEEDED [V3-REGIONAL]: Sourcing pipeline analysis registers deviation parameters within local structural layers.",
      vars: ["caste_category", "shortlisted", "hired"]
    },
    disability: {
      title: "Accessibility Guard Matrix",
      framework: "Universal Adaptive Recruitment Statutes & Equal Access Laws",
      rule: "Monitors candidate progression markers across adaptive interview setups to isolate potential software access friction points.",
      flag: "🚨 FUNNEL ADVANCEMENT RISK [V3-ACCESSIBILITY]: Sub-funnel velocity tracks exhibit drop-off lines relative to baseline processing speeds.",
      vars: ["disability_status", "shortlisted", "hired"]
    },
    skin: {
      title: "Appearance Variable Guard",
      framework: "Global Anti-Bias Codes & Enterprise Representation Rules",
      rule: "Scans data paths to protect against unconscious profile filtering tendencies during remote digital evaluation cycles.",
      flag: "🚨 INSULATION REJECTION FLAG [V3-APPEARANCE]: Evaluation system registers drop-off signals linking pipeline retention to phenotype indices.",
      vars: ["skin_tone_group", "shortlisted", "hired"]
    },
    proxy: {
      title: "Indirect Correlation Scan",
      framework: "Hidden Dependency Insulation & Core Integrity Frameworks",
      rule: "Examines secondary features (such as residential zone codes or high school categories) that replicate restricted demographic patterns.",
      flag: "🚨 INDIRECT MATCH IDENTIFIED [V3-PROXY]: Secondary environmental fields exhibit unexpected alignment loops with profile variables.",
      vars: ["postal_code", "location_category", "hired"]
    },
    spg: {
      title: "Multi-Gate Process Tracker",
      framework: "Comprehensive Funnel Lifecycle Safety Regulations",
      rule: "Breaks down conversion indices across multi-phase testing systems to isolate the specific gate where process balance spikes.",
      flag: "🚨 GATED RETENTION ANOMALY [V3-FUNNEL]: Technical interview phase markers demonstrate unproportional screening metrics.",
      vars: ["assessment_score", "interview_status", "hired"]
    },
    institution: {
      title: "Sourcing Insularity Scan",
      framework: "Anti-Elitism Benchmarks & Open Talent Network Protocols",
      rule: "Measures systemic dependency trends over localized university tiers to track reliance indicators on closed legacy channels.",
      flag: "🚨 TRACKING CONCENTRATION ALERT [V3-INSTITUTION]: Talent conversion pipelines indicate high dependency on a narrow band of university sets.",
      vars: ["university_tier", "source_channel", "hired"]
    },
    marital: {
      title: "Intersectional Layer Scan",
      framework: "Multi-Category Safety Matrix & Demography Protection Rules",
      rule: "Combines overlapping candidate variables to identify hidden process drop-offs masked by high-level raw averages.",
      flag: "🚨 BLENDED INDEX ANOMALY [V3-INTERSECTIONAL]: Cross-category validation highlights process gaps within specific combined applicant profiles.",
      vars: ["marital_status", "gender", "hired"]
    },
    age: {
      title: "Age Demographics Matrix",
      framework: "Universal Career Protection Directives & Lifecycle Safety Laws",
      rule: "Validates intake streams to verify experienced, mid-career, and junior candidate brackets experience matching evaluation gates.",
      flag: "🚨 GENERATIONAL VARIANCE DETECTED [V3-AGE]: Funnel progression records show processing differences across candidate age brackets.",
      vars: ["age_bracket", "dob", "hired"]
    },
    referral: {
      title: "Network Concentration Guard",
      framework: "Corporate Transparency Standards & Anti-Nepotism Rules",
      rule: "Measures candidate source networks against standard open-market entries to isolate sourcing monopolization patterns.",
      flag: "🚨 MONOPOLY CAPTURE RECORDED [V3-NETWORKS]: Internal employee referral channels cross maximum structural balance benchmarks.",
      vars: ["referral_source", "application_mode", "hired"]
    }
  }

  const currentModule = modulesData[activeTab] || modulesData.gender

  return (
    <div className="hp-wrapper">
      <div className="hp-container">
        
        {/* ── SECTION A: MINIMAL CENTERED HERO SECTION ── */}
        <section className="hp-template-hero">
          <div className="hp-badge-pill">
            ⚖️ PLATFORM LOGS SECURED v2.0
          </div>
          <div className="hp-hero-title-group">
            <h1>
              Audit Selection Logs for <span>Systemic Risk</span>
            </h1>
          </div>
          <p className="hp-hero-description">
            Securely map corporate recruitment pipelines to evaluate process outcomes, analyze conversion metrics against global frameworks, and protect institutional integrity.
          </p>
          
          <div className="hp-hero-input-bar">
            <input 
              type="text" 
              placeholder="Enter compliance parameter or vector to scan..." 
              disabled 
              value="System Sandbox Workspace Environment Active"
            />
            <button className="hp-input-bar-btn" onClick={onStartApp}>
              {isGuest ? '🚀 Open Workspace' : '📤 Ingest CSV'}
            </button>
          </div>

          <div className="hp-hero-actions">
            <button 
              className="hp-btn-outline-dark"
              onClick={() => document.getElementById('compliance-console').scrollIntoView({ behavior: 'smooth' })}
            >
              View Active Benchmarks
            </button>
          </div>
        </section>

        {/* ── SECTION B: CORE SAFEGUARDS IN TEMPLATE CARD SCHEME ── */}
        <section className="hp-section-wrapper">
          <div className="hp-centered-title">
            <h2>Core Safeguards</h2>
            <p>Three architectural validation frames checking process pipeline configurations.</p>
          </div>
          <div className="hp-trio-layout">
            
            {/* BOX 1: Global Integrity Scale */}
            <div className="hp-feature-node">
              <div className="hp-icon-housing blue-badge">📊</div>
              <h3>Global Integrity Scale</h3>
              <p>Provides an enterprise 0–100 process score displaying structural pipeline health, with penalty deductions built-in for critical gate imbalances.</p>
            </div>

            {/* BOX 2: Framework Cross-Checks */}
            <div className="hp-feature-node">
              <div className="hp-icon-housing emerald-badge">🛡️</div>
              <h3>Framework Cross-Checks</h3>
              <p>Maintains runtime checking models mapping hiring steps against constitutional mandates, regional guidelines, and organizational safety metrics.</p>
            </div>

            {/* BOX 3: Anomaly Filter Layers */}
            <div className="hp-feature-node">
              <div className="hp-icon-housing purple-badge">🧹</div>
              <h3>Anomaly Filter Layers</h3>
              <p>Utilizes custom data sanitization filters to bypass temporary background anomalies, ensuring only genuine operational risks trip alert logs.</p>
            </div>

          </div>
        </section>

        {/* ── SECTION C: INTERACTIVE RISK CONSOLE ── */}
        <section id="compliance-console" className="hp-glass-mainframe">
          <div className="hp-centered-title" style={{ textAlign: 'left' }}>
            <h2>Risk Parameter Console</h2>
            <p>Select a monitoring vector to verify its underlying framework requirements, system tracking logic, and target indicators.</p>
          </div>

          <div className="hp-console-split">
            <div className="hp-console-menu">
              {Object.keys(modulesData).map((key) => (
                <button
                  key={key}
                  className={`hp-console-item ${activeTab === key ? 'is-selected' : ''}`}
                  onClick={() => setActiveTab(key)}
                >
                  <span>{key === 'spg' ? 'multi-stage funnel' : key.replace('_', ' ')}</span>
                  <span className="hp-console-arrow">➔</span>
                </button>
              ))}
            </div>

            <div className="hp-view-surface">
              <div className="hp-surface-group">
                <h4>{currentModule.title}</h4>
                <p className="hp-surface-body" style={{ fontWeight: 600, color: '#0f172a' }}>
                  {currentModule.framework}
                </p>
              </div>

              <div className="hp-surface-group">
                <h4>Platform Evaluation Parameter</h4>
                <p className="hp-surface-body" style={{ color: '#475569', fontSize: '0.98rem' }}>{currentModule.rule}</p>
              </div>

              <div className="hp-surface-group">
                <h4>Simulated Warning Output Log</h4>
                <div className="hp-log-banner">
                  <span>⚠️</span>
                  <div>{currentModule.flag}</div>
                </div>
              </div>

              <div className="hp-surface-group">
                <h4>Active Schema Keys</h4>
                <div className="hp-token-wrap">
                  {currentModule.vars.map((v, idx) => (
                    <span key={idx} className="hp-token-node">{v}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── SECTION D: BLUEPRINT LAYOUT DECK ── */}
        <section className="hp-glass-mainframe" style={{ background: '#f8fafc' }}>
          <div className="hp-centered-title" style={{ textAlign: 'left', marginBottom: '24px' }}>
            <h2 style={{ fontSize: '1.65rem' }}>Infrastructure Matrix</h2>
            <p>Decoupled processing layers handling dynamic validation pipelines securely.</p>
          </div>
          <div className="hp-blueprint-deck">
            
            {/* NODE 1 */}
            <div className="hp-blueprint-node" style={{ background: '#ffffff' }}>
              <div className="hp-blueprint-img-frame">
                <div style={{ width: '100%', height: '120px', background: '#f1f5f9', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <i className="ti ti-filter" style={{ fontSize: '32px', color: '#94a3b8' }} />
                </div>
              </div>
              <h4>Sanitization Core</h4>
              <p>Optimized data processing tasks parsing tabular data arrays for record cleaning and field mapping.</p>
            </div>

            {/* NODE 2 */}
            <div className="hp-blueprint-node" style={{ background: '#ffffff' }}>
              <div className="hp-blueprint-img-frame">
                <div style={{ width: '100%', height: '120px', background: '#f1f5f9', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <i className="ti ti-api" style={{ fontSize: '32px', color: '#94a3b8' }} />
                </div>
              </div>
              <h4>Secure Core API</h4>
              <p>Asynchronous service network routing system validations while running isolated PDF documentation builders.</p>
            </div>

            {/* NODE 3 */}
            <div className="hp-blueprint-node" style={{ background: '#ffffff' }}>
              <div className="hp-blueprint-img-frame">
                <div style={{ width: '100%', height: '120px', background: '#f1f5f9', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <i className="ti ti-layout-dashboard" style={{ fontSize: '32px', color: '#94a3b8' }} />
                </div>
              </div>
              <h4>Client Interface</h4>
              <p>Lightweight single-page environment executing responsive layout updates and clean workspace states.</p>
            </div>

            {/* NODE 4 */}
            <div className="hp-blueprint-node" style={{ background: '#ffffff' }}>
              <div className="hp-blueprint-img-frame">
                <div style={{ width: '100%', height: '120px', background: '#f1f5f9', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <i className="ti ti-database" style={{ fontSize: '32px', color: '#94a3b8' }} />
                </div>
              </div>
              <h4>Encrypted Ledger</h4>
              <p>Relational storage layers deployed to record pattern updates and secure historical continuity logs cleanly.</p>
            </div>

          </div>
        </section>

        {/* ── SECTION E: MATURED SCHEMATIC GRID MATRIX ── */}
        <section className="hp-section-wrapper">
          <div className="hp-centered-title" style={{ textAlign: 'left' }}>
            <h2>Production Data Ingestion Specifications</h2>
            <p>Developer blueprint outlining header criteria requirements prior to running system pipeline scanning.</p>
          </div>
          <div className="hp-table-frame">
            <table className="hp-schematic-grid">
              <thead>
                <tr>
                  <th>Field Code</th>
                  <th>Requirement Status</th>
                  <th>Accepted Value Formats</th>
                  <th>Operational Description</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>gender</strong></td>
                  <td><span className="hp-badge-critical">Required Field</span></td>
                  <td><span className="hp-code-inline">Male</span>, <span className="hp-code-inline">Female</span>, <span className="hp-code-inline">Non-binary</span></td>
                  <td>Monitors foundational pipeline demographic distribution metrics across system gates.</td>
                </tr>
                <tr>
                  <td><strong>shortlisted</strong></td>
                  <td><span className="hp-badge-critical">Required Field</span></td>
                  <td><span className="hp-code-inline">0</span> (No) or <span className="hp-code-inline">1</span> (Yes)</td>
                  <td>Measures process conversion velocities post early-stage screening phases.</td>
                </tr>
                <tr>
                  <td><strong>hired</strong></td>
                  <td><span className="hp-badge-critical">Required Field</span></td>
                  <td><span className="hp-code-inline">0</span> (No) or <span className="hp-code-inline">1</span> (Yes)</td>
                  <td>Tracks total process conversion status relative to the original source distribution.</td>
                </tr>
                <tr>
                  <td><strong>disability_status</strong></td>
                  <td><span className="hp-badge-secondary">Optional Key</span></td>
                  <td><span className="hp-code-inline">Yes</span>, <span className="hp-code-inline">No</span></td>
                  <td>Supplies accessibility metrics tracking parameter equality across system software gates.</td>
                </tr>
                <tr>
                  <td><span className="hp-code-inline">caste</span> or <span className="hp-code-inline">category</span> or <span className="hp-code-inline">social_group</span></td>
                  <td><span className="hp-badge-secondary">Optional Key</span></td>
                  <td>Alphanumeric system classification labels</td>
                  <td>Checks pipeline alignment indices with respect to local statutory inclusion mandates.</td>
                </tr>
                <tr>
                  <td><span className="hp-code-inline">skin_colour</span> or <span className="hp-code-inline">skin_tone</span></td>
                  <td><span className="hp-badge-secondary">Optional Key</span></td>
                  <td>Integers representing color balance sets</td>
                  <td>Alerts system administrators to subtle cosmetic profile imbalances during interview loops.</td>
                </tr>
                <tr>
                  <td><strong>referral</strong></td>
                  <td><span className="hp-badge-secondary">Optional Key</span></td>
                  <td>Source path identifiers (e.g., Agency, Internal)</td>
                  <td>Guards channels from network isolation profiles and sourcing monopolization trends.</td>
                </tr>
                <tr>
                  <td><strong>marital_status</strong></td>
                  <td><span className="hp-badge-secondary">Optional Key</span></td>
                  <td><span className="hp-code-inline">Single</span>, <span className="hp-code-inline">Married</span>, <span className="hp-code-inline">Divorced</span></td>
                  <td>Triggers advanced intersectional filters to capture multi-layered processing drop-offs.</td>
                </tr>
                <tr>
                  <td><strong>institution</strong></td>
                  <td><span className="hp-badge-secondary">Optional Key</span></td>
                  <td>Alphanumeric tags matching university keys</td>
                  <td>Monitors institution concentration metrics to maintain open sourcing channels.</td>
                </tr>
                <tr>
                  <td><strong>age / dob</strong></td>
                  <td><span className="hp-badge-secondary">Optional Key</span></td>
                  <td>Valid age integers or date structures</td>
                  <td>Evaluates talent lifecycle trajectories to guarantee equity across all active generational blocks.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* ── SECTION F: PRICING CARDS ── */}
        <section className="hp-pricing-section">
          <div className="hp-pricing-header">
            <h2>Simple, Transparent Pricing</h2>
            <p>One-time audits or ongoing compliance monitoring — pick what fits your organisation.</p>
          </div>

          <div className="hp-pricing-grid">

            {/* ── STARTER: Per-Audit ── */}
            <div className="hp-price-card starter">
              <div className="hp-plan-badge">📋 Starter</div>
              <h3 className="hp-plan-name">Audit Report</h3>
              <p className="hp-plan-sub">Single-run deep audit with a full PDF compliance report.</p>

              <div className="hp-price-block">
                <span className="hp-price-currency">₹</span>
                <span className="hp-price-amount">25K</span>
              </div>
              <p className="hp-price-unit">per audit / roll</p>
              <p className="hp-capacity-note">Up to 500 employees</p>

              <div className="hp-price-divider" />

              <ul className="hp-feature-list">
                <li><span className="hp-feat-icon">✓</span>10+ bias detection modules</li>
                <li><span className="hp-feat-icon">✓</span>Full PDF audit report</li>
                <li><span className="hp-feat-icon">✓</span>Gender, caste, disability, skin tone</li>
                <li><span className="hp-feat-icon">✓</span>Referral &amp; institution analysis</li>
                <li><span className="hp-feat-icon">✓</span>Flag-level remediation notes</li>
              </ul>

              <button className="hp-price-cta" onClick={onStartApp}>
                Start Free Audit →
              </button>
            </div>

            {/* ── PROFESSIONAL: Monthly ── */}
            <div className="hp-price-card professional">
              <div className="hp-popular-chip">Most Popular</div>
              <div className="hp-plan-badge">🏢 Professional</div>
              <h3 className="hp-plan-name">Monthly Plan</h3>
              <p className="hp-plan-sub">Continuous compliance monitoring with full data exports.</p>

              <div className="hp-price-block">
                <span className="hp-price-currency">₹</span>
                <span className="hp-price-amount">68K</span>
              </div>
              <p className="hp-price-unit">per month</p>
              <p className="hp-capacity-note">Up to 5,000 employees</p>

              <div className="hp-price-divider" />

              <ul className="hp-feature-list">
                <li><span className="hp-feat-icon">✓</span>Everything in Starter</li>
                <li><span className="hp-feat-icon">✓</span>Unlimited monthly audits</li>
                <li><span className="hp-feat-icon">✓</span>JSON data export included</li>
                <li><span className="hp-feat-icon">✓</span>Trend tracking over time</li>
                <li><span className="hp-feat-icon">✓</span>Priority support &amp; SLA</li>
                <li><span className="hp-feat-icon">✓</span>Multi-role team access</li>
              </ul>

              <button className="hp-price-cta" onClick={onStartApp}>
                Get Monthly Access →
              </button>
            </div>

            {/* ── ENTERPRISE: API (Coming Soon) ── */}
            <div className="hp-price-card enterprise">
              <div className="hp-coming-soon-ribbon">Coming Soon</div>
              <div className="hp-plan-badge">⚡ Enterprise</div>
              <h3 className="hp-plan-name">API Access</h3>
              <p className="hp-plan-sub">Programmatic integration for custom pipelines and internal tooling.</p>

              <div className="hp-price-block">
                <span className="hp-price-currency">₹</span>
                <span className="hp-price-amount">1.5L</span>
              </div>
              <p className="hp-price-unit">per month</p>
              <p className="hp-capacity-note">1M token context window</p>

              <div className="hp-price-divider" />

              <ul className="hp-feature-list">
                <li><span className="hp-feat-icon">✓</span>Everything in Professional</li>
                <li><span className="hp-feat-icon">✓</span>Dedicated API keys</li>
                <li><span className="hp-feat-icon">✓</span>1M token processing limit</li>
                <li><span className="hp-feat-icon">✓</span>Webhook &amp; HRMS integration</li>
                <li><span className="hp-feat-icon">✓</span>Custom module configuration</li>
                <li><span className="hp-feat-icon">✓</span>Dedicated account manager</li>
              </ul>

              <button className="hp-price-cta" disabled>
                Notify Me on Launch
              </button>
            </div>

          </div>
        </section>

      </div>
    </div>
  )
}
