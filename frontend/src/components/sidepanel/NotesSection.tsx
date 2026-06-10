import { useState } from "react"
import type { NoteInfo } from "../../api/client"

interface NotesSectionProps {
  notes: NoteInfo[]
  onDeleteNote?: (noteId: string) => void
  onUpdateNote?: (noteId: string, comment?: string, visibility?: "personal" | "shared" | "agent") => void
}

export function NotesSection({
  notes,
  onDeleteNote,
}: NotesSectionProps) {
  const [scrollFailed, setScrollFailed] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)

  const handleGoToNote = (e: React.MouseEvent, noteId: string) => {
    e.stopPropagation()
    setScrollFailed(null)

    // Find the highlight element in the chat
    // Support both: id="note-highlight-{noteId}" (primary) and data-note-id="{noteId}" (all segments)
    const primaryEl = document.getElementById(`note-highlight-${noteId}`)
    // Also check legacy format: id="{noteId}" directly
    const legacyEl = !primaryEl ? document.getElementById(noteId) : null
    // Check data-note-id segments as fallback
    const segmentEl = !primaryEl && !legacyEl ? document.querySelector(`[data-note-id="${noteId}"]`) : null

    const targetEl = primaryEl || legacyEl || segmentEl

    if (targetEl) {
      // Check if the message is a collapsed user message — if so, expand it first
      const msgContainer = targetEl.closest('.markdown-body')
      const collapsedDiv = msgContainer?.querySelector('.max-h-24.overflow-y-auto')
      if (collapsedDiv) {
        // Find the expand button and click it
        const bubbleEl = msgContainer?.closest('[class*="mb-3"]')
        const expandBtn = bubbleEl?.querySelector('button') as HTMLElement | null
        if (expandBtn && expandBtn.textContent?.includes('expand')) {
          expandBtn.click()
        }
      }

      targetEl.scrollIntoView({ behavior: 'auto', block: 'center' })
    } else {
      // Note highlight not found — the message might not be loaded (paginated out)
      setScrollFailed(noteId)
      setTimeout(() => setScrollFailed(null), 3000)
    }
  }

  if (notes.length === 0) {
    return (
      <div className="text-[10px] text-[#444] py-2 font-mono italic">
        No notes or highlights in this conversation.
        Select text in the conversation bubbles to create a note.
      </div>
    )
  }

  return (
    <div className="mt-1.5 pt-1.5 space-y-1 font-mono text-xs">
      {notes.map((note) => {
        const isAgent = note.visibility === "agent"
        const isShared = note.visibility === "shared"
        const label = isAgent ? "A" : isShared ? "SH" : "P"
        const labelColor = isAgent ? "text-cyan-400" : isShared ? "text-purple-400" : "text-yellow-400"
        const isFailed = scrollFailed === note.id

        return (
          <div
            key={note.id}
            className="flex flex-col gap-0.5 py-1 px-1.5 hover:bg-[#121212]/50 transition-colors border border-transparent rounded-[2px] group/note"
          >
            <div className="flex items-start gap-1 font-mono text-[10px] leading-tight">
              <span className={`${labelColor} font-bold shrink-0 w-3.5`}>{label}</span>
              <span className="text-gray-500 font-bold shrink-0">&gt;&gt;</span>
              <span className="text-gray-300 break-words flex-1 min-w-0 font-mono select-text">
                "{note.selected_text}"
              </span>
              <button
                onClick={(e) => handleGoToNote(e, note.id)}
                className="shrink-0 text-[#555] hover:text-[#4ade80] transition-colors opacity-0 group-hover/note:opacity-100 ml-0.5"
                title="Go to note in conversation"
              >
                ↗
              </button>
              {onDeleteNote && (
                confirmDeleteId === note.id ? (
                  <span className="shrink-0 flex items-center gap-1 ml-0.5">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onDeleteNote(note.id)
                        setConfirmDeleteId(null)
                      }}
                      className="text-[#ef4444] hover:text-red-400 text-[9px]"
                      title="Confirm delete"
                    >
                      ✓
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setConfirmDeleteId(null)
                      }}
                      className="text-[#555] hover:text-gray-300 text-[9px]"
                      title="Cancel"
                    >
                      ✕
                    </button>
                  </span>
                ) : (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setConfirmDeleteId(note.id)
                    }}
                    className="shrink-0 text-[#555] hover:text-[#ef4444] transition-colors opacity-0 group-hover/note:opacity-100 ml-0.5"
                    title="Delete note"
                  >
                    ✕
                  </button>
                )
              )}
            </div>
            {note.comment && (
              <div className="flex items-start gap-1 pl-4 font-mono text-[9px] leading-tight text-gray-500">
                <span className="shrink-0 font-bold">&gt;&gt;</span>
                <span className="break-words flex-1 min-w-0 italic font-mono select-text">
                  {note.comment}
                </span>
              </div>
            )}
            {isFailed && (
              <div className="pl-4 text-[9px] text-yellow-600 italic">
                Message not loaded — scroll up to load older messages first
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
