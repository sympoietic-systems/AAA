import { useSyncExternalStore } from "react"

/**
 * SedimentNotification represents a trace fold on the material interface.
 * It can be a 'sediment' arrival (agent message elsewhere), a 'glitch' (error),
 * or a 'trace' (informational system trace).
 */
export interface SedimentNotification {
  id: string
  type: 'sediment' | 'glitch' | 'trace'
  conversationId?: string
  messageId?: number
  parentMessageId?: number
  timestamp: string
  snippet: string
  speaker?: string
  source?: string
  read?: boolean
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
 */
export function addNotification(
  notif: Omit<SedimentNotification, "id" | "type" | "read" | "timestamp"> & {
    id?: string
    type?: 'sediment' | 'glitch' | 'trace'
    timestamp?: string
  }
) {
  const type = notif.type || 'sediment'
  const timestamp = notif.timestamp || new Date().toISOString()
  let id = notif.id
  if (!id) {
    if (type === 'sediment' && notif.conversationId && notif.messageId) {
      id = `${notif.conversationId}-${notif.messageId}`
    } else {
      id = `${type}-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
    }
  }
  if (notifications.some((n) => n.id === id)) return
  
  notifications = [{ ...notif, type, id, timestamp, read: false } as SedimentNotification, ...notifications]
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
 * Clear notifications of a specific type.
 */
export function clearNotificationsByType(type: 'sediment' | 'glitch' | 'trace') {
  const next = notifications.filter((n) => n.type !== type)
  if (next.length !== notifications.length) {
    notifications = next
    emitChange()
  }
}

/**
 * Mark all notifications of a specific type as read.
 */
export function markAllAsRead(type?: 'sediment' | 'glitch' | 'trace') {
  let changed = false
  notifications = notifications.map((n) => {
    if ((!type || n.type === type) && !n.read) {
      changed = true
      return { ...n, read: true }
    }
    return n
  })
  if (changed) {
    emitChange()
  }
}

/**
 * React hook to subscribe to notifications.
 */
export function useNotifications(): SedimentNotification[] {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
}

