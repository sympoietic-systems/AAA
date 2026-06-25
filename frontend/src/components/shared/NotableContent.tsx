import { memo, useState, useRef, useCallback, useEffect } from "react"
import { SelectionToolbar } from "../pages/nodeexplorer/SelectionToolbar"
import { NoteEditorPopover } from "../pages/nodeexplorer/NoteEditorPopover"
import type { NoteInfo } from "../../api/client"
import { COLOR_PALETTE } from "../../config/colors"

export interface NotableContentHooks {
  addNote: (selectedText: string, comment?: string, visibility?: "personal" | "shared" | "agent", startOffset?: number) => Promise<NoteInfo | null>
  editNote: (noteId: string, comment?: string, visibility?: "personal" | "shared" | "agent") => Promise<NoteInfo | null>
  removeNote: (noteId: string) => Promise<void>
  notes: NoteInfo[]
}

interface NotableContentProps {
  hooks: NotableContentHooks
  title?: string
  children: React.ReactNode
  className?: string
}

const VISIBILITY_COLORS: Record<string, string> = {
  personal: COLOR_PALETTE.notePersonal,
  shared: COLOR_PALETTE.noteShared,
  agent: COLOR_PALETTE.noteAgent,
}

function clearHighlights(container: HTMLElement) {
  const marks = container.querySelectorAll("mark[data-note-id]")
  marks.forEach((mark) => {
    const parent = mark.parentNode
    if (parent) {
      parent.replaceChild(document.createTextNode(mark.textContent || ""), mark)
    }
  })
  container.normalize()
}

function applyHighlights(container: HTMLElement, notes: NoteInfo[]) {
  for (const note of notes) {
    if (!note.selected_text.trim()) continue
    highlightText(container, note.selected_text.trim(), note.id, note.visibility)
  }
}

function highlightText(container: Element, searchText: string, noteId: string, visibility: string) {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) => {
      const parent = node.parentElement
      return parent?.closest("mark[data-note-id], button, input, textarea, select, script, style, svg")
        ? NodeFilter.FILTER_REJECT
        : NodeFilter.FILTER_ACCEPT
    },
  })
  const textNodes: Text[] = []
  while (walker.nextNode()) textNodes.push(walker.currentNode as Text)

  const color = VISIBILITY_COLORS[visibility] || "#eab308"
  const escaped = searchText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")

  for (const node of textNodes) {
    const text = node.textContent || ""
    const regex = new RegExp(escaped, "g")
    const matches: { index: number; length: number }[] = []
    let m: RegExpExecArray | null
    while ((m = regex.exec(text)) !== null) {
      matches.push({ index: m.index, length: m[0].length })
    }
    if (matches.length === 0) continue

    const fragment = document.createDocumentFragment()
    let lastIdx = 0
    for (const { index, length } of matches) {
      if (index > lastIdx) {
        fragment.appendChild(document.createTextNode(text.slice(lastIdx, index)))
      }
      const mark = document.createElement("mark")
      mark.setAttribute("data-note-id", noteId)
      mark.textContent = text.slice(index, index + length)
      mark.style.cssText = `background:${color}20;color:${color};border-bottom:1px solid ${color}40;cursor:pointer;border-radius:2px;padding:0 1px`
      fragment.appendChild(mark)
      lastIdx = index + length
    }
    if (lastIdx < text.length) {
      fragment.appendChild(document.createTextNode(text.slice(lastIdx)))
    }
    node.parentNode?.replaceChild(fragment, node)
  }
}

export const NotableContent = memo(function NotableContent({
  hooks,
  title,
  children,
  className,
}: NotableContentProps) {
  const [selectedText, setSelectedText] = useState("")
  const [showToolbar, setShowToolbar] = useState(false)
  const [showEditor, setShowEditor] = useState(false)
  const [noteComment, setNoteComment] = useState("")
  const [noteVisibility, setNoteVisibility] = useState<"personal" | "shared" | "agent">("personal")
  const [popupCoords, setPopupCoords] = useState<{ x: number; y: number } | null>(null)
  const [editingNote, setEditingNote] = useState<NoteInfo | null>(null)
  const [copied, setCopied] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    clearHighlights(el)
    applyHighlights(el, hooks.notes)
  }, [hooks.notes, children])

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const mark = (e.target as HTMLElement).closest("mark[data-note-id]") as HTMLElement | null
    if (!mark) return
    e.stopPropagation()
    e.preventDefault()
    const noteId = mark.getAttribute("data-note-id")
    if (!noteId) return
    const note = hooks.notes.find(n => n.id === noteId)
    if (!note) return
    setSelectedText(note.selected_text)
    setNoteComment(note.comment)
    setNoteVisibility(note.visibility)
    setEditingNote(note)
    const rect = mark.getBoundingClientRect()
    const showAbove = rect.bottom + 180 > window.innerHeight
    setPopupCoords({ x: rect.left, y: showAbove ? rect.top - 180 - 8 : rect.bottom + 8 })
    setShowEditor(true)
    window.getSelection()?.removeAllRanges()
  }, [hooks.notes])

  const handleMouseUp = useCallback(() => {
    if (editingNote) return
    const sel = window.getSelection()
    if (!sel) return
    const text = sel.toString().trim()
    if (!text) return
    const anchorNode = sel.anchorNode
    if (!anchorNode || !containerRef.current?.contains(anchorNode)) return
    if (anchorNode.parentElement?.closest("mark[data-note-id]")) return
    setSelectedText(text)
    setShowEditor(false)
    setCopied(false)
    if (sel.rangeCount > 0) {
      const range = sel.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      setPopupCoords({ x: rect.left, y: rect.bottom + 8 })
      setEditingNote(null)
      setShowToolbar(true)
    }
  }, [editingNote])

  const handleDismissToolbar = useCallback(() => {
    setShowToolbar(false)
  }, [])

  const handleOpenEditor = useCallback(() => {
    setNoteComment("")
    setNoteVisibility("personal")
    setShowToolbar(false)
    setShowEditor(true)
  }, [])

  const handleSaveNote = useCallback(async () => {
    if (editingNote) {
      await hooks.editNote(editingNote.id, noteComment, noteVisibility)
      setEditingNote(null)
    } else if (selectedText) {
      await hooks.addNote(selectedText, noteComment, noteVisibility)
    }
    setShowEditor(false)
    setSelectedText("")
    setNoteComment("")
    setPopupCoords(null)
    window.getSelection()?.removeAllRanges()
  }, [editingNote, selectedText, noteComment, noteVisibility, hooks])

  const handleDismissEditor = useCallback(() => {
    setEditingNote(null)
    setShowEditor(false)
    setSelectedText("")
    setNoteComment("")
    setPopupCoords(null)
    window.getSelection()?.removeAllRanges()
  }, [])

  useEffect(() => {
    if (!showToolbar && !showEditor) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleDismissEditor()
        setShowToolbar(false)
        setSelectedText("")
        setPopupCoords(null)
        window.getSelection()?.removeAllRanges()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [showToolbar, showEditor, handleDismissEditor])

  return (
    <div ref={containerRef} onMouseUp={handleMouseUp} onMouseDown={handleMouseDown} className={className}>
      {title && <div className="text-ui-dim text-[8px] mb-1 uppercase">{title}</div>}
      {children}

      {showToolbar && popupCoords && (
        <SelectionToolbar
          selectedText={selectedText}
          popupCoords={popupCoords}
          onDismiss={handleDismissToolbar}
          onOpenNoteEditor={handleOpenEditor}
          copied={copied}
          onCopied={setCopied}
        />
      )}

      {showEditor && popupCoords && (
        <NoteEditorPopover
          selectedText={selectedText}
          noteComment={noteComment}
          noteVisibility={noteVisibility}
          editingNote={editingNote}
          popupCoords={popupCoords}
          onCommentChange={setNoteComment}
          onVisibilityChange={setNoteVisibility}
          onSave={handleSaveNote}
          onDismiss={handleDismissEditor}
          onDeleteNote={editingNote ? hooks.removeNote : undefined}
        />
      )}
    </div>
  )
})
