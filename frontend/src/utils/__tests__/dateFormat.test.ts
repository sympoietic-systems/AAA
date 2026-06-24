import { describe, it, expect } from 'vitest'
import {
  formatTime,
  formatTimeShort,
  formatDateTime,
  formatDateTimeFull,
  formatTimestamp,
  formatRelativeTime,
} from '../dateFormat'

const VALID_ISO = '2024-06-15T14:30:45.000Z'

describe('formatTime', () => {
  it('returns empty string for null', () => {
    expect(formatTime(null)).toBe('')
  })

  it('returns empty string for undefined', () => {
    expect(formatTime(undefined)).toBe('')
  })

  it('returns empty string for empty string', () => {
    expect(formatTime('')).toBe('')
  })

  it('returns a time string for valid ISO', () => {
    const result = formatTime(VALID_ISO)
    expect(result).toBeTruthy()
    expect(result).toMatch(/\d{2}:\d{2}:\d{2}/)
  })

  it('returns the input unchanged for invalid date', () => {
    expect(formatTime('not-a-date')).toBe('not-a-date')
  })
})

describe('formatTimeShort', () => {
  it('returns empty string for null', () => {
    expect(formatTimeShort(null)).toBe('')
  })

  it('returns a short time string for valid ISO', () => {
    const result = formatTimeShort(VALID_ISO)
    expect(result).toBeTruthy()
    expect(result).toMatch(/\d{2}:\d{2}/)
  })
})

describe('formatDateTime', () => {
  it('returns empty string for null', () => {
    expect(formatDateTime(null)).toBe('')
  })

  it('returns a formatted date-time for valid ISO', () => {
    const result = formatDateTime(VALID_ISO)
    expect(result).toBeTruthy()
    expect(result.length).toBeGreaterThan(5)
  })

  it('returns the input unchanged for invalid date', () => {
    expect(formatDateTime('garbage')).toBe('garbage')
  })
})

describe('formatDateTimeFull', () => {
  it('returns empty string for null', () => {
    expect(formatDateTimeFull(null)).toBe('')
  })

  it('returns a string for valid ISO', () => {
    const result = formatDateTimeFull(VALID_ISO)
    expect(result).toBeTruthy()
    expect(result.length).toBeGreaterThan(10)
  })
})

describe('formatTimestamp', () => {
  it('returns empty string for null', () => {
    expect(formatTimestamp(null)).toBe('')
  })

  it('returns YYYY-MM-DD HH:MM:SS format', () => {
    const result = formatTimestamp(VALID_ISO)
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)
  })

  it('returns the input unchanged for invalid date', () => {
    expect(formatTimestamp('bad')).toBe('bad')
  })
})

describe('formatRelativeTime', () => {
  it('returns empty string for null', () => {
    expect(formatRelativeTime(null)).toBe('')
  })

  it('returns "just now" for future date', () => {
    const future = new Date(Date.now() + 60000).toISOString()
    expect(formatRelativeTime(future)).toBe('just now')
  })

  it('returns seconds ago', () => {
    const recent = new Date(Date.now() - 30000).toISOString()
    expect(formatRelativeTime(recent)).toMatch(/^\d+s ago$/)
  })

  it('returns minutes ago', () => {
    const minAgo = new Date(Date.now() - 5 * 60000).toISOString()
    expect(formatRelativeTime(minAgo)).toMatch(/^\d+m ago$/)
  })

  it('returns hours ago', () => {
    const hourAgo = new Date(Date.now() - 3 * 3600000).toISOString()
    expect(formatRelativeTime(hourAgo)).toMatch(/^\d+h ago$/)
  })

  it('returns days ago', () => {
    const dayAgo = new Date(Date.now() - 2 * 86400000).toISOString()
    expect(formatRelativeTime(dayAgo)).toMatch(/^\d+d ago$/)
  })
})
