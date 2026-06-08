import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { authFetch } from './authUtils'

// ── PlanBadge ─────────────────────────────────────────────────────────────────
function PlanBadge({ plan }) {
  const styles = {
    free:       { bg: 'var(--bg-muted)',   color: 'var(--text-muted)',   label: 'Free' },
    pro:        { bg: 'var(--blue-100,#dbeafe)', color: 'var(--blue-600,#2563eb)', label: 'Pro' },
    enterprise: { bg: '#fef3c7',           color: '#92400e',             label: 'Enterprise' },
  }
  const s = styles[plan] || styles.free
  return (
    <span style={{
      display: 'inline-block', fontSize: 10, fontWeight: 700, letterSpacing: '0.04em',
      padding: '2px 7px', borderRadius: 99,
      background: s.bg, color: s.color, textTransform: 'uppercase',
    }}>
      {s.label}
    </span>
  )
}

// ── UsageBar ──────────────────────────────────────────────────────────────────
function UsageBar({ used, limit }) {
  if (limit === -1) {
    // unlimited plan
    return (
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
        ∞ unlimited audits
      </div>
    )
  }
  const pct = Math.min(100, Math.round((used / limit) * 100))
  const barColor = pct >= 100 ? 'var(--rose-500,#ef4444)'
                 : pct >= 80  ? '#f59e0b'
                 : 'var(--blue-500,#3b82f6)'

  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
        {used} / {limit} audits this month
      </div>
      <div style={{
        height: 4, borderRadius: 99, background: 'var(--border)',
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`, height: '100%',
          borderRadius: 99, background: barColor,
          transition: 'width 0.4s ease',
        }} />
      </div>
    </div>
  )
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
export default function Sidebar({ user, apiBase, onLogout, hasResult }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [subscription, setSubscription] = useState(null)
  const [mobileOpen, setMobileOpen] = useState(false)

  const page = location.pathname.replace(/^\//, '') || 'home'

  // Fetch subscription status once on mount (and when user changes)
  useEffect(() => {
    if (!user || !apiBase) return
    let cancelled = false

    authFetch(`${apiBase}/api/subscription-status`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!cancelled && data) setSubscription(data)
      })
      .catch(() => {/* silently ignore — sidebar is non-critical */})

    return () => { cancelled = true }
  }, [user?.id, apiBase])

  const plan  = subscription?.plan  ?? user?.plan  ?? 'free'
  const used  = subscription?.audit_count_this_month ?? 0
  const limit = subscription?.monthly_limit ?? 5

  const goTo = (path) => {
    navigate(path)
    setMobileOpen(false)
  }

  const scrollToModule = (moduleId, path) => {
    navigate(path)
    setTimeout(() => document.getElementById(moduleId)?.scrollIntoView({ behavior: 'smooth' }), 100)
    setMobileOpen(false)
  }

  return (
    <>
      {/* Hamburger button — visible only on mobile */}
      <button
        className="sidebar-hamburger"
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label="Toggle menu"
      >
        ☰
      </button>

      {/* Overlay for mobile */}
      {mobileOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside className={`sidebar${mobileOpen ? ' sidebar-open' : ''}`}>
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">FH</div>
          <div className="sidebar-brand-text">
            <h1>FairHire</h1>
            <span>AI Fairness Auditor v2.0</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section">Audit</div>
          <button className={`nav-item ${page === 'home' || page === '' ? 'active' : ''}`} onClick={() => goTo('/')}>
            <span className="nav-icon">🏠</span> Home Page
          </button>
          <button className={`nav-item ${page === 'upload' ? 'active' : ''}`} onClick={() => goTo('/upload')}>
            <span className="nav-icon">📤</span> New Audit
          </button>
          {hasResult && (
            <button className={`nav-item ${page === 'dashboard' ? 'active' : ''}`} onClick={() => goTo('/dashboard')}>
              <span className="nav-icon">📊</span> Dashboard
            </button>
          )}
          <button className={`nav-item ${page === 'history' ? 'active' : ''}`} onClick={() => goTo('/history')}>
            <span className="nav-icon">📋</span> Audit History
          </button>

          <div className="nav-section">Bias Modules</div>
          {hasResult && (
            <>
              <button className="nav-item" onClick={() => scrollToModule('mod-gender', '/dashboard')}>
                <span className="nav-icon">⚧</span> Gender AIR
              </button>
              <button className="nav-item" onClick={() => scrollToModule('mod-caste', '/dashboard')}>
                <span className="nav-icon">🏛</span> Caste/Category
              </button>
              <button className="nav-item" onClick={() => scrollToModule('mod-skin', '/dashboard')}>
                <span className="nav-icon">🎨</span> Colorism
              </button>
              <button className="nav-item" onClick={() => scrollToModule('mod-proxy', '/dashboard')}>
                <span className="nav-icon">🔍</span> Proxy Bias
              </button>
            </>
          )}
        </nav>

        <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16, marginTop: 'auto' }}>
          <div style={{ padding: '0 8px', marginBottom: 12 }}>
            {/* User row */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <div style={{
                width: 32, height: 32, borderRadius: 'var(--radius-full)',
                background: 'var(--blue-100)', color: 'var(--blue-600)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 700, fontSize: 13, flexShrink: 0,
              }}>
                {(user?.email || '?')[0].toUpperCase()}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user?.company_name || 'User'}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user?.email}
                </div>
              </div>
            </div>

            {/* Plan badge + usage — BILL-5 */}
            <div style={{
              background: 'var(--bg-muted)', borderRadius: 'var(--radius-md)',
              padding: '8px 10px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 2 }}>
                <PlanBadge plan={plan} />
                {plan === 'free' && (
                  <button
                    onClick={() => goTo('/upload')}
                    style={{
                      fontSize: 10, fontWeight: 700, background: 'none', border: 'none',
                      cursor: 'pointer', color: 'var(--blue-600,#2563eb)', padding: 0,
                      textDecoration: 'underline',
                    }}
                  >
                    Upgrade
                  </button>
                )}
              </div>
              <UsageBar used={used} limit={limit} />
            </div>
          </div>

          <button className="nav-item" onClick={onLogout} style={{ color: 'var(--rose-600)' }}>
            <span className="nav-icon">🚪</span> Sign Out
          </button>
        </div>
      </aside>
    </>
  )
}
