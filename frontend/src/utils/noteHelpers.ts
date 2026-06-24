import type { NoteInfo } from "../api/client"

export const EMPTY_NOTE_ARRAY: NoteInfo[] = []

export function buildNotesMap(notes: NoteInfo[]): Map<number, NoteInfo[]> {
  const map = new Map<number, NoteInfo[]>()
  for (const note of notes) {
    if (note.message_id !== undefined && note.message_id !== null) {
      const existing = map.get(note.message_id)
      if (existing) {
        existing.push(note)
      } else {
        map.set(note.message_id, [note])
      }
    }
  }
  return map
}
