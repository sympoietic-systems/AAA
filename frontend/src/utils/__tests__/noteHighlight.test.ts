import { describe, it, expect } from 'vitest'
import { wrapSelectedTextInMarks } from '../noteHighlight'
import type { NoteInfo } from '../../api/client'

function makeNote(overrides: Partial<NoteInfo> = {}): NoteInfo {
  return {
    id: 'n1',
    asset_type: 'research_task',
    asset_id: 't1',
    conversation_id: null,
    selected_text: 'hello',
    comment: '',
    visibility: 'personal',
    created_at: '',
    updated_at: '',
    ...overrides,
  }
}

describe('wrapSelectedTextInMarks', () => {
  it('returns original markdown for empty notes', () => {
    expect(wrapSelectedTextInMarks('hello world', [])).toBe('hello world')
  })

  it('wraps single word in mark tags', () => {
    const result = wrapSelectedTextInMarks('hello world', [
      makeNote({ id: 'a', selected_text: 'hello' }),
    ])
    expect(result).toContain('<mark')
    expect(result).toContain('data-note-id="a"')
    expect(result).toContain('</mark>')
  })

  it('handles bold formatting in markdown', () => {
    const result = wrapSelectedTextInMarks('**hello** world', [
      makeNote({ id: 'a', selected_text: 'hello' }),
    ])
    expect(result).toContain('<mark')
    expect(result).toContain('data-note-id="a"')
  })

  it('handles multi-line paragraph breaks', () => {
    const md = 'paragraph one\n\nparagraph two'
    const result = wrapSelectedTextInMarks(md, [
      makeNote({ id: 'a', selected_text: 'paragraph tw' }),
    ])
    expect(result).toContain('<mark')
    expect(result).toContain('data-note-id="a"')
  })

  it('handles text spanning paragraphs', () => {
    const md = 'first paragraph\n\nsecond paragraph\n\nthird paragraph'
    const result = wrapSelectedTextInMarks(md, [
      makeNote({ id: 'a', selected_text: 'first paragraph second paragraph' }),
    ])
    expect(result).toContain('<mark')
    expect(result).toContain('data-note-id="a"')
  })

  it('handles partial word match (selection starts mid-word)', () => {
    const md = 'form of observation'
    const result = wrapSelectedTextInMarks(md, [
      makeNote({ id: 'a', selected_text: 'm of observation' }),
    ])
    expect(result).toContain('<mark')
    expect(result).toContain('data-note-id="a"')
  })

  it('handles nested highlights', () => {
    const md = 'aaa bbb ccc ddd'
    const result = wrapSelectedTextInMarks(md, [
      makeNote({ id: 'a', selected_text: 'aaa bbb ccc ddd' }),
      makeNote({ id: 'b', selected_text: 'bbb ccc' }),
    ])
    expect(result).toContain('data-note-id="a"')
    expect(result).toContain('data-note-id="b"')
  })
})
