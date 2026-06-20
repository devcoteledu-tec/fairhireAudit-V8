import React from 'react'
export function GaugeChart({ value, max = 100, label, size = 180 }) {
  const safeValue = Number.isFinite(Number(value)) ? Number(value) : 0
  const pct = Math.min(safeValue / max, 1)
  const r = 70, cx = 90, cy = 85
  const startAngle = Math.PI, endAngle = 0
  const sweep = pct * Math.PI
  // use safe value
  const color = safeValue >= 80 ? '#10b981' : safeValue >= 60 ? '#f59e0b' : '#e11d48'
  const x1 = cx + r * Math.cos(startAngle)
  const y1 = cy - r * Math.sin(startAngle)
  const x2 = cx + r * Math.cos(startAngle - sweep)
  const y2 = cy - r * Math.sin(startAngle - sweep)
  const largeArc = sweep > Math.PI ? 1 : 0
  const bgX2 = cx + r * Math.cos(endAngle)
  const bgY2 = cy - r * Math.sin(endAngle)
  return (
    <div className="gauge-container">
      <svg width={size} height={size * 0.6} viewBox="0 0 180 100">
        <path d={`M ${x1} ${y1} A ${r} ${r} 0 1 1 ${bgX2} ${bgY2}`}
          fill="none" stroke="#E2E8F0" strokeWidth="14" strokeLinecap="round" />
        {pct > 0.01 && (
          <path d={`M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`}
            fill="none" stroke={color} strokeWidth="14" strokeLinecap="round" />
        )}
      </svg>
      <div className="gauge-value" style={{ color }}>{Math.round(safeValue)}</div>
      <div className="gauge-label" style={{ color: 'var(--text-secondary)' }}>{label}</div>
    </div>
  )
}
export function MetricCard({ label, value, sub, color, badge }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={color ? { color } : {}}>
        {value}
        {badge && <span className={`badge badge-${badge}`} style={{ fontSize: 11, marginLeft: 8, verticalAlign: 'middle' }}>
          {badge === 'pass' ? '✓ Pass' : badge === 'warn' ? '⚠ Watch' : '✗ Flag'}
        </span>}
      </div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  )
}
export function FlagFeed({ flags, title, icon = '🚩' }) {
  if (!flags || flags.length === 0) return null
  const getSeverity = (f) => {
    const fl = f.toLowerCase()
    if (fl.includes('high risk') || fl.includes('fail') || fl.includes('✗') || fl.includes('critical')) return 'critical'
    if (fl.includes('watch') || fl.includes('warn') || fl.includes('⚠') || fl.includes('moderate')) return 'warning'
    return 'info'
  }
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">{icon} {title || 'Audit Flags'}</div>
        <span className="badge badge-fail">{flags.length} flag{flags.length > 1 ? 's' : ''}</span>
      </div>
      <div className="flag-feed">
        {flags.map((f, i) => {
          const sev = getSeverity(f)
          return (
            <div key={i} className="flag-item">
              <div className={`flag-icon ${sev}`}>
                {sev === 'critical' ? '!' : sev === 'warning' ? '⚠' : 'ℹ'}
              </div>
              <span>{f}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
export function RegTag({ text }) {
  return <span className="reg-tag">⚖ {text}</span>
}
export function airBadge(air) {
  if (air === null || air === undefined || air === 0) return null
  return air >= 0.80 ? 'pass' : air >= 0.60 ? 'warn' : 'fail'
}
export function pct(n, d) {
  if (!d) return '0.0'
  return ((n / d) * 100).toFixed(1)
}
