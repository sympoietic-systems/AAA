import { describe, it, expect } from 'vitest'
import {
  DIMENSION_NAMES,
  areNumberArraysEqual,
  areStringArraysEqual,
  areNotesEqual,
} from '../messageBubbleUtils'
import type { NoteInfo } from '../../../../api/client'

describe('DIMENSION_NAMES', () => {
  it('has 16 dimensions', () => {
    expect(DIMENSION_NAMES).toHaveLength(16)
  })

  it('contains expected dimension names', () => {
    expect(DIMENSION_NAMES[0]).toBe('Homeostatic')
    expect(DIMENSION_NAMES[1]).toBe('Amplifying')
    expect(DIMENSION_NAMES[15]).toBe('Substrate Materiality')
  })
})

describe('areNumberArraysEqual', () => {
  it('returns true for same reference', () => {
    const arr = [1, 2, 3]
    expect(areNumberArraysEqual(arr, arr)).toBe(true)
  })

  it('returns true for null vs null', () => {
    expect(areNumberArraysEqual(null, null)).toBe(true)
  })

  it('returns true for undefined vs undefined', () => {
    expect(areNumberArraysEqual(undefined, undefined)).toBe(true)
  })

  it('returns false when one is null and other is defined', () => {
    expect(areNumberArraysEqual(null, [1])).toBe(false)
    expect(areNumberArraysEqual([1], null)).toBe(false)
  })

  it('returns false for different lengths', () => {
    expect(areNumberArraysEqual([1, 2], [1, 2, 3])).toBe(false)
  })

  it('returns false for different values', () => {
    expect(areNumberArraysEqual([1, 2], [1, 3])).toBe(false)
  })

  it('returns true for same values', () => {
    expect(areNumberArraysEqual([1, 2, 3], [1, 2, 3])).toBe(true)
  })

  it('returns true for empty arrays', () => {
    expect(areNumberArraysEqual([], [])).toBe(true)
  })
})

describe('areStringArraysEqual', () => {
  it('returns true for same reference', () => {
    const arr = ['a', 'b']
    expect(areStringArraysEqual(arr, arr)).toBe(true)
  })

  it('returns true for null vs null', () => {
    expect(areStringArraysEqual(null, null)).toBe(true)
  })

  it('returns false when one is null and other is defined', () => {
    expect(areStringArraysEqual(null, ['a'])).toBe(false)
  })

  it('returns false for different values', () => {
    expect(areStringArraysEqual(['a'], ['b'])).toBe(false)
  })

  it('returns true for same values', () => {
    expect(areStringArraysEqual(['a', 'b'], ['a', 'b'])).toBe(true)
  })
})

describe('areNotesEqual', () => {
  function makeNote(overrides: Partial<NoteInfo> = {}): NoteInfo {
    return {
      id: 'n1',
      message_id: 1,
      selected_text: 'hello',
      comment: 'world',
      visibility: 'personal',
      conversation_id: 'c1',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      ...overrides,
    }
  }

  it('returns true for same reference', () => {
    const notes = [makeNote()]
    expect(areNotesEqual(notes, notes)).toBe(true)
  })

  it('returns true for null vs null', () => {
    expect(areNotesEqual(null, null)).toBe(true)
  })

  it('returns false when one is null', () => {
    expect(areNotesEqual(null, [makeNote()])).toBe(false)
  })

  it('returns false for different lengths', () => {
    expect(areNotesEqual([makeNote()], [makeNote(), makeNote({ id: 'n2' })])).toBe(false)
  })

  it('returns false for different comments', () => {
    const a = [makeNote({ comment: 'a' })]
    const b = [makeNote({ comment: 'b' })]
    expect(areNotesEqual(a, b)).toBe(false)
  })

  it('returns false for different visibility', () => {
    const a = [makeNote({ visibility: 'personal' })]
    const b = [makeNote({ visibility: 'shared' })]
    expect(areNotesEqual(a, b)).toBe(false)
  })

  it('returns true for equal notes', () => {
    const a = [makeNote()]
    const b = [makeNote()]
    expect(areNotesEqual(a, b)).toBe(true)
  })
})
