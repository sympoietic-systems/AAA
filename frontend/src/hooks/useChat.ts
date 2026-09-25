import { useConversationFiles } from "./useConversationFiles"
import { useCallback, useEffect, useRef, useState, useMemo } from "react"
import {
  getAgent,
  getHistory,
  saveMessage,
  generateResponse,
  commitBranch,
  getConversationTree,
  getMessagePath,
} from "../api/client"
import type { ChatMessage, ConversationTreeNode, ConversationTreeLink } from "../api/client"
import { addNotification, dismissByMatch } from "../stores/notificationStore"
import { estimateTokens, getAncestorPathIds } from "./useChatHelpers"


export function useChat(conversationId: string) {
  const PAGE_SIZE = 50
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [activeMessageId, setActiveMessageId] = useState<number | null>(() => {
    const params = new URLSearchParams(window.location.search)
    const urlMsgId = params.get("m")
    return urlMsgId ? parseInt(urlMsgId, 10) : null
  })
  const [links, setLinks] = useState<ConversationTreeLink[]>([])
  const [treeNodes, setTreeNodes] = useState<ConversationTreeNode[]>([])
  const [isHistoryLoading, setIsHistoryLoading] = useState(false)
  const [generatingUserMessageIds, setGeneratingUserMessageIds] = useState<Set<number>>(new Set())
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)

  const loading = useMemo(() => {
    return isHistoryLoading || (activeMessageId !== null && generatingUserMessageIds.has(activeMessageId))
  }, [isHistoryLoading, activeMessageId, generatingUserMessageIds])

  const activeMessageIdRef = useRef(activeMessageId)
  useEffect(() => {
    activeMessageIdRef.current = activeMessageId
  }, [activeMessageId])

  useEffect(() => {
    if (conversationId && activeMessageId) {
      dismissByMatch(conversationId, activeMessageId)
    }
  }, [conversationId, activeMessageId])

  const loadedRef = useRef<string>("")
  const lifecycle = useRef(0)
  const fetchTree = useCallback(async (convId: string) => {
    const owner = lifecycle.current
    if (!convId) return
    try {
      const data = await getConversationTree(convId)
      if (owner !== lifecycle.current || loadedRef.current !== convId) return
      setLinks(data.links)
      setTreeNodes(data.nodes)
    } catch (err: unknown) {
      if (owner !== lifecycle.current || loadedRef.current !== convId) return
      setLinks([])
      setTreeNodes([])
      const message = err instanceof Error ? err.message : String(err)
      addNotification({
        type: "glitch",
        snippet: `Failed to load conversation tree nodes: ${message || "Unknown resistance"}`,
        source: "Chat.fetchTree"
      })
    }
  }, [])
  const [error, setError] = useState<string | null>(null)
  const [agentName, setAgentName] = useState("...")
  const [history, setHistory] = useState<{ id: number; speaker: string; snippet: string }[]>([])

  const [renderedConversation, setRenderedConversation] = useState(conversationId)
  if (renderedConversation !== conversationId) {
    setRenderedConversation(conversationId)
    setMessages([])
    setLinks([])
    setTreeNodes([])
    setError(null)
    setHistory([])
    setHasMore(true)
    setLoadingMore(false)
    setIsHistoryLoading(false)
    setGeneratingUserMessageIds(new Set())
    const target = Number(new URLSearchParams(window.location.search).get("m"))
    setActiveMessageId(Number.isSafeInteger(target) && target > 0 ? target : null)
  }

  const addToHistory = useCallback((msg: ChatMessage) => {
    setHistory((prev) => {
      const filtered = prev.filter((item) => item.id !== msg.id)
      const snippet = msg.content
        ? msg.content.replace(/<[^>]*>/g, "").substring(0, 30).trim() + (msg.content.length > 30 ? "..." : "")
        : ""
      const newEntry = {
        id: msg.id,
        speaker: msg.speaker,
        snippet: snippet || `[${msg.speaker}]`,
      }
      return [newEntry, ...filtered].slice(0, 5)
    })
  }, [])

  const selectMessage = useCallback((msgId: number | null) => {
    if (activeMessageId !== null && msgId !== null && activeMessageId !== msgId) {
      const current = messages.find(message => message.id === activeMessageId)
      if (current) addToHistory(current)
    }
    setActiveMessageId(msgId)
  }, [messages, activeMessageId, addToHistory])
  const handleFilesIndexed = useCallback(() => {
    const owner = lifecycle.current
    getHistory(PAGE_SIZE, 0, conversationId).then(data => {
      if (owner !== lifecycle.current || loadedRef.current !== conversationId) return
      setMessages(data.messages)
      setHasMore(false)
      fetchTree(conversationId)
    }).catch(error => {
      if (owner === lifecycle.current) setError(error instanceof Error ? error.message : "Unable to refresh indexed files")
    })
  }, [conversationId, fetchTree])
  const fileState = useConversationFiles(conversationId, handleFilesIndexed)
  const { files, upload, deleteFile, reprocess, isIndexing, refreshFiles } = fileState

  useEffect(() => {
    const owner = ++lifecycle.current
    loadedRef.current = conversationId

    getAgent()
      .then((info) => setAgentName(info.name))
      .catch(() => setAgentName("agent"))

    if (conversationId) {
      setIsHistoryLoading(true)
      
      const params = new URLSearchParams(window.location.search)
      const urlMsgId = params.get("m")
      const targetMsgId = urlMsgId ? parseInt(urlMsgId, 10) : null

      if (targetMsgId && !isNaN(targetMsgId)) {
        getMessagePath(targetMsgId)
          .then((pathMessages) => {
            if (owner !== lifecycle.current || loadedRef.current !== conversationId) return
            setMessages(pathMessages)
            setActiveMessageId(targetMsgId)
            setHasMore(false)
          })
          .catch((err) => {
            if (owner !== lifecycle.current || loadedRef.current !== conversationId) return
            console.error("Failed to load message path from URL param 'm':", err)
            addNotification({
              type: "glitch",
              snippet: `Failed to load message path from URL: ${err.message || "Unknown resistance"}`,
              source: "Chat.loadPath"
            })
            getHistory(PAGE_SIZE, 0, conversationId)
              .then((data) => {
                if (owner !== lifecycle.current || loadedRef.current !== conversationId) return
                setMessages(data.messages)
                if (data.messages.length > 0) {
                  const newest = data.messages[data.messages.length - 1]
                  setActiveMessageId(newest.id)
                } else {
                  setActiveMessageId(null)
                }
                setHasMore(false)
              })
              .catch((errHistory) => {
                if (owner !== lifecycle.current || loadedRef.current !== conversationId) return
                setMessages([])
                setActiveMessageId(null)
                setHasMore(false)
                addNotification({
                  type: "glitch",
                  snippet: `Failed to load conversation history fallback: ${errHistory.message || "Unknown resistance"}`,
                  source: "Chat.loadHistory"
                })
              })
          })
          .finally(() => {
            if (owner === lifecycle.current && loadedRef.current === conversationId) setIsHistoryLoading(false)
          })
      } else {
        getHistory(PAGE_SIZE, 0, conversationId)
          .then((data) => {
            if (owner !== lifecycle.current || loadedRef.current !== conversationId) return
            setMessages(data.messages)
            if (data.messages.length > 0) {
              const newest = data.messages[data.messages.length - 1]
              setActiveMessageId(newest.id)
            } else {
              setActiveMessageId(null)
            }
            setHasMore(false)
          })
          .catch((err) => {
            if (owner !== lifecycle.current || loadedRef.current !== conversationId) return
            setMessages([])
            setActiveMessageId(null)
            setHasMore(false)
            addNotification({
              type: "glitch",
              snippet: `Failed to load conversation history: ${err.message || "Unknown resistance"}`,
              source: "Chat.loadHistory"
            })
          })
          .finally(() => {
            if (owner === lifecycle.current && loadedRef.current === conversationId) setIsHistoryLoading(false)
          })
      }

      fetchTree(conversationId)

    } else {
      setMessages([])
      setHasMore(false)
    }
    return () => { loadedRef.current = ""; lifecycle.current = owner + 1 }
  }, [conversationId, fetchTree])

  // Sync activeMessageId to URL search params in place without pushing a new history entry
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (activeMessageId !== null) {
      params.set("m", String(activeMessageId))
    } else {
      params.delete("m")
    }
    const newUrl = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`
    window.history.replaceState(null, "", newUrl)
  }, [activeMessageId])

  // Watch popstate to synchronize active message ID with the URL if it updates via browser back/forward
  useEffect(() => {
    const owner = lifecycle.current
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search)
      const urlMsgId = params.get("m")
      const targetMsgId = urlMsgId ? parseInt(urlMsgId, 10) : null
      if (targetMsgId && !isNaN(targetMsgId)) {
        if (activeMessageId !== targetMsgId) {
          const isLoaded = messages.some((m) => m.id === targetMsgId)
          if (isLoaded) {
            setActiveMessageId(targetMsgId)
          } else {
            getMessagePath(targetMsgId)
              .then((pathMessages) => {
                if (owner !== lifecycle.current) return
                setMessages(pathMessages)
                setActiveMessageId(targetMsgId)
              })
              .catch(() => {})
          }
        }
      }
    }
    window.addEventListener("popstate", handlePopState)
    return () => window.removeEventListener("popstate", handlePopState)
  }, [messages, activeMessageId, conversationId])

  const loadMoreMessages = useCallback(async () => {
    const owner = lifecycle.current
    if (!conversationId || loadingMore || !hasMore) return
    setLoadingMore(true)
    try {
      const data = await getHistory(PAGE_SIZE, messages.length, conversationId)
      if (owner !== lifecycle.current || loadedRef.current !== conversationId) return
      if (data.messages.length < PAGE_SIZE) {
        setHasMore(false)
      } else {
        setHasMore(true)
      }
      setMessages((prev) => {
        const existingIds = new Set(prev.map((m) => m.id))
        const filteredNew = data.messages.filter((m) => !existingIds.has(m.id))
        return [...filteredNew, ...prev]
      })
    } catch (e: any) {
      console.error("Failed to load more messages:", e)
      addNotification({
        type: "glitch",
        snippet: `Failed to load more messages: ${e.message || "Unknown resistance"}`,
        source: "Chat.loadMore"
      })
    } finally {
      if (owner === lifecycle.current) setLoadingMore(false)
    }
  }, [conversationId, messages.length, loadingMore, hasMore])

  const send = useCallback(async (content: string) => {
    const owner = lifecycle.current
    setError(null)

    const parentId = activeMessageId

    // 1. Create a local temporary message for immediate UI feedback
    const tempId = Date.now()
    setGeneratingUserMessageIds((prev) => new Set([...prev, tempId]))
    const userMsg: ChatMessage = {
      id: tempId,
      timestamp: new Date().toISOString(),
      speaker: "human",
      content,
      content_tokens: estimateTokens(content),
      parent_message_id: parentId || undefined,
    }
    setMessages((prev) => [...prev, userMsg])
    setActiveMessageId(tempId)

    let savedMsg: ChatMessage | null = null
    let targetConvId: string | undefined = conversationId

    try {
      // 2. Phase 1: Inscribe/persist the message to the DB
      savedMsg = await saveMessage(content, targetConvId || undefined, parentId)

      // Guard check before changing state of this conversation
      if (owner !== lifecycle.current || (targetConvId && loadedRef.current !== targetConvId)) {
        // User switched conversations, don't update local hook state.
        targetConvId = savedMsg.conversation_id
      } else {
        // Update the message in the list with its real DB ID
        setMessages((prev) =>
          prev.map((m) => (m.id === tempId ? {
            ...m,
            id: savedMsg!.id,
            parent_message_id: savedMsg!.parent_message_id,
            structural_signature: savedMsg!.structural_signature,
            structural_justification: savedMsg!.structural_justification,
          } : m))
        )
        setActiveMessageId(savedMsg.id)
        setGeneratingUserMessageIds((prev) => {
          const next = new Set(prev)
          next.delete(tempId)
          next.add(savedMsg!.id)
          return next
        })

        targetConvId = targetConvId || savedMsg.conversation_id
        if (targetConvId) {
          const finalConvId = targetConvId
          // Fetch/refresh trees and files
          fetchTree(finalConvId)

          refreshFiles(finalConvId)
        }
      }
    } catch (e: any) {
      const msg = e instanceof Error ? e.message : "Failed to persist user message"
      if (owner === lifecycle.current && (!targetConvId || loadedRef.current === targetConvId)) {
        setError(msg)
      }
      if (owner === lifecycle.current) setGeneratingUserMessageIds((prev) => {
        const next = new Set(prev)
        next.delete(tempId)
        return next
      })
      addNotification({
        type: "glitch",
        snippet: `Failed to save message: ${msg}`,
        source: "Chat.saveMessage"
      })
      return null
    }

    // 3. Phase 2: Metabolize/generate response asynchronously/retryably
    try {
      const response = await generateResponse(targetConvId!, savedMsg.id)

      if (owner !== lifecycle.current || loadedRef.current !== targetConvId) {
        // User has switched to another conversation. Show notification.
        addNotification({
          conversationId: targetConvId!,
          messageId: response.id,
          parentMessageId: savedMsg.id,
          timestamp: response.timestamp || new Date().toISOString(),
          snippet: response.content || "",
          speaker: "apparatus"
        })
        return response
      }

      // User is still in the same conversation.
      // Check if user has navigated to another node in the meantime.
      const isViewingSameNode = (activeMessageIdRef.current === savedMsg.id || activeMessageIdRef.current === tempId)

      setMessages((prev) => {
        if (prev.some((m) => m.id === response.id)) return prev
        return [...prev, response]
      })

      if (isViewingSameNode) {
        setActiveMessageId(response.id)
      } else {
        // User is viewing a different node, so do not hijack focus. Show notification instead.
        addNotification({
          conversationId: targetConvId!,
          messageId: response.id,
          parentMessageId: savedMsg.id,
          timestamp: response.timestamp || new Date().toISOString(),
          snippet: response.content || "",
          speaker: "apparatus"
        })
      }

      fetchTree(targetConvId!)

      return response
    } catch (e: any) {
      const msg = e instanceof Error ? e.message : "Failed to generate response"
      if (owner === lifecycle.current && loadedRef.current === targetConvId) {
        setError(msg)
      }
      addNotification({
        type: "glitch",
        snippet: `Failed to generate response: ${msg}`,
        source: "Chat.generateResponse"
      })
      return savedMsg // Return the user message so App.tsx knows the conversation was created/updated
    } finally {
      if (owner === lifecycle.current) setGeneratingUserMessageIds((prev) => {
        const next = new Set(prev)
        next.delete(tempId)
        if (savedMsg) {
          next.delete(savedMsg.id)
        }
        return next
      })
    }
  }, [conversationId, activeMessageId, refreshFiles, fetchTree])

  const regenerate = useCallback(async (userMsgId?: number) => {
    const owner = lifecycle.current
    if (loading) return
    setError(null)
    const targetConvId = conversationId

    let targetMsgId = userMsgId
    if (!targetMsgId) {
      const lastUserMsg = [...messages].reverse().find((m) => m.speaker === "human")
      if (!lastUserMsg || !lastUserMsg.id) {
        setError("No user message found to regenerate response for")
        return
      }
      targetMsgId = lastUserMsg.id
    }

    setGeneratingUserMessageIds((prev) => new Set([...prev, targetMsgId!]))

    try {
      if (!targetConvId) {
        throw new Error("No active conversation")
      }

      const response = await generateResponse(targetConvId, targetMsgId)

      if (owner !== lifecycle.current || loadedRef.current !== targetConvId) {
        addNotification({
          conversationId: targetConvId,
          messageId: response.id,
          parentMessageId: targetMsgId,
          timestamp: response.timestamp || new Date().toISOString(),
          snippet: response.content || "",
          speaker: "apparatus"
        })
        return response
      }

      const isViewingSameNode = (activeMessageIdRef.current === targetMsgId)

      setMessages((prev) => {
        if (prev.some((m) => m.id === response.id)) return prev
        return [...prev, response]
      })

      if (isViewingSameNode) {
        setActiveMessageId(response.id)
      } else {
        addNotification({
          conversationId: targetConvId,
          messageId: response.id,
          parentMessageId: targetMsgId,
          timestamp: response.timestamp || new Date().toISOString(),
          snippet: response.content || "",
          speaker: "apparatus"
        })
      }

      fetchTree(targetConvId)

      return response
    } catch (e: any) {
      const msg = e instanceof Error ? e.message : "Failed to generate response"
      if (owner === lifecycle.current && loadedRef.current === targetConvId) {
        setError(msg)
      }
      addNotification({
        type: "glitch",
        snippet: `Failed to regenerate response: ${msg}`,
        source: "Chat.regenerateResponse"
      })
      return null
    } finally {
      if (owner === lifecycle.current) setGeneratingUserMessageIds((prev) => {
        const next = new Set(prev)
        if (targetMsgId) {
          next.delete(targetMsgId)
        }
        return next
      })
    }
  }, [loading, conversationId, messages, fetchTree])


  const clearError = useCallback(() => setError(null), [])

  const refreshMessages = useCallback(() => {
    const owner = lifecycle.current
    if (conversationId) {
      getHistory(PAGE_SIZE, 0, conversationId)
        .then((data) => {
          if (owner === lifecycle.current && loadedRef.current === conversationId) setMessages(data.messages)
        })
        .catch(() => {})

      fetchTree(conversationId)
    }
  }, [conversationId, fetchTree])

  const refreshTree = useCallback(() => {
    if (conversationId) {
      fetchTree(conversationId)
    }
  }, [conversationId, fetchTree])

  const activePathIds = useMemo(() => getAncestorPathIds(messages, activeMessageId), [messages, activeMessageId])
  const activePathMessages = useMemo(() => messages.filter((m) => activePathIds.has(m.id)), [messages, activePathIds])

  const commitProposedBranch = useCallback(async (parentMsgId: number, content: string) => {
    const owner = lifecycle.current
    if (!conversationId) return null
    setGeneratingUserMessageIds((prev) => new Set([...prev, parentMsgId]))
    setError(null)
    const targetConvId = conversationId
    try {
      const response = await commitBranch(targetConvId, parentMsgId, content)
      
      if (owner !== lifecycle.current || loadedRef.current !== targetConvId) {
        addNotification({
          conversationId: targetConvId,
          messageId: response.id,
          parentMessageId: parentMsgId,
          timestamp: response.timestamp || new Date().toISOString(),
          snippet: response.content || "",
          speaker: "apparatus"
        })
        return response
      }

      fetchTree(targetConvId)
      setMessages((prev) => {
        if (prev.some((m) => m.id === response.id)) return prev
        return [...prev, response]
      })
      setActiveMessageId(response.id)
      return response
    } catch (e: any) {
      const msg = e instanceof Error ? e.message : "Failed to commit branch"
      if (owner === lifecycle.current && loadedRef.current === targetConvId) {
        setError(msg)
      }
      addNotification({
        type: "glitch",
        snippet: `Failed to commit branch: ${msg}`,
        source: "Chat.commitBranch"
      })
      return null
    } finally {
      if (owner === lifecycle.current) setGeneratingUserMessageIds((prev) => {
        const next = new Set(prev)
        next.delete(parentMsgId)
        return next
      })
    }
  }, [conversationId, fetchTree])

  const navigateToMessage = useCallback(async (msgId: number) => {
    const owner = lifecycle.current
    if (activeMessageId !== null && activeMessageId !== msgId) {
      const currentMsg = messages.find((m) => m.id === activeMessageId)
      if (currentMsg) {
        addToHistory(currentMsg)
      }
    }

    const isLoaded = messages.some((m) => m.id === msgId)
    if (isLoaded) {
      setActiveMessageId(msgId)
      return
    }

    setIsHistoryLoading(true)
    setError(null)
    try {
      const pathMessages = await getMessagePath(msgId)
      if (owner !== lifecycle.current || loadedRef.current !== conversationId) return
      setMessages(pathMessages)
      setActiveMessageId(msgId)
    } catch (e: any) {
      if (owner !== lifecycle.current) return
      console.error("Failed to navigate to message path:", e)
      setError("Failed to navigate to the selected message path.")
      addNotification({
        type: "glitch",
        snippet: `Failed to navigate to message path: ${e.message || "Unknown resistance"}`,
        source: "Chat.navigateToMessage"
      })
    } finally {
      if (owner === lifecycle.current) setIsHistoryLoading(false)
    }
  }, [messages, activeMessageId, addToHistory, conversationId])

  const selectedNode = useMemo(() => {
    return messages.find((m) => m.id === activeMessageId) || null
  }, [messages, activeMessageId])

  const parentNode = useMemo(() => {
    if (!selectedNode || !selectedNode.parent_message_id) return null
    return messages.find((m) => m.id === selectedNode.parent_message_id) || null
  }, [messages, selectedNode])

  const siblingNodes = useMemo(() => {
    if (!selectedNode) return []
    const parentId = selectedNode.parent_message_id
    return treeNodes.filter(
      (n) => n.parent_message_id === parentId && n.id !== selectedNode.id && n.speaker === selectedNode.speaker
    )
  }, [treeNodes, selectedNode])

  const childNodes = useMemo(() => {
    if (!activeMessageId) return []
    return treeNodes.filter((n) => n.parent_message_id === activeMessageId)
  }, [treeNodes, activeMessageId])

  return {
    messages: activePathMessages,
    fullTreeMessages: messages,
    links,
    activeMessageId,
    setActiveMessageId: selectMessage,
    activePathIds,
    commitProposedBranch,
    navigateToMessage,
    loading,
    error: error || fileState.error,
    send,
    regenerate,
    clearError: () => { clearError(); fileState.clearError() },
    agentName,
    uploadedFiles: files,
    isIndexing,
    upload,
    deleteFile,
    reprocess,
    hasMore,
    loadingMore,
    loadMoreMessages,
    refreshMessages,
    refreshTree,
    selectedNode,
    parentNode,
    siblingNodes,
    childNodes,
    treeNodes,
    history,
  }
}

