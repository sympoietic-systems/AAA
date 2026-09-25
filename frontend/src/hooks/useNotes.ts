import { useState, useEffect, useCallback, useRef } from "react"
import { getNotes, createNote, updateNote, deleteNote, type NoteInfo } from "../api/notes"
import { addNotification } from "../stores/notificationStore"

type Visibility = "personal" | "shared" | "agent"
type Query = { assetType?: string; assetId?: string; conversationId?: string }
type NewNote = Parameters<typeof createNote>[0]

/** One owner for loading and mutations; stale reads cannot overwrite successful writes. */
function useNoteCollection(query: Query | null) {
  const key = JSON.stringify(query)
  const [state, setState] = useState<{ key: string; notes: NoteInfo[]; loading: boolean; error: string | null }>({ key, notes: [], loading: false, error: null })
  const [revision, setRevision] = useState(0)
  const scope = useRef(0)
  const reads = useRef(0)
  useEffect(() => {
    const owner = ++scope.current
    return () => { scope.current = owner + 1 }
  }, [key])
  useEffect(() => {
    const controller = new AbortController()
    const request = ++reads.current
    const load = async () => {
      const params = JSON.parse(key) as Query | null
      if (!params) return
      await Promise.resolve()
      if (controller.signal.aborted) return
      setState(previous => ({ key, notes: previous.key === key ? previous.notes : [], loading: true, error: null }))
      try {
        const notes = await getNotes(params, controller.signal)
        if (!controller.signal.aborted && request === reads.current) setState({ key, notes, loading: false, error: null })
      } catch (error) {
        if (!controller.signal.aborted && request === reads.current) {
          setState({ key, notes: [], loading: false, error: error instanceof Error ? error.message : "Unable to load notes" })
        }
      }
    }
    void load()
    return () => controller.abort()
  }, [key, revision])

  const mutate = useCallback(async <T,>(operation: () => Promise<T>, apply: (notes: NoteInfo[], value: T) => NoteInfo[]): Promise<T | null> => {
    const owner = scope.current
    try {
      const value = await operation()
      if (owner === scope.current) {
        reads.current++
        setState(previous => ({ key, notes: apply(previous.key === key ? previous.notes : [], value), loading: false, error: null }))
      }
      return value
    } catch (error) {
      if (owner === scope.current) {
        const message = error instanceof Error ? error.message : "Note operation failed"
        setState(previous => ({ ...previous, error: message }))
        addNotification({ type: "glitch", snippet: message, source: "Notes" })
      }
      return null
    }
  }, [key])
  const create = useCallback((params: NewNote) => mutate(() => createNote(params), (notes, created) => [created, ...notes]), [mutate])
  const editNote = useCallback((id: string, comment?: string, visibility?: Visibility) => mutate(() => updateNote(id, comment, visibility), (notes, updated) => notes.map(note => note.id === id ? updated : note)), [mutate])
  const removeNote = useCallback(async (id: string) => {
    const result = await mutate(async () => { await deleteNote(id); return true }, notes => notes.filter(note => note.id !== id))
    return result === true
  }, [mutate])
  const refreshNotes = useCallback(() => setRevision(value => value + 1), [])
  const visible = query && state.key === key ? state : { notes: [], loading: Boolean(query), error: null }
  return { ...visible, create, editNote, removeNote, refreshNotes }
}

export function useNotes(assetType: string, assetId: string, enabled = true) {
  const { create, ...collection } = useNoteCollection(enabled && assetType && assetId ? { assetType, assetId } : null)
  const addNote = useCallback((selectedText: string, comment = "", visibility: Visibility = "personal", startOffset?: number) =>
    create({ assetType, assetId, selectedText, comment, visibility, startOffset }), [create, assetType, assetId])
  return { ...collection, addNote }
}

export function useConversationNotes(conversationId: string) {
  const { create, ...collection } = useNoteCollection(conversationId ? { conversationId } : null)
  const addNote = useCallback((targetAssetId: number, selectedText: string, comment: string, visibility: Visibility, startOffset?: number) =>
    create({ assetType: "conversation_message", assetId: String(targetAssetId), conversationId, selectedText, comment, visibility, startOffset }), [create, conversationId])
  return { ...collection, addNote }
}
