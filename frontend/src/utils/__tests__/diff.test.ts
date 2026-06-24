import { describe, it, expect } from 'vitest'
import { computeLineDiff } from '../diff'

describe('computeLineDiff', () => {
  it('returns empty array for two empty strings', () => {
    expect(computeLineDiff('', '')).toEqual([])
  })

  it('marks added lines', () => {
    const result = computeLineDiff('', 'line1\nline2')
    expect(result).toEqual([
      { type: 'added', value: 'line1' },
      { type: 'added', value: 'line2' },
    ])
  })

  it('marks removed lines', () => {
    const result = computeLineDiff('line1\nline2', '')
    expect(result).toEqual([
      { type: 'removed', value: 'line1' },
      { type: 'removed', value: 'line2' },
    ])
  })

  it('marks unchanged lines', () => {
    const result = computeLineDiff('a\nb', 'a\nb')
    expect(result).toEqual([
      { type: 'unchanged', value: 'a' },
      { type: 'unchanged', value: 'b' },
    ])
  })

  it('handles mixed changes', () => {
    const result = computeLineDiff('a\nb\nc', 'a\nx\nc')
    expect(result).toEqual([
      { type: 'unchanged', value: 'a' },
      { type: 'removed', value: 'b' },
      { type: 'added', value: 'x' },
      { type: 'unchanged', value: 'c' },
    ])
  })

  it('handles single-line replacement', () => {
    const result = computeLineDiff('old', 'new')
    expect(result).toEqual([
      { type: 'removed', value: 'old' },
      { type: 'added', value: 'new' },
    ])
  })
})
