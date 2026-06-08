import React, { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import './index.css'
import AuthPage from './components/AuthPage'
import Sidebar from './components/Sidebar'
import UploadPage from './components/UploadPage'
import Dashboard from './components/Dashboard'
import HistoryPage from './components/HistoryPage'
import HomePage from './components/HomePage'
import VerifyEmailPage from './components/VerifyEmailPage'
import ResetPasswordPage from './components/ResetPasswordPage'
import { authFetch, logout, isLoggedIn } from './components/authUtils'

const API = import.meta.env.VITE_API_URL || ''

// ── ErrorBoundary ─────────────────────────────────────────────────────────────
// Catches any unhandled render/lifecycle error thrown by child components
// (e.g. Chart.js crash on unexpected null API data) and shows a friendly
// recovery card instead of a silent white screen.
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    // Console logging is sufficient; Sentry is already wired on the backend.
    console.error('[FairHire ErrorBoundary] Uncaught render error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          minHeight: '100vh', background: '#f8fafc', padding: '2rem',
        }}>
          <div style={{
            background: '#fff', border: '1px solid #e2e8f0', borderRadius: '12px',
            padding: '2.5rem 3rem', maxWidth: '480px', textAlign: 'center',
            boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
          }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>⚠️</div>
            <h2 style={{ margin: '0 0 0.75rem', color: '#1e293b', fontSize: '1.25rem' }}>
              Something went wrong
            </h2>
            <p style={{ color: '#64748b', margin: '0 0 1.5rem', lineHeight: 1.6 }}>
              An unexpected error occurred while rendering the page. This has been
              logged automatically. Please reload to continue.
            </p>
            {this.state.error && (
              <pre style={{
                background: '#f1f5f9', borderRadius: '6px', padding: '0.75rem',
                fontSize: '0.75rem', color: '#475569', textAlign: 'left',
                overflowX: 'auto', marginBottom: '1.5rem', whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}>
                {this.state.error.message}
              </pre>
            )}
            <button
              onClick={() => window.location.reload()}
              style={{
                background: '#3b82f6', color: '#fff', border: 'none',
                borderRadius: '8px', padding: '0.6rem 1.5rem', fontSize: '0.95rem',
                cursor: 'pointer', fontWeight: 600,
              }}
            >
              Reload page
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

// ── ProtectedRoute ────────────────────────────────────────────────────────────
function ProtectedRoute({ user, children, onShowAuth }) {
  if (!user) {
    onShowAuth()
    return <Navigate to="/" replace />
  }
  return children
}

// ── AppShell ──────────────────────────────────────────────────────────────────
// Rendered only when user is logged in; wraps Sidebar + routed content.
function AppShell({ user, setUser, auditResult, setAuditResult, history, fetchHistory, onLogout }) {
  const navigate = useNavigate()

  const handleAuditComplete = (result) => {
    setAuditResult(result)
    fetchHistory()
    navigate('/dashboard')
  }

  const handleViewAudit = (audit) => {
    setAuditResult(audit)
    navigate('/dashboard')
  }

  // Derive current "page" name from path for Sidebar active state
  const pathToPage = (pathname) => {
    if (pathname === '/') return 'home'
    return pathname.replace(/^\//, '')
  }

  return (
    <div className="app-shell">
      <Sidebar
        user={user}
        apiBase={API}
        onLogout={onLogout}
        hasResult={!!auditResult}
      />
      <main className="main-content">
        <Routes>
          {/* Public email-flow routes — accessible while logged in too */}
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />

          <Route
            path="/"
            element={<HomePage isGuest={false} onStartApp={() => navigate('/upload')} />}
          />
          <Route
            path="/upload"
            element={
              <ProtectedRoute user={user} onShowAuth={() => {}}>
                <UploadPage apiBase={API} user={user} onAuditComplete={handleAuditComplete} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute user={user} onShowAuth={() => {}}>
                {auditResult
                  ? <Dashboard data={auditResult} apiBase={API} />
                  : <Navigate to="/upload" replace />}
              </ProtectedRoute>
            }
          />
          <Route
            path="/history"
            element={
              <ProtectedRoute user={user} onShowAuth={() => {}}>
                <HistoryPage history={history} onView={handleViewAudit} onRefresh={fetchHistory} />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  // user is { id, email, company_name } or null — populated by /api/me ping, NOT localStorage
  const [user, setUser] = useState(null)
  const [authChecked, setAuthChecked] = useState(false)
  const [showAuth, setShowAuth] = useState(false)
  const [auditResult, setAuditResult] = useState(null)
  const [history, setHistory] = useState([])

  // On mount, verify the cookie session is still alive
  useEffect(() => {
    isLoggedIn().then((u) => {
      if (u) {
        setUser(u)
        fetchHistory()
      }
      setAuthChecked(true)
    })
  }, [])

  const fetchHistory = async () => {
    try {
      const r = await authFetch(`${API}/api/history`)
      if (r.ok) {
        setHistory(await r.json())
      } else {
        console.error('fetchHistory: server error', r.status)
      }
    } catch (e) {
      console.error('fetchHistory: network error', e)
    }
  }

  const handleLogin = (u) => {
    setUser(u)
    setShowAuth(false)
    // Fetch full user info from /api/me to populate id + company_name
    isLoggedIn().then((me) => { if (me) setUser(me) })
    fetchHistory()
  }

  const handleLogout = async () => {
    await logout()
    setUser(null)
    setAuditResult(null)
    setShowAuth(false)
  }

  // Wait for the /api/me check before rendering to avoid a flash of the login page
  if (!authChecked) return null

  if (!user) {
    if (showAuth) {
      return <AuthPage apiBase={API} onLogin={handleLogin} onBack={() => setShowAuth(false)} />
    }
    return (
      <Routes>
        {/* Public email-flow routes — accessible without being logged in */}
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="*" element={<HomePage isGuest={true} onStartApp={() => setShowAuth(true)} />} />
      </Routes>
    )
  }

  return (
    <ErrorBoundary>
      <AppShell
        user={user}
        setUser={setUser}
        auditResult={auditResult}
        setAuditResult={setAuditResult}
        history={history}
        fetchHistory={fetchHistory}
        onLogout={handleLogout}
      />
    </ErrorBoundary>
  )
}
