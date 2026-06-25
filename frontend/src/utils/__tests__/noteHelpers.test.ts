import { describe, it, expect } from 'vitest'
import { buildNotesMap } from '../noteHelpers'
import type { NoteInfo } from '../../api/client'

function makeNote(overrides: Partial<NoteInfo> = {}): NoteInfo {
  return {
    id: 'n1',
    asset_type: 'conversation_message',
    asset_id: '1',
    conversation_id: 'c1',
    selected_text: 'hello',
    comment: 'world',
    visibility: 'personal',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('buildNotesMap', () => {
  it('returns empty map for empty array', () => {
    const result = buildNotesMap([])
    expect(result.size).toBe(0)
  })

  it('groups notes by asset_id (message_id)', () => {
    const notes = [
      makeNote({ id: 'n1', asset_id: '1' }),
      makeNote({ id: 'n2', asset_id: '1' }),
      makeNote({ id: 'n3', asset_id: '2' }),
    ]
    const result = buildNotesMap(notes)
    expect(result.get(1)).toHaveLength(2)
    expect(result.get(2)).toHaveLength(1)
  })

  it('skips notes from non-conversation assets', () => {
    const notes = [
      makeNote({ id: 'n1', asset_id: '1' }),
      makeNote({ id: 'n2', asset_type: 'research_task', asset_id: 'r1' }),
    ]
    const result = buildNotesMap(notes)
    expect(result.get(1)).toHaveLength(1)
    expect(result.size).toBe(1)
  })

  it('returns correct notes for each asset_id', () => {
    const notes = [
      makeNote({ id: 'a', asset_id: '10', comment: 'first' }),
      makeNote({ id: 'b', asset_id: '10', comment: 'second' }),
      makeNote({ id: 'c', asset_id: '20', comment: 'third' }),
    ]
    const result = buildNotesMap(notes)
    expect(result.get(10)?.map((n) => n.comment)).toEqual(['first', 'second'])
    expect(result.get(20)?.map((n) => n.comment)).toEqual(['third'])
  })
})
