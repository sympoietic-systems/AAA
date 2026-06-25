import { useState, useEffect, useCallback } from "react"
import { getNotes, createNote, updateNote, deleteNote, type NoteInfo } from "../api/client"
import { addNotification } from "../stores/notificationStore"

function notifyFailure(source: string, err: any) {
  console.error(`Failed to ${source}:`, err)
  addNotification({
    type: "glitch",
    snippet: `Failed to ${source}: ${err.message || "Unknown resistance"}`,
    source: `Notes.${source}`,
  })
}

export function useNotes(assetType: string, assetId: string, enabled: boolean = true) {
  const [notes, setNotes] = useState<NoteInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refreshNotes = useCallback(async () => {
    if (!enabled || !assetType || !assetId) { setNotes([]); return }
    setLoading(true)
    setError(null)
    try {
      setNotes(await getNotes({ assetType, assetId }))
    } catch (err: any) {
      setError("Failed to load notes")
      notifyFailure("load", err)
    } finally {
      setLoading(false)
    }
  }, [enabled, assetType, assetId])

  useEffect(() => { refreshNotes() }, [refreshNotes])

  const addNote = useCallback(async (
    selectedText: string,
    comment = "",
    visibility: "personal" | "shared" | "agent" = "personal",
    startOffset?: number,
  ) => {
    if (!enabled || !assetType || !assetId) return null
    setError(null)
    try {
      const note = await createNote({ assetType, assetId, selectedText, comment, visibility, startOffset })
      setNotes((prev) => [...prev, note])
      return note
    } catch (err: any) {
      setError("Failed to add note")
      notifyFailure("add", err)
      return null
    }
  }, [enabled, assetType, assetId])

  const editNote = useCallback(async (
    noteId: string,
    comment?: string,
    visibility?: "personal" | "shared" | "agent",
  ) => {
    if (!enabled) return null
    setError(null)
    try {
      const updated = await updateNote(noteId, comment, visibility)
      setNotes((prev) => prev.map((n) => (n.id === noteId ? updated : n)))
      return updated
    } catch (err: any) {
      setError("Failed to edit note")
      notifyFailure("edit", err)
      return null
    }
  }, [enabled])

  const removeNote = useCallback(async (noteId: string) => {
    if (!enabled) return null
    setError(null)
    try {
      await deleteNote(noteId)
      setNotes((prev) => prev.filter((n) => n.id !== noteId))
    } catch (err: any) {
      setError("Failed to delete note")
      notifyFailure("delete", err)
    }
  }, [enabled])

  return { notes, loading, error, refreshNotes, addNote, editNote, removeNote }
}

export function useConversationNotes(conversationId: string) {
  const [notes, setNotes] = useState<NoteInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refreshNotes = useCallback(async () => {
    if (!conversationId) { setNotes([]); return }
    setLoading(true)
    setError(null)
    try {
      setNotes(await getNotes({ conversationId }))
    } catch (err: any) {
      setError("Failed to load notes")
      notifyFailure("load", err)
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  useEffect(() => { refreshNotes() }, [refreshNotes])

  const addNote = useCallback(async (
    messageId: number,
    selectedText: string,
    comment = "",
    visibility: "personal" | "shared" | "agent" = "personal",
    startOffset?: number,
  ) => {
    if (!conversationId) return null
    setError(null)
    try {
      const note = await createNote({ assetType: "conversation_message", assetId: String(messageId), conversationId, selectedText, comment, visibility, startOffset })
      setNotes((prev) => [...prev, note])
      return note
    } catch (err: any) {
      setError("Failed to add note")
      notifyFailure("add", err)
      return null
    }
  }, [conversationId])

  const editNote = useCallback(async (
    noteId: string,
    comment?: string,
    visibility?: "personal" | "shared" | "agent",
  ) => {
    if (!conversationId) return null
    setError(null)
    try {
      const updated = await updateNote(noteId, comment, visibility)
      setNotes((prev) => prev.map((n) => (n.id === noteId ? updated : n)))
      return updated
    } catch (err: any) {
      setError("Failed to edit note")
      notifyFailure("edit", err)
      return null
    }
  }, [conversationId])

  const removeNote = useCallback(async (noteId: string) => {
    if (!conversationId) return
    setError(null)
    try {
      await deleteNote(noteId)
      setNotes((prev) => prev.filter((n) => n.id !== noteId))
    } catch (err: any) {
      setError("Failed to delete note")
      notifyFailure("delete", err)
    }
  }, [conversationId])

  return { notes, loading, error, refreshNotes, addNote, editNote, removeNote }
}
