/**
 * Centralized date/time formatting utilities.
 * All functions use the system's local timezone (no UTC hardcoding).
 */

/**
 * Format ISO string → "HH:MM:SS" (24h, system local time)
 */
export function formatTime(isoString?: string | null): string {
  if (!isoString) return ''
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return isoString
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  } catch {
    return isoString
  }
}

/**
 * Format ISO string → "HH:MM" (24h short, system local time)
 */
export function formatTimeShort(isoString?: string | null): string {
  if (!isoString) return ''
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return isoString
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
  } catch {
    return isoString
  }
}

/**
 * Format ISO string → "MMM DD, HH:MM" (e.g. "Jun 15, 18:57", system local time)
 */
export function formatDateTime(isoString?: string | null): string {
  if (!isoString) return ''
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return isoString
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  } catch {
    return isoString
  }
}

/**
 * Format ISO string → full locale string (date + time, system local time)
 */
export function formatDateTimeFull(isoString?: string | null): string {
  if (!isoString) return ''
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return isoString
    return d.toLocaleString()
  } catch {
    return isoString
  }
}

/**
 * Format ISO string → "YYYY-MM-DD HH:MM:SS" (system local time, NOT UTC)
 */
export function formatTimestamp(isoString?: string | null): string {
  if (!isoString) return ''
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return isoString
    const y = d.getFullYear()
    const mo = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const h = String(d.getHours()).padStart(2, '0')
    const mi = String(d.getMinutes()).padStart(2, '0')
    const s = String(d.getSeconds()).padStart(2, '0')
    return `${y}-${mo}-${day} ${h}:${mi}:${s}`
  } catch {
    return isoString
  }
}

/**
 * Format ISO string → relative time (e.g. "3m ago", "2h ago")
 */
export function formatRelativeTime(isoString?: string | null): string {
  if (!isoString) return ''
  const now = Date.now()
  const then = new Date(isoString).getTime()
  if (isNaN(then)) return isoString
  const diffMs = now - then
  if (diffMs < 0) return 'just now'
  const seconds = Math.floor(diffMs / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}
