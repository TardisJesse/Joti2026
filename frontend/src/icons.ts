// Local SVGs keep activity symbols crisp and independent of icon-font loading.
export function objectIcon(type: string): string {
  const paths = type === 'PUZZLE'
    ? '<path d="M9 8a3 3 0 1 1 5 2c-2 1-2 2-2 3"/><circle cx="12" cy="17" r=".7" fill="currentColor"/>'
    : type === 'CAPTURE_POINT'
    ? '<path d="m7 21 5-13 5 13M9 16h6M8 21h8M5 4a8 8 0 0 0 0 10M19 4a8 8 0 0 1 0 10M8 6a4 4 0 0 0 0 6M16 6a4 4 0 0 1 0 6"/><circle cx="12" cy="8" r="1.5"/>'
    : type === 'SCANNER_POINT'
    ? '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="m12 12 6-6M12 3v2M21 12h-2M12 21v-2M3 12h2"/><circle cx="8" cy="14" r="1" fill="currentColor"/>'
    : type === 'PHOTO_POINT'
    ? '<path d="M3 7h4l2-3h6l2 3h4v13H3z"/><circle cx="12" cy="13" r="4"/>'
    : '<path d="M4 13c-3 7 13 10 16 1h-5V9a4 4 0 1 0-8 0v4zM15 9h5l-5 2"/><circle cx="12" cy="8" r=".7" fill="currentColor"/>'
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`
}
