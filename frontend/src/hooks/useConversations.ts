import { useCallback, useEffect, useRef, useState } from "react"
import type { ConversationInfo } from "../api/client"
import {
  listConversations,
  deleteConversation as deleteConvApi,
  getConversation,
  renameConversation as renameConvApi,
  generateConversationTitle as generateTitleApi,
} from "../api/client"

export function useConversations() {
  const [conversations, setConversations] = useState<ConversationInfo[]>([])
  const [activeId, setActiveId] = useState<string>(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get("c") || ""
  })
  const [loading, setLoading] = useState(false)
  const initialized = useRef(false)

  // Sync active ID state and URL query parameter in sync
  const updateActiveId = useCallback((id: string) => {
    setActiveId(id)
    const params = new URLSearchParams(window.location.search)
    if (id) {
      params.set("c", id)
    } else {
      params.delete("c")
    }
    const newUrl = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`
    window.history.pushState(null, "", newUrl)
  }, [])

  // Sync state on popstate (browser back/forward button clicks)
  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search)
      const id = params.get("c") || ""
      setActiveId(id)
    }
    window.addEventListener("popstate", handlePopState)
    return () => window.removeEventListener("popstate", handlePopState)
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listConversations()
      setConversations(data.conversations)
      const urlId = new URLSearchParams(window.location.search).get("c")
      if (!activeId && !urlId && data.conversations.length > 0) {
        updateActiveId(data.conversations[0].id)
      }
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [activeId, updateActiveId])

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true
      refresh()
    }
  }, [refresh])

  const selectConversation = useCallback((id: string) => {
    updateActiveId(id)
  }, [updateActiveId])

  const deleteConversation = useCallback(async (id: string) => {
    try {
      await deleteConvApi(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (activeId === id) {
        const remaining = conversations.filter((c) => c.id !== id)
        updateActiveId(remaining.length > 0 ? remaining[0].id : "")
      }
    } catch {
      // silent
    }
  }, [activeId, conversations, updateActiveId])

  const addConversation = useCallback((conv: ConversationInfo) => {
    setConversations((prev) => {
      const exists = prev.find((c) => c.id === conv.id)
      if (exists) return prev.map((c) => (c.id === conv.id ? conv : c))
      return [conv, ...prev]
    })
    if (!activeId) {
      updateActiveId(conv.id)
    }
  }, [activeId, updateActiveId])

  const newConversation = useCallback(() => {
    updateActiveId("")
  }, [updateActiveId])

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
