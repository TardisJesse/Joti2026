export function timerSeconds(game: any, serverNow: number): number | null {
  if (!game) return null
  if (game.status === 'PAUSED' && game.timer_remaining_seconds != null) return Math.max(0, game.timer_remaining_seconds)
  if (!game.ends_at) return null
  const deadline = Date.parse(game.ends_at)
  return Number.isFinite(deadline) ? Math.max(0, Math.ceil((deadline - serverNow) / 1000)) : null
}
export function formatTimer(seconds: number | null): string {
  if (seconds == null) return '—'
  const pad = (value: number) => String(value).padStart(2, '0')
  const hours = Math.floor(seconds / 3600), minutes = Math.floor(seconds % 3600 / 60)
  return (hours ? pad(hours) + ':' : '') + pad(minutes) + ':' + pad(seconds % 60)
}
