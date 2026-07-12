import { useState, useRef, useCallback } from "react"

interface PanelResizerOptions {
  storageKey: string
  defaultWidth: number
  minWidth?: number
  computeMaxWidth: () => number
  /**
   * Drag direction relative to the panel edge the handle sits on.
   * "right" (default): handle on the panel's right edge — dragging right grows it (left panel).
   * "left": handle on the panel's left edge — dragging left grows it (right panel).
   */
  direction?: "left" | "right"
}

export function usePanelResizer({
  storageKey,
  defaultWidth,
  minWidth = 200,
  computeMaxWidth,
  direction = "right",
}: PanelResizerOptions) {
  const [collapsed, setCollapsed] = useState(false)
  const [width, setWidth] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey)
      return saved ? parseInt(saved, 10) : defaultWidth
    } catch {
      return defaultWidth
    }
  })
  const widthRef = useRef(width)
  widthRef.current = width

  const maxWidthRef = useRef(computeMaxWidth)
  maxWidthRef.current = computeMaxWidth

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    const startX = e.clientX
    const startWidth = widthRef.current
    document.body.style.cursor = "col-resize"
    document.body.style.userSelect = "none"

    const onMove = (ev: MouseEvent) => {
      const maxWidth = maxWidthRef.current()
      const delta = direction === "left" ? startX - ev.clientX : ev.clientX - startX
      const w = Math.max(
        minWidth,
        Math.min(maxWidth, startWidth + delta)
      )
      widthRef.current = w
      setWidth(w)
    }

    const onUp = () => {
      try {
        localStorage.setItem(storageKey, String(widthRef.current))
      } catch { /* ignore */ }
      document.removeEventListener("mousemove", onMove)
      document.removeEventListener("mouseup", onUp)
      document.body.style.cursor = ""
      document.body.style.userSelect = ""
    }

    document.addEventListener("mousemove", onMove)
    document.addEventListener("mouseup", onUp)
  }, [minWidth, storageKey, direction])

  return { width, collapsed, setCollapsed, handleResizeStart }
}
