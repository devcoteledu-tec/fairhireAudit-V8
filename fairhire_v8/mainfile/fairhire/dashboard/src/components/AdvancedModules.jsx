import React from 'react'
import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend
} from 'chart.js'
import annotationPlugin from 'chartjs-plugin-annotation'
import { MetricCard, FlagFeed, RegTag, airBadge } from './ChartHelpers'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, annotationPlugin)

const tooltipCfg = {
  backgroundColor: '#0F172A', titleFont: { family: 'Inter', size: 12, weight: 600 },
  bodyFont: { family: 'Inter', size: 11 }, padding: 10, cornerRadius: 8, displayColors: true,
}

/* ── Exact Fitzpatrick Hex Codes ─────────────────────────────── */
const FITZ_HEX = {
  '1': '#F7E2D3', '2': '#F3CDB6', '3': '#EDB088',
  '4': '#C58459', '5': '#AC734C', '6': '#3B2E2A',
}
const FITZ_LABEL = { '1': 'Type I', '2': 'Type II', '3': 'Type III', '4': 'Type IV', '5': 'Type V', '6': 'Type VI' }
const fitzBorder = c => (c === '#F7E2D3' || c === '#F3CDB6') ? '#d4a574' : '#FFFFFF'

/* ── Helper: compute hire rate from {total, hired} ───────────── */
function hireRate(s) {
  if (!s) return 0
  if (typeof s !== 'object') return parseFloat(s || 0)
  // audit_engine returns {total, shortlisted, hired} — no hire_rate key
  if (s.total && s.total > 0) return s.hired / s.total
  if (s.hire_rate !== undefined) return parseFloat(s.hire_rate)
  return 0
}

function groupN(s) {
  if (!s || typeof s !== 'object') return '?'
  return s.total || s.n || '?'
}

/* ═══════════════════════════════════════════════════════════════════
   6 · COLORISM & SKIN TONE — Fitzpatrick Histogram
   ───────────────────────────────────────────────────────────────────
   Data: d.skin_stats has INTEGER keys (1-6) which become STRING keys
   "1","2",... in JSON. Each value = {total, shortlisted, hired}.
   ═══════════════════════════════════════════════════════════════════ */
export function SkinModule({ data: d }) {
  const stats = d.skin_stats
  if ((!stats || !Object.keys(stats).length) && !d.air_skin) return null

  // Keys are "1","2","3","4","5","6" (stringified integers from Python)
  const rawKeys = Object.keys(stats || {}).sort((a, b) => parseInt(a) - parseInt(b))

  // Build chart arrays from actual data
  const labels = rawKeys.map(k => FITZ_LABEL[k] || `Type ${k}`)
  const rates = rawKeys.map(k => hireRate(stats[k]) * 100)
  const ns = rawKeys.map(k => groupN(stats[k]))
  const colors = rawKeys.map(k => FITZ_HEX[k] || '#C58459')

  // Fallback if skin_stats is empty but we have light/dark rates
  if (rawKeys.length === 0 && (d.skin_light_rate || d.skin_dark_rate)) {
    labels.push('Light', 'Dark')
    rates.push((d.skin_light_rate || 0) * 100, (d.skin_dark_rate || 0) * 100)
    ns.push('?', '?')
    colors.push('#F3CDB6', '#3B2E2A')
  }

  if (labels.length === 0) return null

  const majorityRate = Math.max(...rates)

  const chart = {
    labels,
    datasets: [{
      label: 'Hire Rate %',
      data: rates,
      backgroundColor: colors,
      borderWidth: 2,
      borderColor: colors.map(c => fitzBorder(c)),
      borderRadius: 6,
      barPercentage: 0.65,
    }]
  }

  const opts = {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right',
        labels: { font: { family: 'Inter', size: 12 }, padding: 14, usePointStyle: true, pointStyle: 'rectRounded' }
      },
      tooltip: {
        ...tooltipCfg,
        callbacks: {
          label: ctx => ` Hire Rate: ${ctx.raw.toFixed(1)}%`,
          afterLabel: ctx => {
            const air = majorityRate > 0 ? (ctx.raw / majorityRate).toFixed(2) : '—'
            return `n = ${ns[ctx.dataIndex]} · AIR vs majority: ${air}`
          }
        }
      },
      annotation: {
        annotations: {
          majorityLine: {
            type: 'line', scaleID: 'y', value: majorityRate,
            borderColor: '#64748b', borderWidth: 2, borderDash: [8, 4],
            label: {
              display: true, content: `Majority Rate: ${majorityRate.toFixed(1)}%`,
              position: 'end', backgroundColor: '#475569',
              font: { size: 10, family: 'Inter' }, padding: 4,
            }
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true, grid: { color: '#f1f5f9' },
        title: { display: true, text: 'Hire Rate %', font: { family: 'Inter', size: 11, weight: 500 }, color: '#94A3B8' }
      },
      x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 } } },
    }
  }

  return (
    <section id="mod-skin">
      <div className="card">
        <div className="card-header">
          <div className="card-title" style={{ fontSize: 16 }}>🎨 Colorism & Skin Tone — Fitzpatrick Scale</div>
          <RegTag text="DPDP Act 2025" />
        </div>
        <div className="metric-grid">
          <MetricCard label="Skin Tone AIR" value={d.air_skin?.toFixed(2) || '—'}
            badge={airBadge(d.air_skin)} sub="Dark vs Light adverse impact" />
          <MetricCard label="Light Tone Rate" value={`${((d.skin_light_rate || 0) * 100).toFixed(1)}%`}
            color="#AC734C" sub="Hire rate — lighter tones (I-III)" />
          <MetricCard label="Dark Tone Rate" value={`${((d.skin_dark_rate || 0) * 100).toFixed(1)}%`}
            color="#3B2E2A" sub="Hire rate — darker tones (IV-VI)" />
        </div>
        {/* Fitzpatrick color key */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
          {Object.entries(FITZ_HEX).map(([k, c]) => (
            <div key={k} style={{
              display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--text-secondary)',
              padding: '3px 8px', background: 'var(--bg-muted)', borderRadius: 'var(--radius-sm)',
            }}>
              <span style={{ width: 14, height: 14, borderRadius: 3, background: c, border: '1px solid #d4a574' }} />
              Type {k}
            </div>
          ))}
        </div>
        <div className="chart-wrap chart-wrap-lg">
          <Bar data={chart} options={opts} />
        </div>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8, fontStyle: 'italic' }}>
          Dashed line = majority group hire rate. Bars below this line indicate adverse impact.
        </p>
        <FlagFeed flags={d.skin_flags} title="Colorism Flags" icon="🎨" />
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   7 · REFERRAL NETWORK BIAS
   ═══════════════════════════════════════════════════════════════════ */
export function ReferralModule({ data: d }) {
  if (!d.referral_hire_rate && !d.referral_air) return null
  const chart = {
    labels: ['Referred', 'Cold / Non-Referred'],
    datasets: [{
      label: 'Hire Rate %',
      data: [(d.referral_hire_rate || 0) * 100, (d.non_referral_hire_rate || 0) * 100],
      backgroundColor: ['#2563eb', '#94A3B8'], borderRadius: 6, barPercentage: .45,
    }]
  }
  return (
    <section id="mod-referral"><div className="card">
      <div className="card-header"><div className="card-title" style={{ fontSize: 16 }}>🤝 Referral Network Bias</div><RegTag text="Equal Opportunity" /></div>
      <div className="metric-grid">
        <MetricCard label="Referral AIR" value={(d.referral_air || 0).toFixed(2)} badge={airBadge(d.referral_air)} sub="Cold vs Referred impact" />
        <MetricCard label="Referred Rate" value={`${((d.referral_hire_rate || 0) * 100).toFixed(1)}%`} color="#2563eb" sub="Hire rate via referral" />
        <MetricCard label="Cold Apply Rate" value={`${((d.non_referral_hire_rate || 0) * 100).toFixed(1)}%`} color="#64748b" sub="Cold application" />
        <MetricCard label="Referral HHI" value={(d.referral_hhi || 0).toFixed(3)}
          badge={d.referral_hhi > .25 ? 'fail' : d.referral_hhi > .15 ? 'warn' : 'pass'} sub="Concentration (< 0.15 = diverse)" />
      </div>
      <div className="chart-wrap chart-wrap-sm">
        <Bar data={chart} options={{
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { position: 'right', labels: { font: { family: 'Inter', size: 12 }, padding: 16, usePointStyle: true } }, tooltip: { ...tooltipCfg, callbacks: { afterLabel: () => `AIR: ${(d.referral_air || 0).toFixed(2)}` } } },
          scales: { y: { beginAtZero: true, grid: { color: '#f1f5f9' } }, x: { grid: { display: false } } }
        }} />
      </div>
      <FlagFeed flags={d.referral_flags} title="Referral Flags" icon="🤝" />
    </div></section>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   8 · MARITAL STATUS — Intersectional Heatmap
   ───────────────────────────────────────────────────────────────────
   Data: d.marital_intersectional_stats uses PIPE separator
   Keys are "Married|male", "Single|female" etc. (line 1106 of audit_engine.py)
   ═══════════════════════════════════════════════════════════════════ */
export function MaritalModule({ data: d }) {
  const inter = d.marital_intersectional_stats
  if (!inter || !Object.keys(inter).length) return null

  const hc = r => r >= .3 ? { bg: '#d1fae5', color: '#047857', bd: '#a7f3d0' }
    : r >= .15 ? { bg: '#fef3c7', color: '#92400e', bd: '#fde68a' }
    : { bg: '#ffe4e6', color: '#9f1239', bd: '#fecdd3' }

  const genders = new Set()
  const statuses = new Set()
  const cells = {}
  const cellNs = {}

  Object.entries(inter).forEach(([k, v]) => {
    // Key format from audit_engine.py: "Married|male" (pipe separator)
    let parts = k.split('|')
    // Fallback: also try underscore separator
    if (parts.length < 2) parts = k.split('_')
    if (parts.length < 2) return

    const maritalStatus = parts[0].trim()
    const gender = parts[1].trim()
    // Capitalize gender for display
    const genderDisplay = gender.charAt(0).toUpperCase() + gender.slice(1)

    statuses.add(maritalStatus)
    genders.add(genderDisplay)

    // Compute hire rate from {total, shortlisted, hired}
    const rate = hireRate(v)
    const n = groupN(v)

    cells[`${genderDisplay}_${maritalStatus}`] = rate
    cellNs[`${genderDisplay}_${maritalStatus}`] = n
  })

  const ga = [...genders].sort()
  const sa = [...statuses].sort()

  if (ga.length === 0 || sa.length === 0) return null

  return (
    <section id="mod-marital"><div className="card">
      <div className="card-header"><div className="card-title" style={{ fontSize: 16 }}>💍 Marital Status — Intersectional Heatmap</div><RegTag text="DPDP Act 2025" /></div>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
        Hire rate at the intersection of Gender × Marital Status. Cells below 15% are flagged.
      </p>
      <table className="heatmap-table">
        <thead>
          <tr>
            <th style={{ textAlign: 'left', width: 120 }}>Gender \ Status</th>
            {sa.map(s => <th key={s}>{s}</th>)}
          </tr>
        </thead>
        <tbody>
          {ga.map(g => (
            <tr key={g}>
              <td style={{ fontWeight: 700, textAlign: 'left', fontSize: 13 }}>{g}</td>
              {sa.map(s => {
                const rate = cells[`${g}_${s}`] || 0
                const n = cellNs[`${g}_${s}`] || '?'
                const { bg, color, bd } = hc(rate)
                return (
                  <td key={s} style={{
                    background: bg, color, fontWeight: 700,
                    border: `1px solid ${bd}`, borderRadius: 4,
                  }} title={`n=${n}, Rate=${(rate * 100).toFixed(1)}%`}>
                    {(rate * 100).toFixed(1)}%
                    <div style={{ fontSize: 9, fontWeight: 400, opacity: .7 }}>n={n}</div>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ display: 'flex', gap: 16, marginTop: 14, fontSize: 11, color: 'var(--text-muted)' }}>
        {[['#d1fae5', '≥ 30%'], ['#fef3c7', '15–30%'], ['#ffe4e6', '< 15%']].map(([c, t]) => (
          <span key={t}><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: c, marginRight: 4 }} />{t}</span>
        ))}
      </div>
      <FlagFeed flags={d.marital_flags} title="Marital Status Flags" icon="💍" />
    </div></section>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   9 · PROXY BIAS — Lollipop Chart with φ = 0.20 Threshold
   ═══════════════════════════════════════════════════════════════════ */
export function ProxyModule({ data: d }) {
  const phi = d.proxy_phi_scores; const flags = d.proxy_flags
  if ((!phi || !Object.keys(phi).length) && (!flags || !flags.length)) return null
  const PHI = 0.20
  const labels = Object.keys(phi || {}); const values = labels.map(k => parseFloat(phi[k] || 0))
  const absVals = values.map(v => Math.abs(v))
  const chart = {
    labels: labels.map(l => l.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())),
    datasets: [{
      label: '|φ| Coefficient',
      data: absVals,
      backgroundColor: absVals.map(v => v >= PHI ? '#e11d48' : '#cbd5e1'),
      borderRadius: 6, barPercentage: .55,
      borderWidth: absVals.map(v => v >= PHI ? 2 : 1),
      borderColor: absVals.map(v => v >= PHI ? '#be123c' : '#94a3b8'),
    }]
  }
  return (
    <section id="mod-proxy"><div className="card">
      <div className="card-header"><div className="card-title" style={{ fontSize: 16 }}>🔍 Proxy Bias Detection — Phi Correlation</div><RegTag text="DPDP Act 2025" /></div>
      <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.6 }}>
        Phi coefficient (φ) measures correlation between proxy variables and hiring outcomes.
        Bars turn <span style={{ color: '#e11d48', fontWeight: 700 }}>red</span> when |φ| ≥ {PHI}.
      </p>
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
        {labels.map((l, i) => {
          const high = absVals[i] >= PHI
          return (
            <div key={l} style={{
              padding: '6px 14px', borderRadius: 'var(--radius-full)',
              background: high ? '#fff1f2' : '#f8fafc',
              border: `1px solid ${high ? '#fecdd3' : '#e2e8f0'}`,
              fontSize: 12, fontWeight: 600, color: high ? '#be123c' : '#64748b',
              animation: high ? 'pulse-badge 2s ease-in-out infinite' : 'none',
            }}>
              {l.replace(/_/g, ' ')}: φ = {values[i].toFixed(3)}
              {high && <span style={{ marginLeft: 6, fontSize: 10 }}>⚠ HIGH</span>}
            </div>
          )
        })}
      </div>
      <style>{`@keyframes pulse-badge { 0%,100% { box-shadow: 0 0 0 0 rgba(225,29,72,.3); } 50% { box-shadow: 0 0 0 6px rgba(225,29,72,0); } }`}</style>
      {labels.length > 0 && (
        <div className="chart-wrap">
          <Bar data={chart} options={{
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            plugins: {
              legend: { position: 'right', labels: { font: { family: 'Inter', size: 12 }, padding: 16, usePointStyle: true, pointStyle: 'rectRounded' } },
              tooltip: { ...tooltipCfg, callbacks: {
                label: ctx => { const st = ctx.raw >= .30 ? 'HIGH RISK' : ctx.raw >= PHI ? 'WATCH' : 'OK'; return ` |φ| = ${ctx.raw.toFixed(3)} — ${st}` } } },
              annotation: { annotations: { threshold: {
                type: 'line', scaleID: 'x', value: PHI,
                borderColor: '#e11d48', borderWidth: 2, borderDash: [6, 4],
                label: { display: true, content: `φ = ${PHI}`, position: 'start', backgroundColor: '#e11d48', font: { size: 10, family: 'Inter' }, padding: 4 }
              } } }
            },
            scales: {
              x: { beginAtZero: true, max: Math.max(1, ...absVals) * 1.15, grid: { color: '#f1f5f9' },
                title: { display: true, text: '|φ| Coefficient', font: { family: 'Inter', size: 11, weight: 500 }, color: '#94A3B8' } },
              y: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 12, weight: 500 } } },
            }
          }} />
        </div>
      )}
      <FlagFeed flags={flags} title="Proxy Bias Flags" icon="🔍" />
    </div></section>
  )
}
