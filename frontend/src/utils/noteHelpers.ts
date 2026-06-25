import type { NoteInfo } from "../api/client"

export const EMPTY_NOTE_ARRAY: NoteInfo[] = []

export function buildNotesMap(notes: NoteInfo[]): Map<number, NoteInfo[]> {
  const map = new Map<number, NoteInfo[]>()
  for (const note of notes) {
    if (note.asset_type !== "conversation_message") continue
    const msgId = Number(note.asset_id)
    if (Number.isNaN(msgId)) continue
    const existing = map.get(msgId)
    if (existing) {
      existing.push(note)
    } else {
      map.set(msgId, [note])
    }
  }
  return map
}
