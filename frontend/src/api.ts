// Keep browser traffic on the same origin. Vite forwards /api and /ws to the
// backend container in development, which also works when Windows accesses WSL
// through its IP address rather than localhost forwarding.
const base = import.meta.env.VITE_API_URL || ''
export const token = () => localStorage.getItem('cyberjoti-token')
export async function api(path: string, options: RequestInit = {}) {
  const response = await fetch(`${base}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(token() ? { Authorization: `Bearer ${token()}` } : {}), ...options.headers } })
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Verzoek mislukt')
  return response.json()
}
export const wsUrl = () => {
  if (base) return base.replace(/^http/, 'ws') + '/ws/game?token=' + encodeURIComponent(token() || '')
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return protocol + '//' + window.location.host + '/ws/game?token=' + encodeURIComponent(token() || '')
}
