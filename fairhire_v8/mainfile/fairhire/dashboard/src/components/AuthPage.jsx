import React, { useState } from 'react'

// view: 'login' | 'register' | 'forgot' | 'forgot_sent' | 'register_done'
export default function AuthPage({ apiBase, onLogin, onBack }) {
  const [view, setView]       = useState('login')
  const [email, setEmail]     = useState('')
  const [password, setPassword] = useState('')
  const [company, setCompany] = useState('')
  const [resetEmail, setResetEmail] = useState('')
  const [error, setError]     = useState('')
  const [loading, setLoading] = useState(false)

  const switchView = (v) => { setError(''); setView(v) }

  // ── Login ────────────────────────────────────────────────────────────────
  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const r = await fetch(`${apiBase}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      })

      if (r.status === 403) {
        throw new Error('Please verify your email. Check your inbox.')
      }
      if (!r.ok) {
        const d = await r.json().catch(() => ({}))
        throw new Error(d?.detail?.error || d?.detail || 'Authentication failed')
      }

      const loginData = await r.json()
      onLogin({ email: loginData.email || email })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // ── Register ─────────────────────────────────────────────────────────────
  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const r = await fetch(`${apiBase}/api/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password, company_name: company }),
      })

      if (!r.ok) {
        const d = await r.json().catch(() => ({}))
        throw new Error(d?.detail?.error || d?.detail || d?.message || 'Registration failed')
      }

      switchView('register_done')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // ── Forgot password ───────────────────────────────────────────────────────
  const handleForgot = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await fetch(`${apiBase}/api/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: resetEmail }),
      })
      // Always show success — server never reveals whether email exists
      switchView('forgot_sent')
    } catch {
      // Network error — still show success to avoid enumeration
      switchView('forgot_sent')
    } finally {
      setLoading(false)
    }
  }

  // ── Shared card shell ─────────────────────────────────────────────────────
  const Logo = () => (
    <div style={{ textAlign: 'center', marginBottom: 24 }}>
      <div style={{
        width: 52, height: 52, margin: '0 auto 16px',
        background: 'linear-gradient(135deg, #2563eb, #10b981)',
        borderRadius: 'var(--radius-lg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#fff', fontWeight: 800, fontSize: 20,
      }}>FH</div>
    </div>
  )

  const BackToLogin = ({ label = '← Back to sign in' }) => (
    <button
      onClick={() => switchView('login')}
      style={{
        background: 'none', border: 'none', color: 'var(--text-muted)',
        cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center',
        gap: 4, marginBottom: 16, padding: 0, fontWeight: 600,
      }}
    >{label}</button>
  )

  // ── Views ─────────────────────────────────────────────────────────────────

  // Register success
  if (view === 'register_done') {
    return (
      <div className="auth-wrapper">
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <Logo />
          <div style={{ fontSize: 40, marginBottom: 16 }}>✉️</div>
          <h2>Check your email</h2>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Account created! We've sent a verification link to <strong>{email}</strong>.
            Please verify your email before signing in.
          </p>
          <button
            className="btn btn-primary btn-block"
            style={{ marginTop: 24 }}
            onClick={() => switchView('login')}
          >Go to Sign In</button>
        </div>
      </div>
    )
  }

  // Forgot — sent confirmation
  if (view === 'forgot_sent') {
    return (
      <div className="auth-wrapper">
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <Logo />
          <div style={{ fontSize: 40, marginBottom: 16 }}>📬</div>
          <h2>Reset link sent</h2>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Check your email — reset link sent. If you don't see it within a few minutes,
            check your spam folder.
          </p>
          <button
            className="btn btn-primary btn-block"
            style={{ marginTop: 24 }}
            onClick={() => switchView('login')}
          >Back to Sign In</button>
        </div>
      </div>
    )
  }

  // Forgot password form
  if (view === 'forgot') {
    return (
      <div className="auth-wrapper">
        <div className="auth-card">
          <BackToLogin />
          <Logo />
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <h2>Forgot password?</h2>
            <p className="auth-sub">Enter your email and we'll send a reset link.</p>
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          <form onSubmit={handleForgot}>
            <div className="form-group">
              <label>Email</label>
              <input
                type="email" required
                value={resetEmail}
                onChange={e => setResetEmail(e.target.value)}
                placeholder="you@company.com"
              />
            </div>
            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? <span className="spinner" /> : 'Send reset link'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  // Register form
  if (view === 'register') {
    return (
      <div className="auth-wrapper">
        <div className="auth-card">
          {onBack && (
            <button onClick={onBack} style={{
              background: 'none', border: 'none', color: 'var(--text-muted)',
              cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center',
              gap: 4, marginBottom: 16, padding: 0, fontWeight: 600,
            }}>← Back to Home</button>
          )}
          <Logo />
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <h2>Create account</h2>
            <p className="auth-sub">Start auditing your hiring pipeline</p>
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          <form onSubmit={handleRegister}>
            <div className="form-group">
              <label>Email</label>
              <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
                placeholder="you@company.com" />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
                placeholder="••••••••" minLength={8} />
            </div>
            <div className="form-group">
              <label>Company Name</label>
              <input type="text" required value={company} onChange={e => setCompany(e.target.value)}
                placeholder="Acme Corp" />
            </div>
            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? <span className="spinner" /> : 'Create Account'}
            </button>
          </form>

          <div className="auth-toggle">
            Already have an account?{' '}
            <button onClick={() => switchView('login')}>Sign In</button>
          </div>
        </div>
      </div>
    )
  }

  // Default: Login form
  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        {onBack && (
          <button onClick={onBack} style={{
            background: 'none', border: 'none', color: 'var(--text-muted)',
            cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center',
            gap: 4, marginBottom: 16, padding: 0, fontWeight: 600,
          }}>← Back to Home</button>
        )}
        <Logo />
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <h2>Welcome back</h2>
          <p className="auth-sub">Sign in to your FairHire dashboard</p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label>Email</label>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
              placeholder="you@company.com" />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••" minLength={8} />
            <div style={{ textAlign: 'right', marginTop: 6 }}>
              <button
                type="button"
                onClick={() => switchView('forgot')}
                style={{
                  background: 'none', border: 'none', color: 'var(--text-muted)',
                  cursor: 'pointer', fontSize: 12.5, padding: 0, fontWeight: 500,
                }}
              >Forgot password?</button>
            </div>
          </div>
          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? <span className="spinner" /> : 'Sign In'}
          </button>
        </form>

        <div className="auth-toggle">
          Don't have an account?{' '}
          <button onClick={() => switchView('register')}>Sign Up</button>
        </div>
      </div>
    </div>
  )
}
