import React, { useState, useEffect } from 'react'
import { authFetch } from './authUtils'
import { GaugeChart, MetricCard, FlagFeed } from './ChartHelpers'
import { GenderModule, DisabilityModule, InstitutionModule, AgeModule, CasteModule } from './CoreModules'
import { SkinModule, ReferralModule, MaritalModule, ProxyModule } from './AdvancedModules'
import { Bar, Radar } from 'react-chartjs-2'
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement,
  ArcElement, RadialLinearScale, PointElement, LineElement,
  Filler, Title, Tooltip, Legend
} from 'chart.js'
import annotationPlugin from 'chartjs-plugin-annotation'

ChartJS.register(
  CategoryScale, LinearScale, BarElement, ArcElement,
  RadialLinearScale, PointElement, LineElement, Filler,
  Title, Tooltip, Legend, annotationPlugin
)

/* ─────────────────────────────────────────
   DESIGN SYSTEM — BankDash Premium Light
───────────────────────────────────────── */
const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&family=Instrument+Serif:ital@0;1&display=swap');

  :root {
    --canvas:          #F5F7FA;
    --canvas-2:        #EEF2F8;
    --white:           #FFFFFF;
    --indigo:          #2D60FF;
    --indigo-deep:     #1814F3;
    --indigo-soft:     rgba(45,96,255,0.08);
    --indigo-mid:      rgba(45,96,255,0.15);
    --text-h:          #1A202C;
    --text-card:       #2B3674;
    --text-body:       #344054;
    --text-muted:      #718096;
    --text-faint:      #A0AEC0;
    --border:          #E4E7EC;
    --emerald:         #12B76A;
    --emerald-bg:      #ECFDF5;
    --emerald-bd:      #A6F4C5;
    --amber:           #F79009;
    --amber-bg:        #FFFAEB;
    --amber-bd:        #FEDF89;
    --rose:            #F04438;
    --rose-bg:         #FEF3F2;
    --rose-bd:         #FECDCA;
    --blue-bg:         #EFF6FF;
    --blue-bd:         #BFDBFE;
    --card-shadow:     0px 4px 25px rgba(142,161,201,0.10);
    --card-shadow-h:   0px 10px 40px rgba(142,161,201,0.18);
    --r-card:          20px;
    --r-sm:            10px;
    --r-pill:          100px;
    --font:            'Plus Jakarta Sans', sans-serif;
    --font-serif:      'Instrument Serif', serif;
    --ease:            cubic-bezier(0.22,1,0.36,1);
    --t:               0.22s;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  .bd {
    font-family: var(--font);
    background: var(--canvas);
    color: var(--text-body);
    min-height: 100vh;
    padding-bottom: 72px;
  }

  /* ── Topbar ── */
  .bd-top {
    background: var(--white);
    border-bottom: 1px solid rgba(0,0,0,0.055);
    padding: 0 32px;
    display: flex; align-items: center;
    justify-content: space-between;
    height: 66px;
    position: sticky; top: 0; z-index: 100;
    gap: 16px;
  }

  .bd-brand {
    display: flex; align-items: center; gap: 10px; flex-shrink: 0;
  }

  .bd-brand-logo {
    width: 36px; height: 36px; border-radius: 10px;
    background: linear-gradient(135deg, #2D60FF 0%, #1814F3 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 17px;
    box-shadow: 0 4px 14px rgba(45,96,255,0.32);
  }

  .bd-brand-name {
    font-size: 1.05rem; font-weight: 800; letter-spacing: -0.025em;
    color: var(--text-h);
  }
  .bd-brand-name span { color: var(--indigo); }

  .bd-file-chip {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--canvas); border: 1px solid var(--border);
    border-radius: var(--r-pill); padding: 5px 14px;
    font-size: 0.77rem; color: var(--text-muted); font-weight: 500;
    white-space: nowrap;
  }

  .bd-top-right { display: flex; gap: 10px; align-items: center; }

  /* ── Buttons ── */
  .btn {
    display: inline-flex; align-items: center; gap: 7px;
    font-family: var(--font); font-size: 0.82rem; font-weight: 600;
    padding: 10px 20px; border-radius: var(--r-sm);
    border: none; cursor: pointer;
    transition: all var(--t) var(--ease);
    white-space: nowrap; letter-spacing: -0.01em;
    position: relative; overflow: hidden;
  }

  .btn-primary {
    background: var(--indigo); color: #fff;
    box-shadow: 0 4px 14px rgba(45,96,255,0.30);
  }
  .btn-primary:hover {
    background: var(--indigo-deep);
    box-shadow: 0 6px 22px rgba(45,96,255,0.42);
    transform: translateY(-1px);
  }
  .btn-primary:active { transform: none; box-shadow: none; }

  .btn-outline {
    background: var(--white); color: var(--text-body);
    border: 1.5px solid var(--border);
  }
  .btn-outline:hover {
    background: var(--canvas); border-color: #CBD5E1;
    transform: translateY(-1px);
  }

  .btn-success {
    background: var(--emerald) !important;
    box-shadow: 0 4px 14px rgba(18,183,106,0.28) !important;
  }
  .btn-loading { opacity: 0.6; pointer-events: none; }
  .spin { display: inline-block; animation: spin 0.7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Tab bar ── */
  .bd-tabs {
    background: var(--white);
    border-bottom: 1px solid rgba(0,0,0,0.055);
    padding: 0 32px;
    display: flex; align-items: flex-end;
    gap: 0; overflow-x: auto; scrollbar-width: none;
  }
  .bd-tabs::-webkit-scrollbar { display: none; }

  .bd-tab {
    font-family: var(--font); font-size: 0.81rem; font-weight: 600;
    color: var(--text-muted);
    padding: 16px 18px 14px;
    border: none; background: transparent; cursor: pointer;
    white-space: nowrap;
    border-bottom: 2.5px solid transparent;
    transition: all var(--t) var(--ease);
    letter-spacing: -0.01em;
    position: relative; top: 1px;
  }
  .bd-tab:hover { color: var(--text-card); }
  .bd-tab.is-active {
    color: var(--indigo);
    border-bottom-color: var(--indigo);
  }

  /* ── Page body ── */
  .bd-body { padding: 28px 32px; }

  .bd-page-head {
    display: flex; align-items: flex-start;
    justify-content: space-between; gap: 20px;
    margin-bottom: 24px;
  }
  .bd-page-head h1 {
    font-size: 1.45rem; font-weight: 800; color: var(--text-h);
    letter-spacing: -0.03em; line-height: 1.2;
  }
  .bd-page-head h1 em {
    font-family: var(--font-serif); font-style: italic;
    color: var(--indigo);
  }
  .bd-page-head-sub {
    font-size: 0.79rem; color: var(--text-muted); margin-top: 4px;
  }

  /* ── Card ── */
  .bd-card {
    background: var(--white);
    border-radius: var(--r-card);
    box-shadow: var(--card-shadow);
    padding: 24px;
    transition: box-shadow var(--t) var(--ease), transform var(--t) var(--ease);
  }
  .bd-card:hover {
    box-shadow: var(--card-shadow-h);
    transform: translateY(-1px);
  }

  .bd-card-hd {
    display: flex; align-items: flex-start;
    justify-content: space-between; margin-bottom: 8px;
  }
  .bd-card-title {
    font-size: 1rem; font-weight: 700; color: var(--text-card);
    letter-spacing: -0.02em;
  }
  .bd-card-sub {
    font-size: 0.74rem; color: var(--text-muted); margin-top: 2px;
  }
  .bd-divider { height: 1px; background: #EEF2F8; margin: 16px 0 20px; }

  /* ── Grids ── */
  .bd-g4 {
    display: grid; grid-template-columns: repeat(4,1fr);
    gap: 18px; margin-bottom: 22px;
  }
  .bd-g2 {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 18px; margin-bottom: 22px;
  }

  /* ── Summary widget ── */
  .bd-widget {
    background: var(--white);
    border-radius: var(--r-card);
    box-shadow: var(--card-shadow);
    padding: 22px 22px 20px;
    display: flex; flex-direction: column; gap: 14px;
    transition: all var(--t) var(--ease);
    animation: fadeUp 0.38s var(--ease) both;
  }
  .bd-widget:hover {
    box-shadow: var(--card-shadow-h);
    transform: translateY(-2px);
  }

  .bd-widget-top {
    display: flex; align-items: flex-start;
    justify-content: space-between;
  }

  .bd-widget-icon {
    width: 42px; height: 42px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }
  .wi-pass { background: var(--emerald-bg); }
  .wi-warn { background: var(--amber-bg); }
  .wi-fail { background: var(--rose-bg); }
  .wi-blue { background: var(--blue-bg); }

  .bd-widget-label {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.05em;
    text-transform: uppercase; color: var(--text-muted);
    margin-bottom: 6px;
  }
  .bd-widget-value {
    font-size: 1.95rem; font-weight: 800; letter-spacing: -0.04em;
    line-height: 1; color: var(--text-h);
  }
  .bd-widget.wv-pass .bd-widget-value { color: var(--emerald); }
  .bd-widget.wv-warn .bd-widget-value { color: var(--amber); }
  .bd-widget.wv-fail .bd-widget-value { color: var(--rose); }
  .bd-widget.wv-blue .bd-widget-value { color: var(--indigo); }

  .bd-widget-footer {
    border-top: 1px solid var(--canvas-2);
    padding-top: 12px;
    font-size: 0.73rem; color: var(--text-muted); font-weight: 500;
  }

  /* ── Pill ── */
  .bd-pill {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 4px 11px; border-radius: var(--r-pill);
    font-size: 0.70rem; font-weight: 700; letter-spacing: 0.03em;
    text-transform: uppercase;
  }
  .pp-pass { background: var(--emerald-bg); color: var(--emerald); border: 1px solid var(--emerald-bd); }
  .pp-warn { background: var(--amber-bg);   color: var(--amber);   border: 1px solid var(--amber-bd); }
  .pp-fail { background: var(--rose-bg);    color: var(--rose);    border: 1px solid var(--rose-bd); }
  .pp-blue { background: var(--blue-bg);    color: var(--indigo);  border: 1px solid var(--blue-bd); }
  .bd-pill-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: currentColor; flex-shrink: 0;
  }

  /* ── AIR chips ── */
  .bd-air-row { display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; }
  .bd-air-chip {
    flex: 1; min-width: 75px; padding: 11px 13px;
    border-radius: var(--r-sm); border: 1.5px solid;
    transition: transform var(--t) var(--ease);
  }
  .bd-air-chip:hover { transform: translateY(-1px); }
  .ac-pass { background: var(--emerald-bg); border-color: var(--emerald-bd); }
  .ac-fail { background: var(--rose-bg);    border-color: var(--rose-bd); }
  .bd-air-label {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.06em;
    text-transform: uppercase; color: var(--text-muted); margin-bottom: 5px;
  }
  .bd-air-val {
    font-size: 1.1rem; font-weight: 800; letter-spacing: -0.03em;
  }
  .ac-pass .bd-air-val { color: var(--emerald); }
  .ac-fail .bd-air-val { color: var(--rose); }

  /* ── Chart ── */
  .bd-chart { height: 250px; position: relative; }

  /* ── Flag feed ── */
  .bd-flag-panel { animation: fadeUp 0.38s var(--ease) 0.22s both; }
  .bd-flag-hd {
    display: flex; align-items: center; justify-content: space-between;
    cursor: pointer; user-select: none; margin-bottom: 6px;
  }
  .bd-flag-hd-l { display: flex; align-items: center; gap: 10px; }

  .bd-flag-toggle {
    font-size: 0.73rem; color: var(--indigo); font-weight: 600;
    background: var(--indigo-soft); border: none; cursor: pointer;
    border-radius: var(--r-pill); padding: 4px 12px;
    transition: background var(--t);
  }
  .bd-flag-toggle:hover { background: var(--indigo-mid); }

  .bd-flag-list { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; }

  .bd-flag-item {
    display: flex; align-items: flex-start; gap: 11px;
    padding: 12px 16px; border-radius: var(--r-sm);
    background: var(--canvas); border: 1.5px solid #F2F4F7;
    transition: all var(--t) var(--ease);
    animation: fadeUp 0.3s var(--ease) both;
  }
  .bd-flag-item:hover {
    background: var(--white); border-color: #CBD5E1;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    transform: translateX(2px);
  }
  .bd-flag-critical {
    background: var(--rose-bg); border-color: var(--rose-bd);
    animation: fadeUp 0.3s var(--ease) both, flagPulse 3s ease-in-out infinite;
  }
  .bd-flag-critical:hover {
    background: #fff1f0; border-color: var(--rose);
  }
  @keyframes flagPulse {
    0%,100% { box-shadow: 0 0 0 0 rgba(240,68,56,0); }
    50%      { box-shadow: 0 0 0 3px rgba(240,68,56,0.12); }
  }
  .bd-flag-dot {
    width: 7px; height: 7px; border-radius: 50%;
    margin-top: 5px; flex-shrink: 0;
  }
  .bd-flag-text { font-size: 0.81rem; color: var(--text-body); line-height: 1.6; }
  .bd-flag-critical .bd-flag-text { color: var(--rose); }

  /* ── Animations ── */
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .bd-tab-view { animation: fadeUp 0.32s var(--ease) both; }

  .d0 { animation-delay: 0.04s; }
  .d1 { animation-delay: 0.09s; }
  .d2 { animation-delay: 0.14s; }
  .d3 { animation-delay: 0.19s; }
  .d4 { animation-delay: 0.25s; }

  /* ── Responsive ── */
  @media (max-width: 1024px) {
    .bd-g4 { grid-template-columns: 1fr 1fr; }
  }
  @media (max-width: 768px) {
    .bd-top { padding: 14px 20px; height: auto; flex-wrap: wrap; }
    .bd-tabs { padding: 0 20px; }
    .bd-body { padding: 20px; }
    .bd-g4  { grid-template-columns: 1fr 1fr; gap: 14px; }
    .bd-g2  { grid-template-columns: 1fr; }
    .bd-page-head { flex-direction: column; }
    .bd-top-right { width: 100%; }
    .btn { flex: 1; justify-content: center; }
  }
  @media (max-width: 480px) {
    .bd-g4 { grid-template-columns: 1fr; }
  }
`

function StyleInjector() {
  useEffect(() => {
    const id = 'bd-v2'
    if (!document.getElementById(id)) {
      const el = document.createElement('style')
      el.id = id; el.textContent = STYLES
      document.head.appendChild(el)
    }
  }, [])
  return null
}

/* ─── Export button with state ─── */
function ExportBtn({ label, icon, onClick, onError, variant = 'primary' }) {
  const [st, setSt] = useState('idle')
  const handle = async () => {
    setSt('loading')
    try { await onClick(); setSt('success'); setTimeout(() => setSt('idle'), 2400) }
    catch (err) { setSt('idle'); onError?.(err.message || 'Download failed') }
  }
  const ico = st === 'loading' ? <span className="spin">⟳</span>
    : st === 'success' ? '✓' : icon
  return (
    <button
      className={`btn btn-${variant} ${st === 'loading' ? 'btn-loading' : ''} ${st === 'success' ? 'btn-success' : ''}`}
      onClick={handle}
    >
      {ico}
      {st === 'loading' ? 'Generating…' : st === 'success' ? 'Done!' : label}
    </button>
  )
}

/* ─── Summary widget ─── */
function Widget({ label, value, icon, variant = 'blue', sub, delay = 0 }) {
  const iconCls = `bd-widget-icon wi-${variant}`
  const pillCls = `bd-pill pp-${variant === 'blue' ? 'blue' : variant}`
  const pillTxt = variant === 'pass' ? 'Good' : variant === 'warn' ? 'Watch' : variant === 'fail' ? 'Risk' : 'Info'
  return (
    <div className={`bd-widget wv-${variant}`} style={{ animationDelay: `${delay}s` }}>
      <div className="bd-widget-top">
        <div className={iconCls}>{icon}</div>
        <span className={pillCls}><span className="bd-pill-dot" />{pillTxt}</span>
      </div>
      <div>
        <div className="bd-widget-label">{label}</div>
        <div className="bd-widget-value">{value}</div>
      </div>
      {sub && <div className="bd-widget-footer">{sub}</div>}
    </div>
  )
}

/* ─── Flag panel ─── */
function FlagPanel({ flags, title }) {
  const [open, setOpen] = useState(true)
  if (!flags?.length) return null
  const critical = f => /caste|SC\/ST|OBC|General/i.test(f)
  return (
    <div className="bd-card bd-flag-panel">
      <div className="bd-flag-hd" onClick={() => setOpen(o => !o)}>
        <div className="bd-flag-hd-l">
          <div className="bd-card-title">🚩 {title || 'Audit Evidence'}</div>
          <span className="bd-pill pp-fail">
            <span className="bd-pill-dot" />{flags.length} flag{flags.length !== 1 ? 's' : ''}
          </span>
        </div>
        <button className="bd-flag-toggle">{open ? '▲ Collapse' : '▼ Expand'}</button>
      </div>
      {open && (
        <>
          <div className="bd-divider" />
          <div className="bd-flag-list">
            {flags.map((f, i) => (
              <div
                key={i}
                className={`bd-flag-item ${critical(f) ? 'bd-flag-critical' : ''}`}
                style={{ animationDelay: `${i * 0.04}s` }}
              >
                <div className="bd-flag-dot"
                  style={{ background: critical(f) ? 'var(--rose)' : 'var(--amber)' }} />
                <div className="bd-flag-text">{f}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

/* ─── Chart config ─── */
const TT = {
  backgroundColor: '#1A202C',
  titleFont: { family: 'Plus Jakarta Sans', size: 12, weight: 700 },
  bodyFont: { family: 'Plus Jakarta Sans', size: 11 },
  padding: 12, cornerRadius: 10,
  borderColor: 'rgba(0,0,0,0.06)', borderWidth: 1,
  displayColors: true,
}
const GRID = { color: '#EAF1F9' }
const TICK = { color: '#A0AEC0', font: { family: 'Plus Jakarta Sans', size: 11 } }
const ANIM = { duration: 900, easing: 'easeOutQuart' }

const TABS = [
  { id: 'overview', label: '📊 Overview' },
  { id: 'gender', label: '⚧ Gender' },
  { id: 'caste', label: '🏛 Caste' },
  { id: 'skin', label: '🎨 Colorism' },
  { id: 'referral', label: '🤝 Referral' },
  { id: 'marital', label: '💍 Marital' },
  { id: 'proxy', label: '🔍 Proxy' },
  { id: 'more', label: '📋 More' },
]

/* ══════════════════════════════════════════
   DASHBOARD
══════════════════════════════════════════ */
export default function Dashboard({ data, apiBase }) {
  const [tab, setTab] = useState('overview')
  const [key, setKey] = useState(0)
  const [pdfError, setPdfError] = useState('')
  const d = data
  const score = d.fair_hiring_score || d.score || 0
  const label = d.score_label || d.label || '—'
  const scoreBadge = score >= 80 ? 'pass' : score >= 60 ? 'warn' : 'fail'
  const scoreStatus = score >= 80 ? 'Compliant' : score >= 60 ? 'Needs Attention' : 'Non-Compliant'

  const allFlags = [
    ...(d.flags || []), ...(d.caste_flags || []), ...(d.skin_flags || []),
    ...(d.referral_flags || []), ...(d.marital_flags || []), ...(d.proxy_flags || []),
    ...(d.institution_flags || []), ...(d.age_flags || []),
  ]

  const setTabFn = id => { setTab(id); setKey(k => k + 1) }

  /* ── Radar ── */
  const radarData = {
    labels: ['Gender AIR', 'Disability', 'Caste', 'Colorism', 'Referral', 'Proxy'],
    datasets: [{
      label: 'Fairness Index',
      data: [
        Math.min((d.air_gender || 0) * 100, 100),
        Math.min((d.disability_air || 1) * 100, 100),
        (d.caste_flags?.length || 0) === 0 ? 90 : Math.max(30, 90 - d.caste_flags.length * 15),
        Math.min((d.air_skin || 1) * 100, 100),
        Math.min((d.referral_air || 1) * 100, 100),
        (d.proxy_flags?.length || 0) === 0 ? 90 : Math.max(30, 90 - d.proxy_flags.length * 15),
      ],
      backgroundColor: 'rgba(45,96,255,0.07)',
      borderColor: '#2D60FF', borderWidth: 2,
      pointBackgroundColor: '#fff',
      pointBorderColor: '#2D60FF', pointBorderWidth: 2,
      pointRadius: 5, pointHoverRadius: 7,
    }]
  }

  /* ── Funnel ── */
  const otherG    = d.gender_stats?.other_gender || {}
  const hasOtherG = (otherG.total || 0) > 0

  const funnelData = {
    labels: ['Applied', 'Shortlisted', 'Hired'],
    datasets: [
      { label: `Men (n=${d.men_total || 0})`,    data: [d.men_total || 0,   d.men_shortlisted || 0,   d.men_hired || 0],   backgroundColor: '#2D60FF', hoverBackgroundColor: '#1814F3', borderRadius: 6, barPercentage: 0.5 },
      { label: `Women (n=${d.women_total || 0})`, data: [d.women_total || 0, d.women_shortlisted || 0, d.women_hired || 0], backgroundColor: '#F04438', hoverBackgroundColor: '#DC2626', borderRadius: 6, barPercentage: 0.5 },
      ...(hasOtherG ? [{ label: `Non-binary (n=${otherG.total})`, data: [otherG.total || 0, otherG.shortlisted || 0, otherG.hired || 0], backgroundColor: '#7c3aed', hoverBackgroundColor: '#6d28d9', borderRadius: 6, barPercentage: 0.5 }] : []),
    ]
  }

  /* ── Status pills ── */
  const MODULE_DEFS = [
    { key: 'gender',     display: 'Gender' },
    { key: 'disability', display: 'Disability' },
    { key: 'skin',       display: 'Colorism' },
    { key: 'caste',      display: 'Caste' },
  ]
  const statusPills = (() => {
    if (!d.module_results || Object.keys(d.module_results).length === 0) return null
    return MODULE_DEFS.map(({ key, display }) => {
      const passed = d.module_results?.[key]?.passed
      const pillClass = passed === true ? 'pp-pass' : passed === false ? 'pp-fail' : 'pp-warn'
      const pillLabel = passed === true ? 'PASS'  : passed === false ? 'RISK'  : 'N/A'
      return { key, display, pillClass, pillLabel }
    })
  })()

  /* ── Exports (payloads unchanged) ── */
  const handleExportJSON = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `fairhire-audit-${Date.now()}.json`; a.click()
    URL.revokeObjectURL(url)
  }

  const handleExportPDF = async () => {
    setPdfError('')
    const body = {
      audit_id: d.id,                                              // FIX: required by backend
      score, label, flags: d.flags || [], row_count: d.row_count || 0,
      original_filename: d.original_filename || 'audit.csv',
      company_name: 'FairHire Audit',
      air_gender: d.air_gender || 0, shortlisting_gap: d.shortlisting_gap || 0,
      hiring_gap: d.hiring_gap || 0,
      men_total: d.men_total || 0, women_total: d.women_total || 0,
      men_shortlisted: d.men_shortlisted || 0, women_shortlisted: d.women_shortlisted || 0,
      men_hired: d.men_hired || 0, women_hired: d.women_hired || 0,
      disability_air: d.disability_air || 0,
      caste_stats: d.caste_stats || {}, caste_flags: d.caste_flags || [],
      caste_col: d.caste_col || null,
      air_skin: d.air_skin || 0, skin_best_rate: d.skin_best_rate || 0,
      skin_worst_rate: d.skin_worst_rate || 0,
      skin_stats: d.skin_stats || {}, skin_flags: d.skin_flags || [],
      referral_hire_rate: d.referral_hire_rate || 0,
      non_referral_hire_rate: d.non_referral_hire_rate || 0,
      referral_air: d.referral_air || 0, referral_hhi: d.referral_hhi || 0,
      referral_flags: d.referral_flags || [],
      marital_stats: d.marital_stats || {}, marital_flags: d.marital_flags || [],
      marital_intersectional_stats: d.marital_intersectional_stats || {},
      age_flags: d.age_flags || [], institution_flags: d.institution_flags || [],
      proxy_flags: d.proxy_flags || [], proxy_phi_scores: d.proxy_phi_scores || {},
      gender_stats:         d.gender_stats         || {},
      age_stats:            d.age_stats            || {},
      institution_stats:    d.institution_stats    || {},
      referral_stats:       d.referral_stats       || {},
      proxy_stats:          d.proxy_stats          || {},
    }
    // FIX: use authFetch — sends auth cookie + CSRF token automatically
    const r = await authFetch(`${apiBase}/api/report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!r.ok) {
      const err = await r.json().catch(() => ({}))
      throw new Error(err?.detail?.error || `Report generation failed (${r.status})`)
    }
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'FairHire_Compliance_Report.pdf'; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="bd">
      <StyleInjector />

      {/* ── Topbar ── */}
      <header className="bd-top">
        <div className="bd-brand">
          <div className="bd-brand-logo">⚖️</div>
          <div className="bd-brand-name">Fair<span>Hire</span></div>
          <div className="bd-file-chip">
            📁 {d.original_filename || 'audit.csv'} · {(d.row_count || 0).toLocaleString()} records
          </div>
        </div>
        <div className="bd-top-right">
          <ExportBtn label="Raw JSON" icon="📄" onClick={handleExportJSON} variant="outline" />
          <ExportBtn label="Download Report" icon="📑" onClick={handleExportPDF} onError={setPdfError} variant="primary" />
          {pdfError && (
            <div style={{ marginTop: 8, fontSize: 12.5, color: 'var(--rose)', padding: '6px 10px', background: 'var(--rose-bg)', borderRadius: 'var(--radius-md)', border: '1px solid var(--rose-bd)' }}>
              ⚠️ {pdfError}
            </div>
          )}
        </div>
      </header>

      {/* ── Tabs ── */}
      <nav className="bd-tabs">
        {TABS.map(t => (
          <button key={t.id} className={`bd-tab ${tab === t.id ? 'is-active' : ''}`} onClick={() => setTabFn(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>

      {/* ── Body ── */}
      <main className="bd-body">

        {/* ═══ OVERVIEW ═══ */}
        {tab === 'overview' && (
          <div key={key} className="bd-tab-view">

            {/* Page header */}
            <div className="bd-page-head">
              <div>
                <h1>Bias Audit <em>Overview</em></h1>
                <div className="bd-page-head-sub">
                  10-module compliance analysis · {(d.row_count || 0).toLocaleString()} candidates · Generated {new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
                </div>
              </div>
              {statusPills && (
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                  {statusPills.map(({ key, display, pillClass, pillLabel }) => (
                    <span key={key} className={`bd-pill ${pillClass}`}>
                      <span className="bd-pill-dot" />{display} {pillLabel}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Widget row */}
            <div className="bd-g4">
              <Widget label="Fair Hiring Score" value={`${score}/100`} icon={score >= 80 ? '✅' : score >= 60 ? '⚠️' : '❌'} variant={scoreBadge} sub={scoreStatus} delay={0.04} />
              <Widget label="Gender AIR" value={(d.air_gender || 0).toFixed(3)} icon="⚧" variant={d.air_gender >= 0.8 ? 'pass' : 'fail'} sub="EEOC 4/5ths · threshold 0.80" delay={0.09} />
              <Widget label="Flags Raised" value={allFlags.length} icon="🚩" variant={allFlags.length > 5 ? 'fail' : allFlags.length > 0 ? 'warn' : 'pass'} sub={`Across all 10 modules`} delay={0.14} />
              <Widget label="Candidates" value={(d.row_count || 0).toLocaleString()} icon="👥" variant="blue" sub="Total records audited" delay={0.19} />
            </div>

            {/* Charts */}
            <div className="bd-g2">

              {/* Score card */}
              <div className="bd-card d2" style={{ animation: 'fadeUp 0.38s var(--ease) 0.14s both' }}>
                <div className="bd-card-hd">
                  <div>
                    <div className="bd-card-title">Compliance Score</div>
                    <div className="bd-card-sub">Weighted index · 10 bias modules</div>
                  </div>
                  <span className={`bd-pill pp-${scoreBadge}`}>
                    <span className="bd-pill-dot" />{scoreStatus}
                  </span>
                </div>
                <div className="bd-divider" />
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
                  <GaugeChart value={score} label={label} />
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Fair Hiring Score</div>
                </div>
                <div className="bd-air-row">
                  {[
                    { k: 'Gender AIR', v: (d.air_gender || 0).toFixed(3), ok: d.air_gender >= 0.8 },
                    { k: 'Colorism AIR', v: (d.air_skin || 0).toFixed(3), ok: d.air_skin >= 0.8 },
                    { k: 'Referral AIR', v: (d.referral_air || 0).toFixed(3), ok: d.referral_air >= 0.8 },
                  ].map(({ k, v, ok }) => (
                    <div key={k} className={`bd-air-chip ${ok ? 'ac-pass' : 'ac-fail'}`}>
                      <div className="bd-air-label">{k}</div>
                      <div className="bd-air-val">{v}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Radar */}
              <div className="bd-card d3" style={{ animation: 'fadeUp 0.38s var(--ease) 0.19s both' }}>
                <div className="bd-card-hd">
                  <div>
                    <div className="bd-card-title">Fairness Radar</div>
                    <div className="bd-card-sub">All 6 compliance dimensions at a glance</div>
                  </div>
                </div>
                <div className="bd-divider" />
                <div className="bd-chart">
                  <Radar data={radarData} options={{
                    responsive: true, maintainAspectRatio: false, animation: ANIM,
                    scales: {
                      r: {
                        min: 0, max: 100,
                        ticks: { stepSize: 25, font: { size: 10, family: 'Plus Jakarta Sans' }, backdropColor: 'transparent', color: '#A0AEC0' },
                        grid: GRID, angleLines: GRID,
                        pointLabels: { font: { family: 'Plus Jakarta Sans', size: 11, weight: 600 }, color: '#718096' },
                      }
                    },
                    plugins: { legend: { display: false }, tooltip: TT }
                  }} />
                </div>
              </div>
            </div>

            {/* Funnel */}
            <div className="bd-card d4" style={{ marginBottom: 22, animation: 'fadeUp 0.38s var(--ease) 0.24s both' }}>
              <div className="bd-card-hd">
                <div>
                  <div className="bd-card-title">Hiring Pipeline — Gender Breakdown</div>
                  <div className="bd-card-sub">Applied → Shortlisted → Hired · Disproportionate drops signal systemic bias</div>
                </div>
                <span className="bd-pill pp-blue">
                  <span className="bd-pill-dot" />{(d.men_total || 0) + (d.women_total || 0) + (otherG.total || 0)} applicants
                </span>
              </div>
              <div className="bd-divider" />
              <div className="bd-chart" style={{ height: 230 }}>
                <Bar data={funnelData} options={{
                  responsive: true, maintainAspectRatio: false, animation: ANIM,
                  plugins: {
                    legend: { position: 'right', labels: { font: { family: 'Plus Jakarta Sans', size: 12, weight: 500 }, padding: 20, usePointStyle: true, pointStyle: 'rectRounded', color: '#718096' } },
                    tooltip: TT,
                  },
                  scales: {
                    y: { beginAtZero: true, grid: GRID, ticks: TICK, border: { display: false } },
                    x: { grid: { display: false }, ticks: TICK, border: { display: false } },
                  }
                }} />
              </div>
            </div>

            {/* Flags */}
            {allFlags.length > 0 && <FlagPanel flags={allFlags} title="All Audit Evidence" />}
          </div>
        )}

        {/* ═══ MODULE TABS ═══ */}
        {tab !== 'overview' && (
          <div key={key} className="bd-tab-view">
            <div className="bd-page-head" style={{ marginBottom: 20 }}>
              <div>
                <h1>{TABS.find(t => t.id === tab)?.label.replace(/^\S+\s/, '')} <em>Analysis</em></h1>
                <div className="bd-page-head-sub">FairHire v2.0 · Detailed module view</div>
              </div>
            </div>
            {tab === 'gender' && <GenderModule data={d} />}
            {tab === 'caste' && <CasteModule data={d} />}
            {tab === 'skin' && <SkinModule data={d} />}
            {tab === 'referral' && <ReferralModule data={d} />}
            {tab === 'marital' && <MaritalModule data={d} />}
            {tab === 'proxy' && <ProxyModule data={d} />}
            {tab === 'more' && (
              <>
                <DisabilityModule data={d} />
                <div style={{ marginTop: 24 }}><InstitutionModule data={d} /></div>
                <div style={{ marginTop: 24 }}><AgeModule data={d} /></div>
              </>
            )}
          </div>
        )}

      </main>
    </div>
  )
}