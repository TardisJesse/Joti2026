// Keep browser traffic on the same origin. Vite forwards /api and /ws to the
// backend container in development, which also works when Windows accesses WSL
// through its IP address rather than localhost forwarding.
const base = import.meta.env.VITE_API_URL || ''
export const token = () => sessionStorage.getItem('cyberjoti-view-token') || localStorage.getItem('cyberjoti-token')
export function setPlayerToken(value: string) {
  sessionStorage.removeItem('cyberjoti-view-token')
  localStorage.setItem('cyberjoti-token', value)
}
export function clearToken() {
  if (sessionStorage.getItem('cyberjoti-view-token')) sessionStorage.removeItem('cyberjoti-view-token')
  else localStorage.removeItem('cyberjoti-token')
}
export function acceptTeamLink() {
  const invitation = new URLSearchParams(window.location.hash.slice(1)).get('team')
  if (!invitation) return
  sessionStorage.setItem('cyberjoti-view-token', invitation)
  window.history.replaceState(null, '', window.location.pathname + window.location.search)
}
export async function api(path: string, options: RequestInit = {}) {
  const requestToken = token()
  const response = await fetch(`${base}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(requestToken ? { Authorization: `Bearer ${requestToken}` } : {}), ...options.headers } })
  if (!response.ok) {
    if (response.status === 401 && requestToken && requestToken === token() && path !== '/api/auth/login') {
      window.dispatchEvent(new Event('cyberjoti-session-expired'))
    }
    const body = await response.json().catch(() => ({}))
    const detail = body.detail
    const message = Array.isArray(detail)
      ? detail.map((item: any) => `${item.loc?.slice(-1)[0] || 'veld'}: ${item.msg || 'ongeldig'}`).join('; ')
      : typeof detail === 'string' ? detail : 'Verzoek mislukt'
    throw new Error(message)
  }
  return response.json()
}
export const wsUrl = (gameId?: string) => {
  const query = '?v=2&token=' + encodeURIComponent(token() || '') + (gameId ? '&game_id=' + encodeURIComponent(gameId) : '')
  if (base) return base.replace(/^http/, 'ws') + '/ws/game' + query
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return protocol + '//' + window.location.host + '/ws/game' + query
}
