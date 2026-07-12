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

  it('grows on rightward drag with default direction and persists on mouseup', () => {
    const { result } = renderHook(() =>
      usePanelResizer({
        storageKey: 'test_panel',
        defaultWidth: 300,
        computeMaxWidth: () => 500,
      })
    )
    act(() => {
      result.current.handleResizeStart({ clientX: 100, preventDefault: () => {} } as any)
    })
    act(() => {
      document.dispatchEvent(new MouseEvent('mousemove', { clientX: 180 }))
    })
    expect(result.current.width).toBe(380)
    act(() => {
      document.dispatchEvent(new MouseEvent('mouseup'))
    })
    expect(localStorage.getItem('test_panel')).toBe('380')
  })

  it('grows on leftward drag when direction is "left"', () => {
    const { result } = renderHook(() =>
      usePanelResizer({
        storageKey: 'test_panel',
        defaultWidth: 300,
        direction: 'left',
        computeMaxWidth: () => 500,
      })
    )
    act(() => {
      result.current.handleResizeStart({ clientX: 200, preventDefault: () => {} } as any)
    })
    act(() => {
      document.dispatchEvent(new MouseEvent('mousemove', { clientX: 120 }))
    })
    expect(result.current.width).toBe(380)
  })

  it('clamps width to computeMaxWidth', () => {
    const { result } = renderHook(() =>
      usePanelResizer({
        storageKey: 'test_panel',
        defaultWidth: 300,
        computeMaxWidth: () => 400,
      })
    )
    act(() => {
      result.current.handleResizeStart({ clientX: 0, preventDefault: () => {} } as any)
    })
    act(() => {
      document.dispatchEvent(new MouseEvent('mousemove', { clientX: 999 }))
    })
    expect(result.current.width).toBe(400)
  })
})
