/**
 * authUtils.js — FairHire v2.1 auth helpers (FIXED VERSION)
 *
 * Auth is now fully cookie-based (HttpOnly fh_access + fh_refresh).
 * No token is ever stored in localStorage or readable by JS.
 * All authenticated requests use credentials: 'include' so the browser
 * sends the cookies automatically.
 */

const _BASE = import.meta.env.VITE_API_URL || ''

const LOGIN_PATH = '/'

export function getCsrfToken() {
  try {
    const allCookies = document.cookie
    console.log('[CSRF] All cookies:', allCookies)
    
    const csrfCookie = allCookies
      .split('; ')
      .find(row => row.startsWith('fh_csrf='))
    
    console.log('[CSRF] Found cookie:', csrfCookie)
    
    if (!csrfCookie) {
      console.warn('[CSRF] fh_csrf cookie not found')
      return ''
    }
    
    const token = csrfCookie.split('=')[1]
    console.log('[CSRF] Extracted token:', token ? token.substring(0, 20) + '...' : 'EMPTY')
    
    return token || ''
  } catch (err) {
    console.error('[CSRF] Error extracting token:', err)
    return ''
  }
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
  
  const csrfToken = needsCsrf ? getCsrfToken() : ''
  
  console.log(`[AUTH] ${method} ${url}`)
  console.log(`[AUTH] Need CSRF: ${needsCsrf}, Token present: ${!!csrfToken}`)
  
  const opts = {
    ...options,
    credentials: 'include',
    headers: {
      ...(options.headers || {}),
      ...(needsCsrf && csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
    },
  }
  
  console.log('[AUTH] Request headers:', opts.headers)

  let res = await fetch(url, opts)
  
  console.log(`[AUTH] Response status: ${res.status}`)

  if (res.status !== 401) return res

  // Attempt a silent token refresh
  try {
    console.log('[AUTH] Got 401, attempting refresh...')
    const csrfTokenForRefresh = getCsrfToken()
    const refreshRes = await fetch(`${_BASE}/api/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'X-CSRF-Token': csrfTokenForRefresh },
    })

    console.log(`[AUTH] Refresh response: ${refreshRes.status}`)

    if (!refreshRes.ok) {
      // Refresh token is expired/invalid — send user to login
      console.log('[AUTH] Refresh failed, redirecting to login')
      window.location.href = LOGIN_PATH
      // Return a synthetic 401 so callers don't hang
      return new Response(JSON.stringify({ detail: 'Session expired' }), { status: 401 })
    }
  } catch (err) {
    console.error('[AUTH] Refresh error:', err)
    window.location.href = LOGIN_PATH
    return new Response(JSON.stringify({ detail: 'Session expired' }), { status: 401 })
  }

  // Retry the original request with the fresh access cookie
  console.log('[AUTH] Retrying original request...')
  res = await fetch(url, opts)

  console.log(`[AUTH] Retry response: ${res.status}`)

  if (res.status === 401) {
    // Still 401 after refresh — give up and redirect
    console.log('[AUTH] Still 401 after refresh, redirecting to login')
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
