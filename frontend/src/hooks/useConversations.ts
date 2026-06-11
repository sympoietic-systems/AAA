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
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [totalCount, setTotalCount] = useState(0)

  // Local state cache for the current tags/filters
  const [tag, setTag] = useState<string | undefined>(undefined)
  const [search, setSearch] = useState<string | undefined>(undefined)
  const LIMIT = 20

  const initialized = useRef(false)

  // Sync active ID state and URL query parameter
  const updateActiveId = useCallback((id: string) => {
    setActiveId(id)
    const params = new URLSearchParams(window.location.search)
    if (id) {
      params.set("c", id)
      params.delete("m")
    } else {
      params.delete("c")
      params.delete("m")
    }
    const newUrl = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`
    window.history.pushState(null, "", newUrl)
  }, [])

  // Sync state on popstate (browser back/forward clicks)
  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search)
      const id = params.get("c") || ""
      setActiveId(id)
    }
    window.addEventListener("popstate", handlePopState)
    return () => window.removeEventListener("popstate", handlePopState)
  }, [])

  const refresh = useCallback(async (newTag?: string | null, newSearch?: string) => {
    setLoading(true)
    try {
      const queryTag = newTag !== undefined ? (newTag === null || newTag === "all" ? undefined : newTag) : tag
      const querySearch = newSearch !== undefined ? newSearch : search

      if (newTag !== undefined) setTag(newTag === null || newTag === "all" ? undefined : newTag)
      if (newSearch !== undefined) setSearch(newSearch)

      const data = await listConversations(queryTag, querySearch, LIMIT, 0)
      setConversations(data.conversations)
      setTotalCount(data.total_count || 0)
      setHasMore(!!data.has_more)
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [tag, search])

  const loadMore = useCallback(async () => {
    if (loading || loadingMore || !hasMore) return
    setLoadingMore(true)
    try {
      const currentOffset = conversations.length
      const data = await listConversations(tag, search, LIMIT, currentOffset)
      setConversations((prev) => {
        const existingIds = new Set(prev.map((c) => c.id))
        const filteredNew = data.conversations.filter((c) => !existingIds.has(c.id))
        return [...prev, ...filteredNew]
      })
      setTotalCount(data.total_count || 0)
      setHasMore(!!data.has_more)
    } catch {
      // silent
    } finally {
      setLoadingMore(false)
    }
  }, [loading, loadingMore, hasMore, conversations.length, tag, search])

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true
      // On start, load the first page with no filters
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
      setTotalCount((prev) => Math.max(0, prev - 1))
      if (activeId === id) {
        updateActiveId("")
      }
    } catch {
      // silent
    }
  }, [activeId, updateActiveId])

  const addConversation = useCallback((conv: ConversationInfo) => {
    setConversations((prev) => {
      const exists = prev.find((c) => c.id === conv.id)
      if (exists) return prev.map((c) => (c.id === conv.id ? conv : c))
      return [conv, ...prev]
    })
    setTotalCount((prev) => prev + 1)
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
    loadingMore,
    hasMore,
    totalCount,
    loadMore,
    refresh,
    deleteConversation,
    addConversation,
    newConversation,
    refreshTitle,
    renameConversation,
    generateTitle,
  }
}
