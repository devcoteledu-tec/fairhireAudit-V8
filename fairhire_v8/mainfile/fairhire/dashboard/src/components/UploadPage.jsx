import React, { useState, useRef } from 'react'
import { authFetch } from './authUtils'

// ── Upgrade Modal ─────────────────────────────────────────────────────────────
function UpgradeModal({ onClose, apiBase }) {
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  const handleUpgrade = async () => {
    setLoading(true)
    setError('')
    try {
      const r = await authFetch(`${apiBase}/api/create-checkout-session`, {
        method: 'POST',
      })
      const d = await r.json()
      if (!r.ok) {
        const msg = typeof d.detail === 'object' ? d.detail?.error : d.detail
        throw new Error(msg || 'Could not start checkout')
      }
      // Redirect to Stripe Checkout
      window.location.href = d.url
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 16,
    }}>
      <div style={{
        background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)',
        boxShadow: '0 24px 64px rgba(0,0,0,0.3)',
        width: '100%', maxWidth: 560, padding: 32,
        border: '1px solid var(--border)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>You've hit the Free plan limit</h2>
            <p style={{ margin: '6px 0 0', color: 'var(--text-secondary)', fontSize: 14 }}>
              Upgrade to Pro for unlimited audits + PDF reports
            </p>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 20,
                     color: 'var(--text-muted)', padding: '0 4px', lineHeight: 1 }}
            aria-label="Close"
          >×</button>
        </div>

        {/* Plan comparison table */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
          gap: 1, background: 'var(--border)',
          borderRadius: 'var(--radius-md)', overflow: 'hidden',
          marginBottom: 24, fontSize: 13,
        }}>
          {/* Header row */}
          {['Feature', 'Free', 'Pro'].map((h, i) => (
            <div key={h} style={{
              background: i === 2 ? 'var(--blue-600)' : 'var(--bg-muted)',
              color: i === 2 ? '#fff' : 'var(--text-primary)',
              padding: '10px 14px', fontWeight: 700,
            }}>{h}</div>
          ))}

          {/* Rows */}
          {[
            ['Monthly audits',  '5 / month', 'Unlimited'],
            ['PDF reports',     '✗',          '✓'],
            ['Audit history',   '✓',          '✓'],
            ['All bias modules','✓',          '✓'],
            ['Priority support','✗',          '✓'],
          ].map(([label, free, pro]) => (
            <React.Fragment key={label}>
              <div style={{ background: 'var(--bg-card)', padding: '10px 14px', color: 'var(--text-secondary)' }}>{label}</div>
              <div style={{ background: 'var(--bg-card)', padding: '10px 14px', color: free === '✗' ? 'var(--rose-500)' : 'var(--text-primary)', textAlign: 'center' }}>{free}</div>
              <div style={{ background: 'var(--bg-card)', padding: '10px 14px', color: pro   === '✓' ? 'var(--green-600,#16a34a)' : 'var(--text-primary)', textAlign: 'center', fontWeight: pro === '✓' ? 600 : 400 }}>{pro}</div>
            </React.Fragment>
          ))}
        </div>

        {error && (
          <div className="alert alert-error" style={{ marginBottom: 16 }}>⚠️ {error}</div>
        )}

        {/* CTA */}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
          <button className="btn" onClick={onClose} disabled={loading}
            style={{ background: 'var(--bg-muted)', color: 'var(--text-secondary)' }}>
            Maybe later
          </button>
          <button className="btn btn-primary" onClick={handleUpgrade} disabled={loading}
            style={{ minWidth: 180, fontWeight: 700 }}>
            {loading
              ? <><span className="spinner" /> Redirecting…</>
              : '⚡ Upgrade to Pro'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── UploadPage ────────────────────────────────────────────────────────────────
export default function UploadPage({ apiBase, user, onAuditComplete }) {
  const [file, setFile]           = useState(null)
  const [dragOver, setDragOver]   = useState(false)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')
  const [progress, setProgress]   = useState('')
  const [showUpgrade, setShowUpgrade] = useState(false)
  const inputRef = useRef()

  const handleFile = (f) => {
    if (!f) return
    if (!f.name.endsWith('.csv')) {
      setError('Please upload a .csv file')
      if (inputRef.current) inputRef.current.value = ''   // FIX: clear stale input value
      return
    }
    setFile(f)
    setError('')
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files[0]
    if (!dropped) {
      setError('No file detected. Please drop a CSV file.')
      return
    }
    handleFile(dropped)
  }

  const handleSubmit = async () => {
    if (!file) return
    setLoading(true)
    setError('')
    setProgress('Uploading CSV...')

    try {
      const form = new FormData()
      form.append('file', file)

      setProgress('Running bias audit engine...')

      const r = await authFetch(`${apiBase}/api/audit`, {
        method: 'POST',
        body: form,
      })

      // BILL-1 — free plan limit hit
      if (r.status === 402) {
        setShowUpgrade(true)
        setProgress('')
        return
      }

      if (!r.ok) {
        const d = await r.json().catch(() => ({}))
        const msg = typeof d.detail === 'object' ? d.detail?.error : d.detail
        throw new Error(msg || `Audit failed (HTTP ${r.status})`)
      }

      const result = await r.json()
      setProgress('Audit complete!')
      setTimeout(() => onAuditComplete(result), 500)
    } catch (err) {
      setError(err.message)
      setProgress('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {showUpgrade && (
        <UpgradeModal
          apiBase={apiBase}
          onClose={() => setShowUpgrade(false)}
        />
      )}

      <div className="page-header">
        <div>
          <h2>New Fairness Audit</h2>
          <p>Upload your hiring pipeline CSV to analyse for bias</p>
        </div>
      </div>

      {error && <div className="alert alert-error">⚠️ {error}</div>}

      <div className="card" style={{ maxWidth: 700, margin: '0 auto' }}>
        <div
          className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input ref={inputRef} type="file" accept=".csv" hidden
            onChange={e => handleFile(e.target.files[0])} />
          <div className="upload-icon">📁</div>
          {file ? (
            <>
              <h3>✓ {file.name}</h3>
              <p>{(file.size / 1024).toFixed(1)} KB — Ready to audit</p>
            </>
          ) : (
            <>
              <h3>Drop your CSV here</h3>
              <p>or click to browse. Must include: gender, shortlisted, hired columns</p>
            </>
          )}
        </div>

        {file && (
          <div style={{ marginTop: 20, textAlign: 'center' }}>
            <button className="btn btn-primary" onClick={handleSubmit} disabled={loading}
              style={{ minWidth: 200 }}>
              {loading ? (
                <><span className="spinner" /> {progress}</>
              ) : (
                '🔬 Run Fairness Audit'
              )}
            </button>
          </div>
        )}

        <div style={{ marginTop: 28, padding: '20px', background: 'var(--bg-muted)', borderRadius: 'var(--radius-md)' }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10, color: 'var(--text-primary)' }}>
            Required CSV Columns
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 20px', fontSize: 12.5, color: 'var(--text-secondary)' }}>
            {['gender', 'shortlisted', 'hired', 'disability (optional)', 'age (optional)', 'caste/category (optional)',
              'skin_tone (optional)', 'referral_source (optional)', 'marital_status (optional)', 'institution (optional)']
              .map(c => <span key={c}>• {c}</span>)}
          </div>
        </div>
      </div>
    </>
  )
}
