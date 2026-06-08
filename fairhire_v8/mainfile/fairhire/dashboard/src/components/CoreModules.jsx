import React from 'react'
import { Bar, Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement,
  ArcElement, Title, Tooltip, Legend
} from 'chart.js'
import annotationPlugin from 'chartjs-plugin-annotation'
import { MetricCard, FlagFeed, RegTag, airBadge, pct } from './ChartHelpers'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend, annotationPlugin)

const tooltipCfg = {
  backgroundColor: '#0F172A', titleFont: { family: 'Inter', size: 12, weight: 600 },
  bodyFont: { family: 'Inter', size: 11 }, padding: 10, cornerRadius: 8, displayColors: true,
}

/* ── Helper: compute hire rate from {total, shortlisted, hired} ── */
function hireRate(s) {
  if (!s || typeof s !== 'object') return parseFloat(s || 0)
  if (s.total && s.total > 0) return s.hired / s.total
  if (s.hire_rate !== undefined) return parseFloat(s.hire_rate)
  return 0
}

function groupN(s) {
  if (!s || typeof s !== 'object') return '?'
  return s.total || s.n || '?'
}

/* ═══════════════════════════════════════════════════════════════════
   1 · GENDER AIR — Pipeline Funnel
   ═══════════════════════════════════════════════════════════════════ */
export function GenderModule({ data: d }) {
  // Pull other_gender from gender_stats (saved to DB after the api.py fix)
  const gs = d.gender_stats || {}
  const other = gs.other_gender || {}
  const hasOther = (other.total || 0) > 0

  const menSL   = pct(d.men_shortlisted,  d.men_total)
  const womenSL = pct(d.women_shortlisted, d.women_total)
  const menHR   = pct(d.men_hired,         d.men_total)
  const womenHR = pct(d.women_hired,       d.women_total)
  const otherSL = pct(other.shortlisted,   other.total)
  const otherHR = pct(other.hired,         other.total)

  const totalN = (d.men_total || 0) + (d.women_total || 0) + (other.total || 0)

  const datasets = [
    { label: `Men (n=${d.men_total||0})`,     data: [+menSL,   +menHR],   backgroundColor: '#1e3a5f', borderRadius: 6, barPercentage: .55 },
    { label: `Women (n=${d.women_total||0})`,  data: [+womenSL, +womenHR], backgroundColor: '#f43f5e', borderRadius: 6, barPercentage: .55 },
    ...(hasOther ? [{ label: `Non-binary (n=${other.total})`, data: [+otherSL, +otherHR], backgroundColor: '#7c3aed', borderRadius: 6, barPercentage: .55 }] : []),
  ]

  const rows = [
    { g: 'Men',        c: '#1e3a5f', t: d.men_total,   s: d.men_shortlisted,   h: d.men_hired,   sr: menSL,   hr: menHR   },
    { g: 'Women',      c: '#f43f5e', t: d.women_total,  s: d.women_shortlisted,  h: d.women_hired,  sr: womenSL, hr: womenHR },
    ...(hasOther ? [{ g: 'Non-binary', c: '#7c3aed', t: other.total, s: other.shortlisted, h: other.hired, sr: otherSL, hr: otherHR }] : []),
  ]

  const chart = { labels: ['Shortlisting Rate %', 'Hire Rate %'], datasets }

  return (
    <section id="mod-gender">
      <div className="card-header">
        <div className="card-title" style={{fontSize:16}}>⚧ Gender Adverse Impact Analysis</div>
        <RegTag text="EEOC 4/5ths Rule" />
      </div>
      <div className="metric-grid" style={{marginTop:16}}>
        <MetricCard label="Gender AIR" value={d.air_gender?.toFixed(2)||'—'} badge={airBadge(d.air_gender)} sub={`Threshold ≥ 0.80 · n=${totalN}`}/>
        <MetricCard label="Shortlisting Gap" value={`${(d.shortlisting_gap||0).toFixed(1)}pp`} color={Math.abs(d.shortlisting_gap)>15?'#e11d48':'#10b981'} sub="Statistical Parity Difference"/>
        <MetricCard label="Hiring Gap" value={`${(d.hiring_gap||0).toFixed(1)}pp`} color={Math.abs(d.hiring_gap)>15?'#e11d48':'#10b981'} sub="Final-stage parity gap"/>
        {hasOther && (
          <MetricCard
            label="Non-binary Hire Rate"
            value={`${otherHR}%`}
            color={parseFloat(otherHR) < parseFloat(menHR) * 0.8 ? '#e11d48' : '#10b981'}
            sub={`n=${other.total} · ${other.hired || 0} hired`}
          />
        )}
      </div>
      <div className="grid-2">
        <div className="card">
          <div className="card-title" style={{marginBottom:12}}>Pipeline Comparison</div>
          <div className="chart-wrap">
            <Bar data={chart} options={{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{font:{family:'Inter',size:12},padding:16,usePointStyle:true,pointStyle:'rectRounded'}},tooltip:tooltipCfg},scales:{y:{beginAtZero:true,grid:{color:'#f1f5f9'}},x:{grid:{display:false}}}}}/>
          </div>
        </div>
        <div className="card">
          <div className="card-title" style={{marginBottom:12}}>Pipeline Counts</div>
          <table style={{width:'100%',fontSize:13,borderCollapse:'collapse'}}>
            <thead>
              <tr style={{borderBottom:'2px solid var(--border)'}}>
                {['Group','Applied','Shortlisted','Hired'].map(h=>(
                  <th key={h} style={{padding:'10px 8px',textAlign:h==='Group'?'left':'right',fontWeight:700,fontSize:10,textTransform:'uppercase',letterSpacing:'.6px',color:'var(--text-muted)'}}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(r=>(
                <tr key={r.g} style={{borderBottom:'1px solid var(--border-light)'}}>
                  <td style={{padding:'12px 8px',fontWeight:600}}>
                    <span style={{display:'inline-block',width:10,height:10,borderRadius:2,background:r.c,marginRight:8}}/>
                    {r.g}
                  </td>
                  <td style={{padding:'12px 8px',textAlign:'right'}}>{r.t||0}</td>
                  <td style={{padding:'12px 8px',textAlign:'right'}}>{r.s||0} <span style={{color:'var(--text-muted)',fontSize:11}}>({r.sr}%)</span></td>
                  <td style={{padding:'12px 8px',textAlign:'right'}}>{r.h||0} <span style={{color:'var(--text-muted)',fontSize:11}}>({r.hr}%)</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <FlagFeed flags={d.gender_flags} title="Gender Flags" icon="⚧"/>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   2 · DISABILITY AIR — Pass/Fail Card
   ═══════════════════════════════════════════════════════════════════ */
export function DisabilityModule({ data: d }) {
  const air = d.disability_air; if (!air) return null; const pass = air >= .80
  return (
    <section id="mod-disability"><div className="card" style={{borderLeft:`4px solid ${pass?'#10b981':'#e11d48'}`}}>
      <div className="card-header"><div className="card-title" style={{fontSize:16}}>♿ Disability Inclusion</div><RegTag text="RPWD Act 2016"/></div>
      <div className="metric-grid">
        <MetricCard label="Disability AIR" value={air.toFixed(2)} badge={pass?'pass':'fail'} sub="Adverse Impact Ratio for PwD"/>
        <div style={{display:'flex',alignItems:'center',padding:20}}>
          <div style={{fontSize:14,color:pass?'#047857':'#be123c',fontWeight:500,lineHeight:1.6}}>
            {pass?'Disability inclusion meets the 4/5ths threshold. No adverse impact detected.':'PwD candidates face adverse impact — AIR below 0.80 threshold. Immediate remediation required.'}
          </div>
        </div>
      </div>
    </div></section>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   3 · INSTITUTION / COLLEGE — Professional Donut
   ───────────────────────────────────────────────────────────────────
   Data: d.institution_stats = {name: {total, shortlisted, hired}}
   ═══════════════════════════════════════════════════════════════════ */
export function InstitutionModule({ data: d }) {
  const stats = d.institution_stats; if (!stats || !Object.keys(stats).length) return null
  const COLORS = ['#2563eb','#64748b','#7c3aed','#f59e0b','#10b981','#06b6d4','#ec4899','#84cc16']
  const labels = Object.keys(stats)
  const counts = labels.map(k => {
    const v = stats[k]
    return typeof v === 'object' ? (v.hired || 0) : Math.round(parseFloat(v || 0) * 100)
  })
  const total = counts.reduce((a,b)=>a+b,0)||1
  const maxIdx = counts.indexOf(Math.max(...counts))
  const tier1Pct = ((counts[maxIdx]/total)*100).toFixed(0)
  const chart = { labels, datasets:[{ data:counts, backgroundColor:labels.map((_,i)=>COLORS[i%COLORS.length]), borderWidth:3, borderColor:'#FFFFFF', hoverOffset:10 }] }
  return (
    <section id="mod-institution"><div className="card">
      <div className="card-header"><div className="card-title" style={{fontSize:16}}>🏫 Institution / College Bias</div><RegTag text="Equal Opportunity"/></div>
      <div style={{position:'relative',height:320,display:'flex',alignItems:'center',justifyContent:'center'}}>
        <Doughnut data={chart} options={{responsive:true,maintainAspectRatio:false,cutout:'64%',plugins:{legend:{position:'right',labels:{font:{family:'Inter',size:12},padding:14,usePointStyle:true,pointStyle:'circle'}},tooltip:{...tooltipCfg,callbacks:{label:ctx=>{const p=((ctx.raw/total)*100).toFixed(1);return` ${ctx.label}: ${ctx.raw} hires (${p}%)`}}}}}}/>
        <div style={{position:'absolute',top:'50%',left:'calc(50% - 60px)',transform:'translate(-50%,-50%)',textAlign:'center',pointerEvents:'none'}}>
          <div style={{fontSize:32,fontWeight:800,color:'#0F172A',letterSpacing:'-1px'}}>{tier1Pct}%</div>
          <div style={{fontSize:10,fontWeight:700,color:'#94A3B8',textTransform:'uppercase',letterSpacing:'.6px'}}>Tier-1 Dominance</div>
        </div>
      </div>
      <FlagFeed flags={d.institution_flags} title="Institution Flags" icon="🏫"/>
    </div></section>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   4 · AGE GROUP — Monochromatic Gradient (Light Blue → Dark Indigo)
   ───────────────────────────────────────────────────────────────────
   Data: d.age_stats = {bracket: {total, shortlisted, hired}}
   ═══════════════════════════════════════════════════════════════════ */
export function AgeModule({ data: d }) {
  const stats = d.age_stats; if (!stats || !Object.keys(stats).length) return null
  const GRADIENT = ['#bfdbfe','#93c5fd','#60a5fa','#3b82f6','#2563eb','#1d4ed8','#1e40af']
  const labels = Object.keys(stats)
  const rates = labels.map(k => hireRate(stats[k]) * 100)
  const ns = labels.map(k => groupN(stats[k]))
  const chart = { labels, datasets:[{ label:'Hire Rate %', data:rates, backgroundColor:labels.map((_,i)=>GRADIENT[i%GRADIENT.length]), borderRadius:6, barPercentage:.65 }] }
  return (
    <section id="mod-age"><div className="card">
      <div className="card-header"><div className="card-title" style={{fontSize:16}}>📅 Age Group Bias</div><RegTag text="Age Discrimination"/></div>
      <div className="chart-wrap"><Bar data={chart} options={{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{font:{family:'Inter',size:12},padding:16,usePointStyle:true,pointStyle:'rectRounded'}},tooltip:{...tooltipCfg,callbacks:{label:ctx=>` Hire Rate: ${ctx.raw.toFixed(1)}%`,afterLabel:ctx=>`n = ${ns[ctx.dataIndex]}`}}},scales:{y:{beginAtZero:true,grid:{color:'#f1f5f9'},title:{display:true,text:'Hire Rate %',font:{family:'Inter',size:11,weight:500},color:'#94A3B8'}},x:{grid:{display:false}}}}}/></div>
      <FlagFeed flags={d.age_flags} title="Age Flags" icon="📅"/>
    </div></section>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   5 · CASTE / CATEGORY — Grouped Horizontal Bar + Parity Line
   ───────────────────────────────────────────────────────────────────
   Data: d.caste_stats = {"General": {total, shortlisted, hired}, "SC": {...}, ...}
   Hire rate MUST be computed: hired / total (no hire_rate key exists)
   ═══════════════════════════════════════════════════════════════════ */
export function CasteModule({ data: d }) {
  const stats = d.caste_stats; const flags = d.caste_flags
  if ((!stats || !Object.keys(stats).length) && (!flags || !flags.length)) return null

  const PALETTE = { general:'#475569', obc:'#10b981', ews:'#f59e0b', sc:'#f43f5e', st:'#e11d48', default:'#64748b' }
  const colorFor = l => { const w = l.toLowerCase(); return w.includes('general')?PALETTE.general:w.includes('obc')?PALETTE.obc:w.includes('ews')?PALETTE.ews:(w.includes('sc')||w.includes('st'))?PALETTE.sc:PALETTE.default }

  const labels = Object.keys(stats || {})
  // Compute hire rate from {total, shortlisted, hired}
  const rates = labels.map(k => hireRate(stats[k]) * 100)
  const ns = labels.map(k => groupN(stats[k]))

  // Find General rate for parity line
  const genIdx = labels.findIndex(l => l.toLowerCase() === 'general')
  const genRate = genIdx >= 0 ? rates[genIdx] : Math.max(...rates)
  const penCats = labels.filter((_, i) => i !== genIdx && (genRate - rates[i]) > 15)

  const chart = {
    labels,
    datasets: [{
      label: 'Hire Rate %',
      data: rates,
      backgroundColor: labels.map(l => colorFor(l)),
      borderRadius: 6,
      barPercentage: .6,
      // Red border on bars where gap > 15pp
      borderWidth: labels.map((_, i) => i !== genIdx && (genRate - rates[i]) > 15 ? 3 : 0),
      borderColor: labels.map((_, i) => i !== genIdx && (genRate - rates[i]) > 15 ? '#e11d48' : 'transparent'),
    }]
  }

  return (
    <section id="mod-caste">
      {penCats.length > 0 && (
        <div style={{
          background: '#fff1f2', border: '1px solid #fecdd3', borderRadius: 'var(--radius-md)',
          padding: '14px 20px', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <span style={{
            background: '#e11d48', color: '#fff', padding: '3px 10px', borderRadius: 'var(--radius-full)',
            fontSize: 11, fontWeight: 700, letterSpacing: '.3px', whiteSpace: 'nowrap',
          }}>PENALTY</span>
          <span style={{ fontSize: 13, color: '#be123c', fontWeight: 500 }}>
            Gap exceeds 15pp for {penCats.join(', ')} — Article 15 compliance issue.
          </span>
        </div>
      )}
      <div className="card" style={{ borderLeft: penCats.length ? '4px solid #e11d48' : undefined }}>
        <div className="card-header">
          <div className="card-title" style={{ fontSize: 16 }}>🏛 Caste / Category Bias — Stat-Parity Chart</div>
          <RegTag text="Article 15 · DPDP Act 2025" />
        </div>
        {/* Color legend */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          {labels.map((l, i) => (
            <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: colorFor(l) }} />
              {l} ({rates[i].toFixed(1)}%, n={ns[i]})
            </div>
          ))}
        </div>
        {labels.length > 0 && (
          <div className="chart-wrap">
            <Bar data={chart} options={{
              indexAxis: 'y', responsive: true, maintainAspectRatio: false,
              plugins: {
                legend: { display: false },
                tooltip: {
                  ...tooltipCfg,
                  callbacks: {
                    label: ctx => ` Hire Rate: ${ctx.raw.toFixed(1)}%`,
                    afterLabel: ctx => `n = ${ns[ctx.dataIndex]} · Gap vs General: ${(genRate - ctx.raw).toFixed(1)}pp`
                  }
                },
                annotation: {
                  annotations: {
                    parityLine: {
                      type: 'line', scaleID: 'x', value: genRate,
                      borderColor: '#475569', borderWidth: 2, borderDash: [8, 4],
                      label: {
                        display: true, content: `General Parity: ${genRate.toFixed(1)}%`,
                        position: 'end', backgroundColor: '#475569',
                        font: { size: 10, family: 'Inter' }, padding: 4,
                      }
                    }
                  }
                }
              },
              scales: {
                x: { beginAtZero: true, grid: { color: '#f1f5f9' },
                  title: { display: true, text: 'Hire Rate %', font: { family: 'Inter', size: 11, weight: 500 }, color: '#94A3B8' } },
                y: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 12, weight: 500 } } },
              }
            }} />
          </div>
        )}
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 12, fontStyle: 'italic' }}>
          Aligned with Article 15 of the Constitution of India and DPDP Act 2025.
        </p>
        <FlagFeed flags={flags} title="Caste/Category Flags" icon="🏛" />
      </div>
    </section>
  )
}