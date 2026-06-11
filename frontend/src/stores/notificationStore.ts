import { useSyncExternalStore } from "react"

/**
 * SedimentNotification represents an agent response that arrived while
 * the participant was elsewhere (different conversation or different node).
 *
 * This store is a pure JS module — calling addNotification() causes
 * zero re-renders in the caller. Only components that subscribe via
 * useNotifications() will re-render.
 */
export interface SedimentNotification {
  id: string
  conversationId: string
  messageId: number
  parentMessageId?: number
  timestamp: string
  snippet: string
  speaker: string
}

type Listener = () => void

let notifications: SedimentNotification[] = []
const listeners = new Set<Listener>()

function emitChange() {
  for (const listener of listeners) {
    listener()
  }
}

function subscribe(listener: Listener) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

function getSnapshot(): SedimentNotification[] {
  return notifications
}

/**
 * Add a notification. Can be called from any hook, callback, or module.
 * Does NOT trigger React re-renders in the caller — only subscribers re-render.
 */
export function addNotification(notif: Omit<SedimentNotification, "id">) {
  const id = `${notif.conversationId}-${notif.messageId}`
  if (notifications.some((n) => n.id === id)) return
  notifications = [{ ...notif, id }, ...notifications]
  emitChange()
}

/**
 * Dismiss a single notification by its ID.
 */
export function dismissNotification(id: string) {
  const next = notifications.filter((n) => n.id !== id)
  if (next.length !== notifications.length) {
    notifications = next
    emitChange()
  }
}

/**
 * Dismiss a notification matching a specific conversation + message pair.
 * Called automatically when the participant navigates to a node that matches.
 */
export function dismissByMatch(conversationId: string, messageId: number) {
  const matchId = `${conversationId}-${messageId}`
  const next = notifications.filter((n) => n.id !== matchId)
  if (next.length !== notifications.length) {
    notifications = next
    emitChange()
  }
}

/**
 * Clear all notifications.
 */
export function clearAllNotifications() {
  if (notifications.length === 0) return
  notifications = []
  emitChange()
}

/**
 * React hook to subscribe to notifications.
 * Only components using this hook re-render when notifications change.
 */
export function useNotifications(): SedimentNotification[] {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
}
