import { useState, useEffect, useCallback } from "react"
import { getNotes, createNote, updateNote, deleteNote, type NoteInfo } from "../api/client"

export function useNotes(conversationId: string) {
  const [notes, setNotes] = useState<NoteInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refreshNotes = useCallback(async () => {
    if (!conversationId) {
      setNotes([])
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await getNotes(conversationId)
      setNotes(data)
    } catch (err) {
      console.error("Failed to load notes:", err)
      setError("Failed to load notes")
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  useEffect(() => {
    refreshNotes()
  }, [conversationId, refreshNotes])

  const addNote = useCallback(async (
    messageId: number,
    selectedText: string,
    comment = "",
    visibility: "personal" | "shared" | "agent" = "personal",
    startOffset?: number
  ) => {
    if (!conversationId) return null
    setError(null)
    try {
      const newNote = await createNote(conversationId, messageId, selectedText, comment, visibility, startOffset)
      setNotes((prev) => [...prev, newNote])
      return newNote
    } catch (err) {
      console.error("Failed to add note:", err)
      setError("Failed to add note")
      return null
    }
  }, [conversationId])

  const editNote = useCallback(async (
    noteId: string,
    comment?: string,
    visibility?: "personal" | "shared" | "agent"
  ) => {
    if (!conversationId) return null
    setError(null)
    try {
      const updated = await updateNote(conversationId, noteId, comment, visibility)
      setNotes((prev) => prev.map((n) => (n.id === noteId ? updated : n)))
      return updated
    } catch (err) {
      console.error("Failed to edit note:", err)
      setError("Failed to edit note")
      return null
    }
  }, [conversationId])

  const removeNote = useCallback(async (noteId: string) => {
    if (!conversationId) return
    setError(null)
    try {
      await deleteNote(conversationId, noteId)
      setNotes((prev) => prev.filter((n) => n.id !== noteId))
    } catch (err) {
      console.error("Failed to delete note:", err)
      setError("Failed to delete note")
    }
  }, [conversationId])

  return {
    notes,
    loading,
    error,
    refreshNotes,
    addNote,
    editNote,
    removeNote,
  }
}
