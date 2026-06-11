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
} from "../api/client"
import type { ChatMessage, ConversationFile } from "../api/client"

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
  const [activeMessageId, setActiveMessageId] = useState<number | null>(null)
  const [links, setLinks] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [agentName, setAgentName] = useState("...")
  const [files, setFiles] = useState<ConversationFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
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
      setLoading(true)
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
        .finally(() => setLoading(false))

      getConversationTree(conversationId)
        .then((data) => setLinks(data.links))
        .catch(() => setLinks([]))

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
  }, [conversationId, startPolling])

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    }
  }, [])

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
    if (!content.trim() || loading) return
    setError(null)
    setLoading(true)

    const parentId = activeMessageId

    // 1. Create a local temporary message for immediate UI feedback
    const tempId = Date.now()
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

      targetConvId = targetConvId || savedMsg.conversation_id
      if (targetConvId) {
        const finalConvId = targetConvId
        // Fetch/refresh trees and files
        getConversationTree(finalConvId)
          .then((data) => setLinks(data.links))
          .catch(() => {})

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
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to persist user message"
      setError(msg)
      setLoading(false)
      return null
    }

    // 3. Phase 2: Metabolize/generate response asynchronously/retryably
    try {
      const response = await generateResponse(targetConvId!, savedMsg.id)
      setMessages((prev) => {
        if (prev.some((m) => m.id === response.id)) return prev
        return [...prev, response]
      })
      setActiveMessageId(response.id)
      return response
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to generate response"
      setError(msg)
      return savedMsg // Return the user message so App.tsx knows the conversation was created/updated
    } finally {
      setLoading(false)
    }
  }, [loading, conversationId, activeMessageId, startPolling])

  const regenerate = useCallback(async (userMsgId?: number) => {
    if (loading) return
    setError(null)
    setLoading(true)

    let targetMsgId = userMsgId
    if (!targetMsgId) {
      const lastUserMsg = [...messages].reverse().find((m) => m.speaker === "human")
      if (!lastUserMsg || !lastUserMsg.id) {
        setError("No user message found to regenerate response for")
        setLoading(false)
        return
      }
      targetMsgId = lastUserMsg.id
    }

    try {
      const targetConvId = conversationId
      if (!targetConvId) {
        throw new Error("No active conversation")
      }

      const response = await generateResponse(targetConvId, targetMsgId)
      setMessages((prev) => {
        if (prev.some((m) => m.id === response.id)) return prev
        return [...prev, response]
      })
      setActiveMessageId(response.id)

      getConversationTree(targetConvId)
        .then((data) => setLinks(data.links))
        .catch(() => {})

      return response
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to generate response"
      setError(msg)
      return null
    } finally {
      setLoading(false)
    }
  }, [loading, conversationId, messages])


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

      getConversationTree(conversationId)
        .then((data) => setLinks(data.links))
        .catch(() => setLinks([]))
    }
  }, [conversationId])

  const refreshTree = useCallback(() => {
    if (conversationId) {
      getConversationTree(conversationId)
        .then((data) => setLinks(data.links))
        .catch(() => {})
    }
  }, [conversationId])

  const isIndexing = isUploading || files.some(
    (f) => f.status === "uploading" || f.status === "processing"
  )

  const activePathIds = useMemo(() => getAncestorPathIds(messages, activeMessageId), [messages, activeMessageId])
  const activePathMessages = useMemo(() => messages.filter((m) => activePathIds.has(m.id)), [messages, activePathIds])

  const commitProposedBranch = useCallback(async (parentMsgId: number, content: string) => {
    if (!conversationId) return null
    setLoading(true)
    setError(null)
    try {
      const response = await commitBranch(conversationId, parentMsgId, content)
      getConversationTree(conversationId)
        .then((data) => setLinks(data.links))
        .catch(() => {})
      setMessages((prev) => {
        if (prev.some((m) => m.id === response.id)) return prev
        return [...prev, response]
      })
      setActiveMessageId(response.id)
      return response
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to commit branch"
      setError(msg)
      return null
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  return {
    messages: activePathMessages,
    fullTreeMessages: messages,
    links,
    activeMessageId,
    setActiveMessageId,
    activePathIds,
    commitProposedBranch,
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
  }
}

