import React from 'react'

export default function HistoryPage({ history, onView, onRefresh }) {
  const scoreColor = (s) => s >= 75 ? '#10b981' : s >= 50 ? '#f59e0b' : '#e11d48'
  const scoreBadge = (s) => s >= 75 ? 'pass' : s >= 50 ? 'warn' : 'fail'

  return (
    <>
      <div className="page-header">
        <div>
          <h2>Audit History</h2>
          <p>{history.length} audit{history.length !== 1 ? 's' : ''} on record</p>
        </div>
        <button className="btn btn-outline" onClick={onRefresh}>🔄 Refresh</button>
      </div>

      {history.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 48, marginBottom: 16, opacity: .4 }}>📋</div>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 6 }}>No audits yet</h3>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Upload a CSV to run your first fairness audit</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {history.map((a, i) => {
            const score = a.fair_hiring_score || a.score || 0
            const flagCount = (a.flags?.length || 0) + (a.caste_flags?.length || 0) +
              (a.skin_flags?.length || 0) + (a.referral_flags?.length || 0) +
              (a.proxy_flags?.length || 0) + (a.marital_flags?.length || 0) +
              (a.institution_flags?.length || 0) + (a.age_flags?.length || 0)

            return (
              <div key={a.id || i} className="card" style={{ cursor: 'pointer', transition: 'all .2s' }}
                onClick={() => onView(a)}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div style={{
                      width: 48, height: 48, borderRadius: 'var(--radius-md)',
                      background: score >= 80 ? 'var(--emerald-50)' : score >= 60 ? 'var(--amber-50)' : 'var(--rose-50)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontWeight: 800, fontSize: 18, color: scoreColor(score),
                    }}>
                      {Math.round(score)}
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>
                        {a.original_filename || 'Audit'}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                        {a.row_count || 0} candidates • {a.computed_at ? new Date(a.computed_at).toLocaleDateString() : '—'}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    {flagCount > 0 && (
                      <span className="badge badge-fail">{flagCount} flag{flagCount > 1 ? 's' : ''}</span>
                    )}
                    <span className={`badge badge-${scoreBadge(score)}`}>
                      {a.score_label || a.label || '—'}
                    </span>
                    <span style={{ color: 'var(--text-muted)', fontSize: 18 }}>→</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}