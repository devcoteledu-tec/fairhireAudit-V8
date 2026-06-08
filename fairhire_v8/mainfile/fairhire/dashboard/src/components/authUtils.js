/**
 * authUtils.js — FairHire v2.1 auth helpers
 *
 * Auth is now fully cookie-based (HttpOnly fh_access + fh_refresh).
 * No token is ever stored in localStorage or readable by JS.
 * All authenticated requests use credentials: 'include' so the browser
 * sends the cookies automatically.
 */

const _BASE = import.meta.env.VITE_API_URL || ''

const LOGIN_PATH = '/'

export function getCsrfToken() {
  return document.cookie
    .split('; ')
    .find(row => row.startsWith('fh_csrf='))
    ?.split('=')[1] ?? ''
}

/**
 * Thin fetch wrapper that always sends cookies and retries once on 401
 * by calling /api/refresh. If refresh also fails, redirects to login.
 *
 * @param {string}  url
 * @param {object}  options  Standard fetch options (method, headers, body …)
 * @returns {Promise<Response>}
 */
export async function authFetch(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const needsCsrf = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)
  const opts = {
    ...options,
    credentials: 'include',
    headers: {
      ...(options.headers || {}),
      ...(needsCsrf ? { 'X-CSRF-Token': getCsrfToken() } : {}),
    },
  }

  let res = await fetch(url, opts)

  if (res.status !== 401) return res

  // Attempt a silent token refresh
  try {
    const csrfToken = document.cookie
      .split('; ')
      .find(r => r.startsWith('fh_csrf='))
      ?.split('=')[1] ?? ''
    const refreshRes = await fetch(`${_BASE}/api/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'X-CSRF-Token': csrfToken },
    })

    if (!refreshRes.ok) {
      // Refresh token is expired/invalid — send user to login
      window.location.href = LOGIN_PATH
      // Return a synthetic 401 so callers don't hang
      return new Response(JSON.stringify({ detail: 'Session expired' }), { status: 401 })
    }
  } catch {
    window.location.href = LOGIN_PATH
    return new Response(JSON.stringify({ detail: 'Session expired' }), { status: 401 })
  }

  // Retry the original request with the fresh access cookie
  res = await fetch(url, opts)

  if (res.status === 401) {
    // Still 401 after refresh — give up and redirect
    window.location.href = LOGIN_PATH
  }

  return res
}

/**
 * Call /api/logout to clear server-side cookies, then redirect to login.
 */
export async function logout() {
  try {
    await authFetch(`${_BASE}/api/logout`, { method: 'POST' })
  } catch {
    // Network failure or server error — the browser will discard
    // the cookies on redirect; proceed to login regardless.
    console.warn("[FairHire] logout request failed — redirecting anyway")
  }
  window.location.href = LOGIN_PATH
}

/**
 * Ping /api/me to check whether the access cookie is still valid.
 * Returns the user object { id, email, company_name } on success,
 * or null when unauthenticated.
 *
 * @returns {Promise<object|null>}
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

/**
 * Legacy stub — kept so any remaining import doesn't break at build time.
 * With cookie auth no explicit headers are needed; use authFetch instead.
 * @deprecated
 */
export function authHeaders(extra = {}) {
  return { ...extra }
}

/**
 * Legacy stub — same as above for multipart requests.
 * @deprecated
 */
export function authHeadersMultipart() {
  return {}
}

/**
 * Legacy stub — 401 handling is now inside authFetch.
 * @deprecated
 */
export function handleUnauthorized(res) {
  if (res.status === 401) {
    window.location.href = LOGIN_PATH
    return true
  }
  return false
}
