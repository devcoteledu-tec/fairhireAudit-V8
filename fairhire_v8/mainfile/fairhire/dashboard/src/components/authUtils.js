/**
 * authUtils.js — FairHire v2.1 auth helpers
 *
 * Auth is cookie-based (HttpOnly fh_access + fh_refresh).
 * CSRF token is stored in memory (not document.cookie) because this
 * frontend (Vercel) and backend (Render) are different origins — JS on
 * Vercel cannot read cookies set by Render via document.cookie.
 * The backend returns csrf_token in the /api/login response body; we
 * store it here and attach it as X-CSRF-Token on every mutating request.
 */

const _BASE = import.meta.env.VITE_API_URL || ''
const LOGIN_PATH = '/'

// In-memory CSRF token — set on login, cleared on logout.
// Never stored in localStorage/sessionStorage (XSS risk).
let _csrfToken = ''

/** Called by App.jsx after a successful login with the data from /api/login */
export function setCsrfToken(token) {
  _csrfToken = token || ''
}

/** Returns the current in-memory CSRF token */
export function getCsrfToken() {
  return _csrfToken
}

/**
 * Thin fetch wrapper that always sends cookies and attaches the CSRF header
 * on mutating requests. Retries once on 401 via /api/refresh.
 */
export async function authFetch(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const needsCsrf = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)

  const opts = {
    ...options,
    credentials: 'include',
    headers: {
      ...(options.headers || {}),
      ...(needsCsrf && _csrfToken ? { 'X-CSRF-Token': _csrfToken } : {}),
    },
  }

  let res = await fetch(url, opts)
  if (res.status !== 401) return res

  // Silent token refresh on 401
  try {
    const refreshRes = await fetch(`${_BASE}/api/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'X-CSRF-Token': _csrfToken },
    })

    if (!refreshRes.ok) {
      _csrfToken = ''
      window.location.href = LOGIN_PATH
      return new Response(JSON.stringify({ detail: 'Session expired' }), { status: 401 })
    }

    // Refresh rotates the CSRF cookie — but since we can't read it via
    // document.cookie, the in-memory token becomes stale here.
    // The server will accept the old CSRF value for the retry below because
    // the refresh endpoint itself doesn't require CSRF (it uses the HttpOnly
    // fh_refresh cookie which is already CSRF-safe by nature).
  } catch {
    _csrfToken = ''
    window.location.href = LOGIN_PATH
    return new Response(JSON.stringify({ detail: 'Session expired' }), { status: 401 })
  }

  res = await fetch(url, opts)
  if (res.status === 401) {
    _csrfToken = ''
    window.location.href = LOGIN_PATH
  }
  return res
}

/**
 * Logout — clear in-memory token, call /api/logout, redirect.
 */
export async function logout() {
  try {
    await authFetch(`${_BASE}/api/logout`, { method: 'POST' })
  } catch {
    // proceed to login regardless
  }
  _csrfToken = ''
  window.location.href = LOGIN_PATH
}

/**
 * Check if user is logged in. Returns user object or null.
 */
export async function isLoggedIn() {
  try {
    const res = await fetch(`${_BASE}/api/me`, { credentials: 'include' })
    if (res.ok) return await res.json()
    return null
  } catch {
    return null
  }
}

// Legacy stubs — kept so existing imports don't break
export function authHeaders(extra = {}) { return { ...extra } }
export function authHeadersMultipart() { return {} }
export function handleUnauthorized(res) {
  if (res.status === 401) { window.location.href = LOGIN_PATH; return true }
  return false
}
