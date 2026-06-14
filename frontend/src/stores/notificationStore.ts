import { useSyncExternalStore } from "react"
import {
  getNotifications,
  createNotification,
  dismissNotification as apiDismissNotification,
  dismissNotificationByMatch,
  clearNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../api/client"
import type { SedimentNotification } from "../api/client"

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
 * Synchronize local state with the backend's active (un-dismissed) notifications.
 */
export async function syncNotifications() {
  try {
    const backendNotifs = await getNotifications(false)
    // Check if anything changed in the list of IDs or read states
    const idsA = notifications.map(n => `${n.id}-${n.read ? 1 : 0}`).join(",")
    const idsB = backendNotifs.map(n => `${n.id}-${n.read ? 1 : 0}`).join(",")
    if (idsA !== idsB) {
      notifications = backendNotifs
      emitChange()
    }
  } catch (err) {
    console.warn("Failed to sync notifications with backend:", err)
  }
}

// Perform initial synchronization
syncNotifications()

// Set up periodic polling every 12 seconds
if (typeof window !== "undefined") {
  setInterval(syncNotifications, 12000)
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

  const newNotif: SedimentNotification = {
    ...notif,
    type,
    id,
    timestamp,
    read: false,
    dismissed: false,
  }

  // Optimistic update
  notifications = [newNotif, ...notifications]
  emitChange()

  // Sync with backend
  createNotification(newNotif)
    .then(() => syncNotifications())
    .catch((err) => console.error("Failed to persist notification on backend:", err))
}

/**
 * Dismiss a single notification by its ID (also marks as read).
 */
export function dismissNotification(id: string) {
  const next = notifications.filter((n) => n.id !== id)
  if (next.length !== notifications.length) {
    notifications = next
    emitChange()
  }

  // Sync with backend — dismiss and also mark as read
  Promise.all([
    apiDismissNotification(id),
    markNotificationRead(id),
  ])
    .then(() => syncNotifications())
    .catch((err) => console.error("Failed to dismiss notification on backend:", err))
}

/**
 * Dismiss a notification matching a specific conversation + message pair.
 */
export function dismissByMatch(conversationId: string, messageId: number) {
  const next = notifications.filter(
    (n) => !(n.conversationId === conversationId && n.messageId === messageId)
  )
  if (next.length !== notifications.length) {
    notifications = next
    emitChange()
  }

  // Sync with backend using the new dismiss-match API
  dismissNotificationByMatch(conversationId, messageId)
    .then(() => syncNotifications())
    .catch((err) => console.error("Failed to dismiss notification by match on backend:", err))
}

/**
 * Clear all notifications.
 */
export function clearAllNotifications() {
  if (notifications.length === 0) return
  notifications = []
  emitChange()

  // Sync with backend
  clearNotifications()
    .then(() => syncNotifications())
    .catch((err) => console.error("Failed to clear notifications on backend:", err))
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

  // Sync with backend
  clearNotifications(type)
    .then(() => syncNotifications())
    .catch((err) => console.error("Failed to clear notifications by type on backend:", err))
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

  // Sync with backend
  markAllNotificationsRead(type)
    .then(() => syncNotifications())
    .catch((err) => console.error("Failed to mark all read on backend:", err))
}

/**
 * React hook to subscribe to notifications.
 */
export function useNotifications(): SedimentNotification[] {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
}
