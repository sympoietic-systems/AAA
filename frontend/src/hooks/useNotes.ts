import { useState, useEffect, useCallback, useRef } from "react"
import {
  getNotes,
  createNote,
  updateNote,
  deleteNote,
  type NoteInfo,
} from "../api/client"
import { addNotification } from "../stores/notificationStore"

function notifyFailure(op: string, err: unknown) {
  const msg = err instanceof Error ? err.message : String(err)
  addNotification({
    type: "glitch",
    snippet: `Notes: Failed to ${op}: ${msg}`,
    source: "Notes",
  })
}

export function useNotes(assetType: string, assetId: string, enabled: boolean = true) {
  const [notes, setNotes] = useState<NoteInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const currentAssetRef = useRef(`${assetType}:${assetId}`)

  const fetchNotes = useCallback(async (targetType: string, targetId: string) => {
    if (!enabled || !targetType || !targetId) {
      setNotes([])
      return
    }
    const targetKey = `${targetType}:${targetId}`
    setLoading(true)
    setError(null)
    try {
      const data = await getNotes({ assetType: targetType, assetId: targetId })
      if (currentAssetRef.current === targetKey) {
        setNotes(data)
      }
    } catch (err: unknown) {
      if (currentAssetRef.current === targetKey) {
        setError("Failed to load notes")
        notifyFailure("load", err)
      }
    } finally {
      if (currentAssetRef.current === targetKey) {
        setLoading(false)
      }
    }
  }, [enabled])

  useEffect(() => {
    currentAssetRef.current = `${assetType}:${assetId}`
    let cancelled = false

    const load = async () => {
      if (!enabled || !assetType || !assetId) {
        if (!cancelled) setNotes([])
        return
      }
      setLoading(true)
      setError(null)
      try {
        const data = await getNotes({ assetType, assetId })
        if (!cancelled && currentAssetRef.current === `${assetType}:${assetId}`) {
          setNotes(data)
        }
      } catch (err: unknown) {
        if (!cancelled && currentAssetRef.current === `${assetType}:${assetId}`) {
          setError("Failed to load notes")
          notifyFailure("load", err)
        }
      } finally {
        if (!cancelled && currentAssetRef.current === `${assetType}:${assetId}`) {
          setLoading(false)
        }
      }
    }

    load()

    return () => {
      cancelled = true
    }
  }, [assetType, assetId, enabled])

  const addNote = useCallback(async (
    selectedText: string,
    comment?: string,
    visibility: "personal" | "shared" | "agent" = "personal",
    startOffset?: number
  ) => {
    try {
      const created = await createNote({
        assetType,
        assetId,
        comment: comment ?? "",
        visibility,
        selectedText,
        startOffset,
      })
      setNotes(prev => [created, ...prev])
      return created
    } catch (err: unknown) {
      notifyFailure("create note", err)
      return null
    }
  }, [assetType, assetId])

  const editNote = useCallback(async (
    noteId: string,
    comment?: string,
    visibility?: "personal" | "shared" | "agent"
  ) => {
    try {
      const updated = await updateNote(noteId, comment, visibility)
      setNotes(prev => prev.map(n => n.id === noteId ? updated : n))
      return updated
    } catch (err: unknown) {
      notifyFailure("update note", err)
      return null
    }
  }, [])

  const removeNote = useCallback(async (noteId: string) => {
    try {
      await deleteNote(noteId)
      setNotes(prev => prev.filter(n => n.id !== noteId))
      return true
    } catch (err: unknown) {
      notifyFailure("delete note", err)
      return false
    }
  }, [])

  const refreshNotes = useCallback(() => {
    if (assetType && assetId) {
      fetchNotes(assetType, assetId)
    }
  }, [assetType, assetId, fetchNotes])

  return {
    notes,
    loading,
    error,
    addNote,
    editNote,
    removeNote,
    refreshNotes,
  }
}

export function useConversationNotes(conversationId: string) {
  const [notes, setNotes] = useState<NoteInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const currentConvRef = useRef(conversationId)

  const fetchNotes = useCallback(async (targetId: string) => {
    if (!targetId) {
      setNotes([])
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await getNotes({ conversationId: targetId })
      if (currentConvRef.current === targetId) {
        setNotes(data)
      }
    } catch (err: unknown) {
      if (currentConvRef.current === targetId) {
        setError("Failed to load notes")
        notifyFailure("load", err)
      }
    } finally {
      if (currentConvRef.current === targetId) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    currentConvRef.current = conversationId
    let cancelled = false

    const load = async () => {
      if (!conversationId) {
        if (!cancelled) setNotes([])
        return
      }
      setLoading(true)
      setError(null)
      try {
        const data = await getNotes({ conversationId })
        if (!cancelled && currentConvRef.current === conversationId) {
          setNotes(data)
        }
      } catch (err: unknown) {
        if (!cancelled && currentConvRef.current === conversationId) {
          setError("Failed to load notes")
          notifyFailure("load", err)
        }
      } finally {
        if (!cancelled && currentConvRef.current === conversationId) {
          setLoading(false)
        }
      }
    }

    load()

    return () => {
      cancelled = true
    }
  }, [conversationId])

  const addNote = useCallback(async (
    targetAssetId: number,
    selectedText: string,
    comment: string,
    visibility: "personal" | "shared" | "agent",
    startOffset?: number
  ) => {
    try {
      const created = await createNote({
        assetType: "message",
        assetId: String(targetAssetId),
        conversationId,
        comment,
        visibility,
        selectedText,
        startOffset,
      })
      setNotes(prev => [created, ...prev])
      return created
    } catch (err: unknown) {
      notifyFailure("create note", err)
      return null
    }
  }, [conversationId])

  const editNote = useCallback(async (
    noteId: string,
    comment?: string,
    visibility?: "personal" | "shared" | "agent"
  ) => {
    try {
      const updated = await updateNote(noteId, comment, visibility)
      setNotes(prev => prev.map(n => n.id === noteId ? updated : n))
      return updated
    } catch (err: unknown) {
      notifyFailure("update note", err)
      return null
    }
  }, [])

  const removeNote = useCallback(async (noteId: string) => {
    try {
      await deleteNote(noteId)
      setNotes(prev => prev.filter(n => n.id !== noteId))
      return true
    } catch (err: unknown) {
      notifyFailure("delete note", err)
      return false
    }
  }, [])

  const refreshNotes = useCallback(() => {
    if (conversationId) {
      fetchNotes(conversationId)
    }
  }, [conversationId, fetchNotes])

  return {
    notes,
    loading,
    error,
    addNote,
    editNote,
    removeNote,
    refreshNotes,
  }
}
