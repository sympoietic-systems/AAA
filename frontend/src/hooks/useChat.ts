import { useCallback, useEffect, useRef, useState } from "react"
import {
  getAgent,
  getHistory,
  sendMessage,
  getConversationFiles,
  uploadFiles,
  deleteConversationFile,
  reprocessFile,
  commitBranch,
} from "../api/client"
import type { ChatMessage, ConversationFile } from "../api/client"

function estimateTokens(text: string): number {
  if (!text) return 0
  return Math.max(1, Math.floor(text.length / 4))
}

function getAncestorPathIds(messages: ChatMessage[], leafId: number | null): Set<number> {
  const path = new Set<number>()
  if (!leafId) return path

  let currentId: number | null = leafId
  const parentMap = new Map<number, number | null>()
  for (const m of messages) {
    parentMap.set(m.id, m.parent_message_id || null)
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
  const PAGE_SIZE = 1000
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [activeMessageId, setActiveMessageId] = useState<number | null>(null)
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
          getHistory(1000, 0, convId)
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
      getHistory(1000, 0, conversationId)
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

    const userMsg: ChatMessage = {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      speaker: "human",
      content,
      content_tokens: estimateTokens(content),
      parent_message_id: parentId || undefined,
    }
    setMessages((prev) => [...prev, userMsg])

    try {
      const response = await sendMessage(content, conversationId || undefined, undefined, parentId)
      setMessages((prev) => {
        const updated = [...prev]
        for (let i = updated.length - 1; i >= 0; i--) {
          if (updated[i].speaker === "human" && updated[i].id === userMsg.id) {
            updated[i] = {
              ...updated[i],
              id: response.user_message_id || updated[i].id,
              metrics: response.metrics || updated[i].metrics,
              structural_signature: response.user_structural_signature || undefined,
              structural_justification: response.user_structural_justification || undefined,
            }
            break
          }
        }
        updated.push(response)
        return updated
      })

      setActiveMessageId(response.id)
      const targetConvId = conversationId || response.conversation_id
      if (targetConvId) {
        getConversationFiles(targetConvId)
          .then((res) => {
            setFiles(res.files)
            const active = res.files.some(
              (f) => f.status === "uploading" || f.status === "processing"
            )
            if (active) {
              startPolling(targetConvId)
            }
          })
          .catch(() => {})
      }

      return response
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to send message"
      setError(msg)
      return null
    } finally {
      setLoading(false)
    }
  }, [loading, conversationId, activeMessageId, startPolling])

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
    }
  }, [conversationId])

  const isIndexing = isUploading || files.some(
    (f) => f.status === "uploading" || f.status === "processing"
  )

  const activePathIds = getAncestorPathIds(messages, activeMessageId)
  const activePathMessages = messages.filter((m) => activePathIds.has(m.id))

  const commitProposedBranch = useCallback(async (parentMsgId: number, content: string) => {
    if (!conversationId) return null
    setLoading(true)
    setError(null)
    try {
      const response = await commitBranch(conversationId, parentMsgId, content)
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
    activeMessageId,
    setActiveMessageId,
    activePathIds,
    commitProposedBranch,
    loading,
    error,
    send,
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
  }
}

