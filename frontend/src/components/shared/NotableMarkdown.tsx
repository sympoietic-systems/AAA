import { memo, useState, useRef, useCallback, useMemo, useEffect } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import rehypeRaw from "rehype-raw"
import { useNotes } from "../../hooks/useNotes"
import { NotesSection } from "./NotesSection"
import { SelectionToolbar } from "../pages/nodeexplorer/SelectionToolbar"
import { NoteEditorPopover } from "../pages/nodeexplorer/NoteEditorPopover"
import { wrapSelectedTextInMarks } from "../../utils/noteHighlight"
import type { NoteInfo } from "../../api/client"

type ContentTab = "content" | "notes"

interface NotableMarkdownProps {
  assetType: string
  assetId: string
  content: string
  title?: string
  headerActions?: React.ReactNode
  contentRef?: React.RefObject<HTMLDivElement>
  onNoteClick?: (noteId: string) => void
  onNotesChange?: (notes: NoteInfo[]) => void
  className?: string
  contentClassName?: string
}

export const NotableMarkdown = memo(function NotableMarkdown({
  assetType,
  assetId,
  content,
  title,
  headerActions,
  contentRef,
  onNoteClick,
  onNotesChange,
  className,
  contentClassName,
}: NotableMarkdownProps) {
  const noteHook = useNotes(assetType, assetId)
  const [tab, setTab] = useState<ContentTab>("content")
  const [selectedText, setSelectedText] = useState("")
  const [showToolbar, setShowToolbar] = useState(false)
  const [showEditor, setShowEditor] = useState(false)
  const [noteComment, setNoteComment] = useState("")
  const [noteVisibility, setNoteVisibility] = useState<"personal" | "shared" | "agent">("personal")
  const [popupCoords, setPopupCoords] = useState<{ x: number; y: number } | null>(null)
  const [editingNote, setEditingNote] = useState<NoteInfo | null>(null)
  const [copied, setCopied] = useState(false)
  const internalRef = useRef<HTMLDivElement>(null)
  const reportRef = contentRef ?? internalRef

  const [highlightedContent, setHighlightedContent] = useState(content || "")

  useEffect(() => {
    try {
      setHighlightedContent(wrapSelectedTextInMarks(content || "", noteHook.notes))
    } catch (e) {
      console.error("wrapSelectedTextInMarks failed:", e)
    }
  }, [content, noteHook.notes])

  useEffect(() => {
    if (onNotesChange) onNotesChange(noteHook.notes)
  }, [noteHook.notes, onNotesChange])

  const handleMouseUp = useCallback(() => {
    if (editingNote) return
    const sel = window.getSelection()
    if (!sel) return
    const text = sel.toString().trim()
    if (!text) return
    const anchorNode = sel.anchorNode
    if (!anchorNode || !reportRef.current?.contains(anchorNode)) return
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
  }, [editingNote, reportRef])

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
      await noteHook.editNote(editingNote.id, noteComment, noteVisibility)
      setEditingNote(null)
    } else if (selectedText) {
      await noteHook.addNote(selectedText, noteComment, noteVisibility)
    }
    setShowEditor(false)
    setSelectedText("")
    setNoteComment("")
    setPopupCoords(null)
    window.getSelection()?.removeAllRanges()
  }, [editingNote, selectedText, noteComment, noteVisibility, noteHook])

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

  const handleNoteGoto = useCallback((noteId: string) => {
    setTab("content")
    setTimeout(() => {
      import("../../utils/noteHighlight")
        .then(({ scrollToNoteHighlight }) => scrollToNoteHighlight(noteId))
        .catch(() => {})
    }, 100)
  }, [])

  const handleNoteClick = useCallback((e: React.MouseEvent<HTMLElement>) => {
    e.stopPropagation()
    e.preventDefault()
    const noteId = e.currentTarget.dataset.noteId
    if (!noteId) return
    if (onNoteClick) {
      onNoteClick(noteId)
      return
    }
    const note = noteHook.notes.find(n => n.id === noteId)
    if (!note) return
    setSelectedText(note.selected_text)
    setNoteComment(note.comment)
    setNoteVisibility(note.visibility)
    setEditingNote(note)
    const rect = e.currentTarget.getBoundingClientRect()
    const showAbove = rect.bottom + 180 > window.innerHeight
    setPopupCoords({ x: rect.left, y: showAbove ? rect.top - 180 - 8 : rect.bottom + 8 })
    setShowEditor(true)
  }, [noteHook.notes, onNoteClick])

  const markComponents = useMemo(() => ({
    mark: ({ node, ...props }: any) => {
      const properties = node?.properties ?? {}
      const noteId = properties['data-note-id'] ?? props['data-note-id']
      const styleString = properties['style'] ?? ''
      const styleObj: Record<string, string> = {}
      if (typeof styleString === 'string' && styleString) {
        styleString.split(';').forEach((pair: string) => {
          const [k, v] = pair.split(':').map((s: string) => s.trim())
          if (!k || !v) return
          if (k.startsWith('--')) {
            styleObj[k] = v
          } else {
            const camelKey = k.replace(/-([a-z])/g, (_: string, c: string) => c.toUpperCase())
            styleObj[camelKey] = v
          }
        })
      }
      return (
        <mark
          {...{ 'data-note-id': noteId }}
          className={properties['className'] || ''}
          style={styleObj}
          onClick={handleNoteClick}
        >
          {props.children}
        </mark>
      )
    },
  }), [handleNoteClick])

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-1 shrink-0">
        {title && (
          <span className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ {title} ]</span>
        )}
        <div className="flex items-center gap-x-2 text-[9px] select-none">
          <button
            onClick={() => setTab("content")}
            className={`cursor-pointer transition-colors ${tab === "content" ? "text-[#94a3b8]" : "text-[#444] hover:text-[#777]"}`}
          >
            Content
          </button>
          <span className="text-[#333]">|</span>
          <button
            onClick={() => setTab("notes")}
            className={`cursor-pointer transition-colors ${tab === "notes" ? "text-[#94a3b8]" : "text-[#444] hover:text-[#777]"}`}
          >
            Notes{noteHook.notes.length > 0 ? ` (${noteHook.notes.length})` : ""}
          </button>
        </div>
        {headerActions ? headerActions : null}
      </div>

      {tab === "content" && highlightedContent && (
        <div ref={reportRef} onMouseUp={handleMouseUp} className={contentClassName ?? "text-[#94a3b8] text-[10px] leading-relaxed prose prose-invert prose-xs max-w-none"}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkBreaks]}
            rehypePlugins={[rehypeRaw]}
            components={markComponents}
          >
            {highlightedContent}
          </ReactMarkdown>
        </div>
      )}

      {tab === "content" && !highlightedContent && (
        <div className="text-[10px] text-[#444] py-2 font-mono italic">
          No content available.
        </div>
      )}

      {tab === "notes" && (
        <NotesSection notes={noteHook.notes} onNavigate={handleNoteGoto} onDeleteNote={noteHook.removeNote} />
      )}

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
          onDeleteNote={editingNote ? noteHook.removeNote : undefined}
        />
      )}
    </div>
  )
})
