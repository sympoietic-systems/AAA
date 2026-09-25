import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react"
import { getConversationFiles, uploadFiles, deleteConversationFile, reprocessFile } from "../api/conversations"
import type { ConversationFile } from "../api/types"
import { addNotification } from "../stores/notificationStore"

/** File operations and single-flight indexing polling, scoped to a conversation lifetime. */
export function useConversationFiles(conversationId: string, onIndexed: () => void) {
  const [state, setState] = useState<{ id: string; files: ConversationFile[] }>({ id: conversationId, files: [] })
  const [isUploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [revision, setRevision] = useState(0)
  const [ownerId, setOwnerId] = useState(conversationId)
  if (ownerId !== conversationId) {
    setOwnerId(conversationId)
    setState({ id: conversationId, files: [] })
    setUploading(false)
    setError(null)
  }
  const lifetime = useRef(0)
  const indexed = useEffectEvent(onIndexed)
  useEffect(() => {
    const owner = ++lifetime.current
    return () => { lifetime.current = owner + 1 }
  }, [conversationId])
  useEffect(() => {
    const owner = lifetime.current
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | undefined
    let processing = revision > 0
    const poll = async () => {
      try {
        const result = await getConversationFiles(conversationId, controller.signal)
        if (controller.signal.aborted || owner !== lifetime.current) return
        setState({ id: conversationId, files: result.files })
        setError(null)
        const active = result.files.some(file => file.status === "uploading" || file.status === "processing")
        if (!active && processing) indexed()
        processing = active
        if (active) timer = setTimeout(poll, 2000)
      } catch (error) {
        if (controller.signal.aborted || owner !== lifetime.current) return
        setError(error instanceof Error ? error.message : "Unable to load files")
        timer = setTimeout(poll, 5000)
      }
    }
    if (conversationId) void poll()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [conversationId, revision])
  const refreshFiles = useCallback((id = conversationId) => {
    if (id === conversationId) setRevision(value => value + 1)
  }, [conversationId])
  const report = (reason: unknown) => {
    const message = reason instanceof Error ? reason.message : "File operation failed"
    setError(message)
    addNotification({ type: "glitch", snippet: message, source: "Chat.files" })
  }
  const upload = async (files: File[]) => {
    if (!files.length) return null
    const owner = lifetime.current
    setUploading(true)
    setError(null)
    try {
      const result = await uploadFiles(conversationId || "new", files)
      if (owner === lifetime.current) {
        setState({ id: conversationId, files: result.files })
        refreshFiles(result.conversation_id)
      }
      return result.conversation_id
    } catch (error) {
      if (owner === lifetime.current) report(error)
      return null
    } finally {
      if (owner === lifetime.current) setUploading(false)
    }
  }
  const deleteFile = async (name: string) => {
    if (!conversationId) return
    const owner = lifetime.current
    try {
      await deleteConversationFile(conversationId, name)
      if (owner === lifetime.current) refreshFiles()
    } catch (error) { if (owner === lifetime.current) report(error) }
  }
  const reprocess = async (name: string) => {
    if (!conversationId) return
    const owner = lifetime.current
    try {
      await reprocessFile(conversationId, name)
      if (owner === lifetime.current) refreshFiles()
    } catch (error) { if (owner === lifetime.current) report(error) }
  }
  const files = state.id === conversationId ? state.files : []
  return { files, upload, deleteFile, reprocess, refreshFiles, error, clearError: () => setError(null),
    isIndexing: isUploading || files.some(file => file.status === "uploading" || file.status === "processing") }
}
