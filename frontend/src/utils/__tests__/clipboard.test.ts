import { describe, it, expect, vi } from 'vitest'
import { copyToClipboard } from '../clipboard'

describe('copyToClipboard', () => {
  it('uses navigator.clipboard.writeText when available', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', {
      clipboard: { writeText },
    })

    const result = await copyToClipboard('test text')
    expect(result).toBe(true)
    expect(writeText).toHaveBeenCalledWith('test text')

    vi.unstubAllGlobals()
  })

  it('falls back to execCommand when clipboard API fails', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('denied'))
    const execCommand = vi.fn().mockReturnValue(true)
    vi.stubGlobal('navigator', {
      clipboard: { writeText },
    })

    const originalExec = document.execCommand
    document.execCommand = execCommand

    const result = await copyToClipboard('fallback text')
    expect(result).toBe(true)
    expect(execCommand).toHaveBeenCalledWith('copy')

    document.execCommand = originalExec
    vi.unstubAllGlobals()
  })

  it('falls back to execCommand when clipboard API is missing', async () => {
    vi.stubGlobal('navigator', {})

    const execCommand = vi.fn().mockReturnValue(true)
    const originalExec = document.execCommand
    document.execCommand = execCommand

    const result = await copyToClipboard('no api text')
    expect(result).toBe(true)
    expect(execCommand).toHaveBeenCalledWith('copy')

    document.execCommand = originalExec
    vi.unstubAllGlobals()
  })

  it('returns false when both methods fail', async () => {
    vi.stubGlobal('navigator', {})

    const execCommand = vi.fn().mockReturnValue(false)
    const originalExec = document.execCommand
    document.execCommand = execCommand

    const result = await copyToClipboard('doomed')
    expect(result).toBe(false)

    document.execCommand = originalExec
    vi.unstubAllGlobals()
  })
})
