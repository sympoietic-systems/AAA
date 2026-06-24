import { describe, it, expect } from 'vitest'
import { estimateTokens, getAncestorPathIds } from '../useChatHelpers'
import type { ChatMessage } from '../../api/client'

function makeMsg(id: number, parentId?: number): ChatMessage {
  return {
    id,
    timestamp: new Date().toISOString(),
    speaker: 'human',
    content: `message ${id}`,
    parent_message_id: parentId ?? undefined,
  }
}

describe('estimateTokens', () => {
  it('returns 0 for empty string', () => {
    expect(estimateTokens('')).toBe(0)
  })

  it('returns minimum 1 for whitespace-only string (floor(len/4) floors to 0, clamped to 1)', () => {
    expect(estimateTokens('   ')).toBe(1)
  })

  it('returns at least 1 for short text', () => {
    expect(estimateTokens('hi')).toBe(1)
  })

  it('estimates tokens as floor(len / 4)', () => {
    expect(estimateTokens('hello world')).toBe(2)
  })

  it('handles long text', () => {
    const long = 'a'.repeat(100)
    expect(estimateTokens(long)).toBe(25)
  })
})

describe('getAncestorPathIds', () => {
  it('returns empty set for null leafId', () => {
    expect(getAncestorPathIds([], null).size).toBe(0)
  })

  it('returns singleton set for root message with no parent', () => {
    const msgs = [makeMsg(1)]
    const path = getAncestorPathIds(msgs, 1)
    expect(path.has(1)).toBe(true)
    expect(path.size).toBe(1)
  })

  it('returns ancestor chain for leaf node', () => {
    const msgs = [
      makeMsg(1),
      makeMsg(2, 1),
      makeMsg(3, 2),
      makeMsg(4, 3),
    ]
    const path = getAncestorPathIds(msgs, 4)
    expect(path.has(1)).toBe(true)
    expect(path.has(2)).toBe(true)
    expect(path.has(3)).toBe(true)
    expect(path.has(4)).toBe(true)
    expect(path.size).toBe(4)
  })

  it('handles unsorted messages', () => {
    const msgs = [
      makeMsg(4, 3),
      makeMsg(1),
      makeMsg(3, 2),
      makeMsg(2, 1),
    ]
    const path = getAncestorPathIds(msgs, 4)
    expect(path.has(1)).toBe(true)
    expect(path.has(2)).toBe(true)
    expect(path.has(3)).toBe(true)
    expect(path.has(4)).toBe(true)
  })

  it('does not include siblings outside the path', () => {
    const msgs = [
      makeMsg(1),
      makeMsg(2, 1),
      makeMsg(3, 1),
      makeMsg(4, 2),
    ]
    const path = getAncestorPathIds(msgs, 4)
    expect(path.has(1)).toBe(true)
    expect(path.has(2)).toBe(true)
    expect(path.has(4)).toBe(true)
    expect(path.has(3)).toBe(false)
  })

  it('returns path with only leafId when message is not in list', () => {
    const msgs = [makeMsg(1), makeMsg(2, 1)]
    const path = getAncestorPathIds(msgs, 999)
    expect(path.has(999)).toBe(true)
    expect(path.size).toBe(1)
  })
})
