import { useCallback, useEffect, useRef, useState } from "react"
import type { ConversationInfo } from "../api/client"
import {
  listConversations,
  deleteConversation as deleteConvApi,
  getConversation,
  renameConversation as renameConvApi,
  generateConversationTitle as generateTitleApi,
} from "../api/client"

const POLL_INTERVAL_MS = 30_000

export function useConversations() {
  const [conversations, setConversations] = useState<ConversationInfo[]>([])
  const [activeId, setActiveId] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const initialized = useRef(false)
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const activeIdRef = useRef(activeId)

  useEffect(() => {
    activeIdRef.current = activeId
  }, [activeId])

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listConversations()
      setConversations(data.conversations)
      if (!activeIdRef.current && data.conversations.length > 0) {
        setActiveId(data.conversations[0].id)
      }
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [])

  const silentRefresh = useCallback(async () => {
    try {
      const data = await listConversations()
      setConversations(data.conversations)
    } catch {
      // silent
    }
  }, [])

  // Initial fetch
  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true
      refresh()
    }
  }, [refresh])

  // Periodic polling + visibility change
  useEffect(() => {
    const startPolling = () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current)
      pollTimerRef.current = setInterval(() => {
        if (!document.hidden) {
          silentRefresh()
        }
      }, POLL_INTERVAL_MS)
    }

    const handleVisibility = () => {
      if (!document.hidden) {
        silentRefresh()
        startPolling()
      } else {
        if (pollTimerRef.current) {
          clearInterval(pollTimerRef.current)
          pollTimerRef.current = null
        }
      }
    }

    startPolling()
    document.addEventListener("visibilitychange", handleVisibility)

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current)
      document.removeEventListener("visibilitychange", handleVisibility)
    }
  }, [silentRefresh])

  const selectConversation = useCallback((id: string) => {
    setActiveId(id)
  }, [])

  const deleteConversation = useCallback(async (id: string) => {
    try {
      await deleteConvApi(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (activeId === id) {
        const remaining = conversations.filter((c) => c.id !== id)
        setActiveId(remaining.length > 0 ? remaining[0].id : "")
      }
    } catch {
      // silent
    }
  }, [activeId, conversations])

  const addConversation = useCallback((conv: ConversationInfo) => {
    setConversations((prev) => {
      const exists = prev.find((c) => c.id === conv.id)
      if (exists) return prev.map((c) => (c.id === conv.id ? conv : c))
      return [conv, ...prev]
    })
    if (!activeId) {
      setActiveId(conv.id)
    }
  }, [activeId])

  const newConversation = useCallback(() => {
    setActiveId("")
  }, [])

  const refreshTitle = useCallback(async (id: string) => {
    try {
      const updated = await getConversation(id)
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: updated.title } : c))
      )
    } catch {
      // silent
    }
  }, [])

  const renameConversation = useCallback(async (id: string, title: string) => {
    try {
      await renameConvApi(id, title)
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title } : c))
      )
    } catch {
      // silent
    }
  }, [])

  const generateTitle = useCallback(async (id: string) => {
    try {
      const updated = await generateTitleApi(id)
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: updated.title } : c))
      )
      return updated.title
    } catch {
      return null
    }
  }, [])

  return {
    conversations,
    activeId,
    setActiveId: selectConversation,
    loading,
    refresh,
    deleteConversation,
    addConversation,
    newConversation,
    refreshTitle,
    renameConversation,
    generateTitle,
  }
}
