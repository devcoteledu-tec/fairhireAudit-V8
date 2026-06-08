import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const API = import.meta.env.VITE_API_URL || ''

export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [token, setToken] = useState(null)
  const [noToken, setNoToken] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [validationError, setValidationError] = useState('')
  const [status, setStatus] = useState('idle') // 'idle' | 'loading' | 'success' | 'error'
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get('token')
    if (!t) {
      setNoToken(true)
    } else {
      setToken(t)
    }
  }, [])

  const handleSubmit = async () => {
    if (!token) {
      setValidationError('Reset token is missing. Please use the link from your email.')
      return
    }
    setValidationError('')

    if (newPassword.length < 8) {
      setValidationError('Password must be at least 8 characters.')
      return
    }
    if (newPassword !== confirmPassword) {
      setValidationError('Passwords do not match.')
      return
    }

    setStatus('loading')

    try {
      const res = await fetch(`${API}/api/reset-password`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: newPassword }),
      })

      if (res.ok) {
        setStatus('success')
      } else {
        let msg = 'Password reset failed. The link may have expired.'
        try {
          const data = await res.json()
          if (data?.detail?.error) msg = data.detail.error
        } catch {}
        setErrorMsg(msg)
        setStatus('error')
      }
    } catch {
      setErrorMsg('Network error. Please check your connection and try again.')
      setStatus('error')
    }
  }

  // ── No token ──────────────────────────────────────────────────────────────
  if (noToken) {
    return (
      <div className="auth-wrapper">
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <BrandLogo />
          <div style={{ fontSize: 52, marginBottom: 16 }}>🔗</div>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Invalid reset link</h2>
          <p className="auth-sub" style={{ marginBottom: 24 }}>
            This link is missing a reset token. Please use the link from your email.
          </p>
          <button className="btn btn-primary btn-block" onClick={() => navigate('/')}>
            Back to home
          </button>
        </div>
      </div>
    )
  }

  // ── Success ───────────────────────────────────────────────────────────────
  if (status === 'success') {
    return (
      <div className="auth-wrapper">
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <BrandLogo />
          <div style={{
            width: 64, height: 64, borderRadius: '50%',
            background: 'var(--emerald-50)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 20px', fontSize: 32,
          }}>✅</div>
          <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, color: 'var(--emerald-700,#065f46)' }}>
            Password updated!
          </h2>
          <p className="auth-sub" style={{ marginBottom: 28 }}>
            Your password has been reset. You can now sign in with your new password.
          </p>
          <button className="btn btn-primary btn-block" onClick={() => navigate('/')}>
            Sign in
          </button>
        </div>
      </div>
    )
  }

  // ── Form ──────────────────────────────────────────────────────────────────
  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <BrandLogo />
        <h2>Reset your password</h2>
        <p className="auth-sub">Enter a new password for your account.</p>

        {/* Server error banner */}
        {status === 'error' && (
          <div className="alert alert-error" style={{ marginBottom: 18 }}>
            {errorMsg}
          </div>
        )}

        {/* Validation error */}
        {validationError && (
          <div className="alert alert-error" style={{ marginBottom: 18 }}>
            {validationError}
          </div>
        )}

        <div className="form-group">
          <label htmlFor="new-password">New password</label>
          <input
            id="new-password"
            type="password"
            minLength={8}
            placeholder="At least 8 characters"
            value={newPassword}
            onChange={(e) => { setNewPassword(e.target.value); setValidationError('') }}
            disabled={status === 'loading'}
          />
        </div>

        <div className="form-group">
          <label htmlFor="confirm-password">Confirm password</label>
          <input
            id="confirm-password"
            type="password"
            minLength={8}
            placeholder="Repeat your new password"
            value={confirmPassword}
            onChange={(e) => { setConfirmPassword(e.target.value); setValidationError('') }}
            disabled={status === 'loading'}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit() }}
          />
        </div>

        <button
          className="btn btn-primary btn-block"
          onClick={handleSubmit}
          disabled={status === 'loading'}
          style={{ marginTop: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
        >
          {status === 'loading' ? (
            <>
              <span style={{
                width: 16, height: 16, borderRadius: '50%',
                border: '2px solid rgba(255,255,255,0.4)',
                borderTopColor: '#fff',
                display: 'inline-block',
                animation: 'spin 0.8s linear infinite',
              }} />
              Resetting…
            </>
          ) : 'Reset Password'}
        </button>

        <div className="auth-toggle" style={{ marginTop: 20 }}>
          <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--blue-600,#2563eb)', fontSize: 13 }} onClick={() => navigate('/')}>
            Back to home
          </button>
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

function BrandLogo() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginBottom: 28 }}>
      <div style={{
        width: 36, height: 36, borderRadius: 8,
        background: 'linear-gradient(135deg, var(--blue-600), var(--emerald-500))',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#fff', fontWeight: 800, fontSize: 15,
      }}>FH</div>
      <span style={{ fontWeight: 700, fontSize: 18, letterSpacing: '-.3px' }}>FairHire</span>
    </div>
  )
}
