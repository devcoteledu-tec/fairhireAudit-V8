import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const API = import.meta.env.VITE_API_URL || ''

export default function VerifyEmailPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState('loading') // 'loading' | 'success' | 'error' | 'no-token'
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get('token')

    if (!token) {
      setStatus('no-token')
      return
    }

    fetch(`${API}/api/verify-email?token=${encodeURIComponent(token)}`, {
      method: 'GET',
      credentials: 'include',
    })
      .then(async (res) => {
        if (res.ok) {
          setStatus('success')
        } else {
          let msg = 'Verification failed. The link may have expired.'
          try {
            const data = await res.json()
            if (data?.detail?.error) msg = data.detail.error
          } catch {}
          setErrorMsg(msg)
          setStatus('error')
        }
      })
      .catch(() => {
        setErrorMsg('Network error. Please check your connection and try again.')
        setStatus('error')
      })
  }, [])

  return (
    <div className="auth-wrapper">
      <div className="auth-card" style={{ textAlign: 'center' }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginBottom: 28 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 8,
            background: 'linear-gradient(135deg, var(--blue-600), var(--emerald-500))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontWeight: 800, fontSize: 15,
          }}>FH</div>
          <span style={{ fontWeight: 700, fontSize: 18, letterSpacing: '-.3px' }}>FairHire</span>
        </div>

        {/* Loading */}
        {status === 'loading' && (
          <>
            <div style={{
              width: 56, height: 56, borderRadius: '50%',
              border: '3px solid var(--border)',
              borderTopColor: 'var(--blue-500)',
              animation: 'spin 0.8s linear infinite',
              margin: '0 auto 20px',
            }} />
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Verifying your email…</h2>
            <p className="auth-sub">This will only take a moment.</p>
          </>
        )}

        {/* No token */}
        {status === 'no-token' && (
          <>
            <div style={{ fontSize: 52, marginBottom: 16 }}>🔗</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Invalid verification link</h2>
            <p className="auth-sub" style={{ marginBottom: 24 }}>
              This link is missing a verification token. Please use the link from your email.
            </p>
            <button className="btn btn-primary btn-block" onClick={() => navigate('/')}>
              Back to home
            </button>
          </>
        )}

        {/* Success */}
        {status === 'success' && (
          <>
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              background: 'var(--emerald-50)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 20px',
              fontSize: 32,
            }}>✅</div>
            <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, color: 'var(--emerald-700,#065f46)' }}>
              Email verified!
            </h2>
            <p className="auth-sub" style={{ marginBottom: 28 }}>
              Your email address has been confirmed. You can now sign in to your account.
            </p>
            <button className="btn btn-primary btn-block" onClick={() => navigate('/')}>
              Sign in
            </button>
          </>
        )}

        {/* Error */}
        {status === 'error' && (
          <>
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              background: 'var(--rose-50)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 20px',
              fontSize: 32,
            }}>❌</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8, color: 'var(--rose-700)' }}>
              Verification failed
            </h2>
            <div className="alert alert-error" style={{ textAlign: 'left', marginBottom: 24 }}>
              {errorMsg}
            </div>
            <button className="btn btn-primary btn-block" onClick={() => navigate('/')}>
              Back to home
            </button>
          </>
        )}
      </div>

      {/* Spinner keyframes injected inline so no extra CSS file needed */}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
