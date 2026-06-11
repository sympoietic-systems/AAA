import { useCallback, useEffect, useRef, useState, useMemo } from "react"
import {
  getAgent,
  getHistory,
  saveMessage,
  generateResponse,
  getConversationFiles,
  uploadFiles,
  deleteConversationFile,
  reprocessFile,
  commitBranch,
  getConversationTree,
  getMessagePath,
} from "../api/client"
import type { ChatMessage, ConversationFile, ConversationTreeNode, ConversationTreeLink } from "../api/client"
import { addNotification, dismissByMatch } from "../stores/notificationStore"

function estimateTokens(text: string): number {
  if (!text) return 0
  return Math.max(1, Math.floor(text.length / 4))
}

function getAncestorPathIds(messages: ChatMessage[], leafId: number | null): Set<number> {
  const path = new Set<number>()
  if (!leafId) return path

  const sorted = [...messages].sort((a, b) => a.id - b.id)

  let currentId: number | null = leafId
  const parentMap = new Map<number, number | null>()
  for (let i = 0; i < sorted.length; i++) {
    const m = sorted[i]
    if (m.parent_message_id !== undefined && m.parent_message_id !== null) {
      parentMap.set(m.id, m.parent_message_id)
    } else if (i > 0) {
      parentMap.set(m.id, sorted[i - 1].id)
    } else {
      parentMap.set(m.id, null)
    }
  }

  const visited = new Set<number>()
  while (currentId !== null && !visited.has(currentId)) {
    visited.add(currentId)
    path.add(currentId)
    currentId = parentMap.get(currentId) || null
  }

  return path
}


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
  const [files, setFiles] = useState<ConversationFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)

  // Synchronously reset conversation-specific states when the active thread changes
  const lastConversationIdRef = useRef(conversationId)
  if (lastConversationIdRef.current !== conversationId) {
    lastConversationIdRef.current = conversationId
    setMessages([])
    setLinks([])
    setTreeNodes([])
    setHasMore(true)
    const params = new URLSearchParams(window.location.search)
    const urlMsgId = params.get("m")
    const targetMsgId = urlMsgId ? parseInt(urlMsgId, 10) : null
    const nextId = targetMsgId && !isNaN(targetMsgId) ? targetMsgId : null
    setActiveMessageId(nextId)
  }

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

  const fetchTree = useCallback(async (convId: string) => {
    if (!convId) return
    try {
      const data = await getConversationTree(convId)
      setLinks(data.links)
      setTreeNodes(data.nodes)
    } catch {
      setLinks([])
      setTreeNodes([])
    }
  }, [])
  const [error, setError] = useState<string | null>(null)
  const [agentName, setAgentName] = useState("...")
  const [history, setHistory] = useState<{ id: number; speaker: string; snippet: string }[]>([])

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
    setActiveMessageId((prevId) => {
      if (prevId !== null && msgId !== null && prevId !== msgId) {
        const currentMsg = messages.find((m) => m.id === prevId)
        if (currentMsg) {
          addToHistory(currentMsg)
        }
      }
      return msgId
    })
  }, [messages, addToHistory])
  const loadedRef = useRef<string>("")
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startPolling = useCallback((convId: string) => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    pollTimerRef.current = setInterval(async () => {
      try {
        const res = await getConversationFiles(convId)
        setFiles(res.files)
        const active = res.files.some(
          (f) => f.status === "uploading" || f.status === "processing"
        )
        if (!active) {
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current)
            pollTimerRef.current = null
          }
          // Fetch updated conversation history to display system message after file indexing completes
          getHistory(PAGE_SIZE, 0, convId)
            .then((data) => {
              setMessages(data.messages)
              if (data.messages.length > 0) {
                setActiveMessageId((prev) => {
                  if (prev !== null && data.messages.some((m) => m.id === prev)) {
                    return prev
                  }
                  return data.messages[data.messages.length - 1].id
                })
              }
              setHasMore(false)
            })
            .catch(() => { })
        }
      } catch {
        // silent
      }
    }, 2000)
  }, [])

  useEffect(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }

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
            setMessages(pathMessages)
            setActiveMessageId(targetMsgId)
            setHasMore(false)
          })
          .catch((err) => {
            console.error("Failed to load message path from URL param 'm':", err)
            getHistory(PAGE_SIZE, 0, conversationId)
              .then((data) => {
                setMessages(data.messages)
                if (data.messages.length > 0) {
                  const newest = data.messages[data.messages.length - 1]
                  setActiveMessageId(newest.id)
                } else {
                  setActiveMessageId(null)
                }
                setHasMore(false)
              })
              .catch(() => {
                setMessages([])
                setActiveMessageId(null)
                setHasMore(false)
              })
          })
          .finally(() => setIsHistoryLoading(false))
      } else {
        getHistory(PAGE_SIZE, 0, conversationId)
          .then((data) => {
            setMessages(data.messages)
            if (data.messages.length > 0) {
              const newest = data.messages[data.messages.length - 1]
              setActiveMessageId(newest.id)
            } else {
              setActiveMessageId(null)
            }
            setHasMore(false)
          })
          .catch(() => {
            setMessages([])
            setActiveMessageId(null)
            setHasMore(false)
          })
          .finally(() => setIsHistoryLoading(false))
      }

      fetchTree(conversationId)

      getConversationFiles(conversationId)
        .then((data) => {
          setFiles(data.files)
          const active = data.files.some(
            (f) => f.status === "uploading" || f.status === "processing"
          )
          if (active) {
            startPolling(conversationId)
          }
        })
        .catch(() => setFiles([]))
    } else {
      setMessages([])
      setFiles([])
      setHasMore(false)
    }
  }, [conversationId, startPolling, fetchTree])

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    }
  }, [])

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
  }, [messages, activeMessageId])

  const loadMoreMessages = useCallback(async () => {
    if (!conversationId || loadingMore || !hasMore) return
    setLoadingMore(true)
    try {
      const data = await getHistory(PAGE_SIZE, messages.length, conversationId)
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
    } catch (e) {
      console.error("Failed to load more messages:", e)
    } finally {
      setLoadingMore(false)
    }
  }, [conversationId, messages.length, loadingMore, hasMore])

  const send = useCallback(async (content: string) => {
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
      if (targetConvId && loadedRef.current !== targetConvId) {
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

          getConversationFiles(finalConvId)
            .then((res) => {
              setFiles(res.files)
              const active = res.files.some(
                (f) => f.status === "uploading" || f.status === "processing"
              )
              if (active) {
                startPolling(finalConvId)
              }
            })
            .catch(() => {})
        }
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to persist user message"
      if (!targetConvId || loadedRef.current === targetConvId) {
        setError(msg)
      }
      setGeneratingUserMessageIds((prev) => {
        const next = new Set(prev)
        next.delete(tempId)
        return next
      })
      return null
    }

    // 3. Phase 2: Metabolize/generate response asynchronously/retryably
    try {
      const response = await generateResponse(targetConvId!, savedMsg.id)

      if (loadedRef.current !== targetConvId) {
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
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to generate response"
      if (loadedRef.current === targetConvId) {
        setError(msg)
      }
      return savedMsg // Return the user message so App.tsx knows the conversation was created/updated
    } finally {
      setGeneratingUserMessageIds((prev) => {
        const next = new Set(prev)
        next.delete(tempId)
        if (savedMsg) {
          next.delete(savedMsg.id)
        }
        return next
      })
    }
  }, [loading, conversationId, activeMessageId, startPolling, fetchTree])

  const regenerate = useCallback(async (userMsgId?: number) => {
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

      if (loadedRef.current !== targetConvId) {
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
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to generate response"
      if (loadedRef.current === targetConvId) {
        setError(msg)
      }
      return null
    } finally {
      setGeneratingUserMessageIds((prev) => {
        const next = new Set(prev)
        if (targetMsgId) {
          next.delete(targetMsgId)
        }
        return next
      })
    }
  }, [loading, conversationId, messages, fetchTree])


  const upload = useCallback(async (filesToUpload: File[]) => {
    if (filesToUpload.length === 0) return null
    setIsUploading(true)
    setError(null)
    try {
      const targetId = conversationId || "new"
      const res = await uploadFiles(targetId, filesToUpload)
      setFiles(res.files)
      startPolling(res.conversation_id)
      return res.conversation_id
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to upload files"
      setError(msg)
      return null
    } finally {
      setIsUploading(false)
    }
  }, [conversationId, startPolling])

  const deleteFile = useCallback(async (fileName: string) => {
    if (!conversationId) return
    try {
      await deleteConversationFile(conversationId, fileName)
      setFiles((prev) => prev.filter((f) => f.file_name !== fileName))
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to delete file"
      setError(msg)
    }
  }, [conversationId])

  const reprocess = useCallback(async (fileName: string) => {
    if (!conversationId) return
    try {
      await reprocessFile(conversationId, fileName)
      setFiles((prev) =>
        prev.map((f) =>
          f.file_name === fileName ? { ...f, status: "processing" as const } : f
        )
      )
      startPolling(conversationId)
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to reprocess file"
      setError(msg)
    }
  }, [conversationId, startPolling])

  const clearError = useCallback(() => setError(null), [])

  const refreshMessages = useCallback(() => {
    if (conversationId) {
      getHistory(1000, 0, conversationId)
        .then((data) => {
          setMessages(data.messages)
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

  const isIndexing = isUploading || files.some(
    (f) => f.status === "uploading" || f.status === "processing"
  )

  const activePathIds = useMemo(() => getAncestorPathIds(messages, activeMessageId), [messages, activeMessageId])
  const activePathMessages = useMemo(() => messages.filter((m) => activePathIds.has(m.id)), [messages, activePathIds])

  const commitProposedBranch = useCallback(async (parentMsgId: number, content: string) => {
    if (!conversationId) return null
    setGeneratingUserMessageIds((prev) => new Set([...prev, parentMsgId]))
    setError(null)
    const targetConvId = conversationId
    try {
      const response = await commitBranch(targetConvId, parentMsgId, content)
      
      if (loadedRef.current !== targetConvId) {
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
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to commit branch"
      if (loadedRef.current === targetConvId) {
        setError(msg)
      }
      return null
    } finally {
      setGeneratingUserMessageIds((prev) => {
        const next = new Set(prev)
        next.delete(parentMsgId)
        return next
      })
    }
  }, [conversationId, fetchTree])

  const navigateToMessage = useCallback(async (msgId: number) => {
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
      setMessages(pathMessages)
      setActiveMessageId(msgId)
    } catch (e) {
      console.error("Failed to navigate to message path:", e)
      setError("Failed to navigate to the selected message path.")
    } finally {
      setIsHistoryLoading(false)
    }
  }, [messages, activeMessageId, addToHistory])

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
    error,
    send,
    regenerate,
    clearError,
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

