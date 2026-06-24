import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePanelResizer } from '../usePanelResizer'

beforeEach(() => {
  localStorage.clear()
})

describe('usePanelResizer', () => {
  it('returns default width when localStorage is empty', () => {
    const { result } = renderHook(() =>
      usePanelResizer({
        storageKey: 'test_panel',
        defaultWidth: 320,
        computeMaxWidth: () => 500,
      })
    )
    expect(result.current.width).toBe(320)
    expect(result.current.collapsed).toBe(false)
  })

  it('reads initial width from localStorage', () => {
    localStorage.setItem('test_panel', '400')
    const { result } = renderHook(() =>
      usePanelResizer({
        storageKey: 'test_panel',
        defaultWidth: 320,
        computeMaxWidth: () => 500,
      })
    )
    expect(result.current.width).toBe(400)
  })

  it('can toggle collapsed state', () => {
    const { result } = renderHook(() =>
      usePanelResizer({
        storageKey: 'test_panel',
        defaultWidth: 320,
        computeMaxWidth: () => 500,
      })
    )
    expect(result.current.collapsed).toBe(false)
    act(() => {
      result.current.setCollapsed(true)
    })
    expect(result.current.collapsed).toBe(true)
  })

  it('returns handleResizeStart as a function', () => {
    const { result } = renderHook(() =>
      usePanelResizer({
        storageKey: 'test_panel',
        defaultWidth: 320,
        computeMaxWidth: () => 500,
      })
    )
    expect(typeof result.current.handleResizeStart).toBe('function')
  })

  it('uses custom minWidth', () => {
    const { result } = renderHook(() =>
      usePanelResizer({
        storageKey: 'test_panel',
        defaultWidth: 150,
        minWidth: 100,
        computeMaxWidth: () => 500,
      })
    )
    expect(result.current.width).toBe(150)
  })
})
