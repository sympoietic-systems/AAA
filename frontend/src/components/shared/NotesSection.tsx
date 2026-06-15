import { useState, memo } from "react"
import type { NoteInfo } from "../../api/client"

interface NotesSectionProps {
  notes: NoteInfo[]
  onDeleteNote?: (noteId: string) => void
  onUpdateNote?: (noteId: string, comment?: string, visibility?: "personal" | "shared" | "agent") => void
  onNavigate?: (messageId: number) => void
}

function NotesSectionComponent({
  notes,
  onDeleteNote,
  onNavigate,
}: NotesSectionProps) {
  const [scrollFailed, setScrollFailed] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)

  const handleGoToNote = (e: React.MouseEvent, note: NoteInfo) => {
    e.stopPropagation()
    if (onNavigate) {
      onNavigate(note.message_id)
      return
    }
    setScrollFailed(null)

    const primaryEl = document.getElementById(`note-highlight-${note.id}`)
    const legacyEl = !primaryEl ? document.getElementById(note.id) : null
    const segmentEl = !primaryEl && !legacyEl ? document.querySelector(`[data-note-id="${note.id}"]`) : null

    const targetEl = primaryEl || legacyEl || segmentEl

    if (targetEl) {
      const msgContainer = targetEl.closest('.markdown-body')
      const collapsedDiv = msgContainer?.querySelector('.max-h-24.overflow-y-auto')
      if (collapsedDiv) {
        const bubbleEl = msgContainer?.closest('[class*="mb-3"]')
        const expandBtn = bubbleEl?.querySelector('button') as HTMLElement | null
        if (expandBtn && expandBtn.textContent?.includes('expand')) {
          expandBtn.click()
        }
      }

      targetEl.scrollIntoView({ behavior: 'auto', block: 'center' })
    } else {
      setScrollFailed(note.id)
      setTimeout(() => setScrollFailed(null), 3000)
    }
  }

  const [searchTerm, setSearchTerm] = useState("")
  const [visibilityFilter, setVisibilityFilter] = useState<'all' | 'personal' | 'shared' | 'agent'>('all')

  if (notes.length === 0) {
    return (
      <div className="text-[10px] text-[#444] py-2 font-mono italic">
        No notes or highlights in this conversation.
        Select text in the conversation bubbles to create a note.
      </div>
    )
  }

  const filteredNotes = notes.filter((note) => {
    // 1. Visibility Filter
    if (visibilityFilter !== "all" && note.visibility !== visibilityFilter) {
      return false
    }

    // 2. Search Term Filter
    if (searchTerm.trim() !== "") {
      const term = searchTerm.toLowerCase()
      const matchesText = note.selected_text.toLowerCase().includes(term)
      const matchesComment = note.comment ? note.comment.toLowerCase().includes(term) : false
      return matchesText || matchesComment
    }

    return true
  })

  return (
    <div className="mt-1.5 pt-1.5 font-mono text-xs flex flex-col gap-1.5">
      {/* Search and Filters controls */}
      <div className="flex flex-col gap-1 pb-1.5 border-b border-[#1a1a1a]">
        <div className="relative flex items-center">
          <input
            type="text"
            placeholder="search notes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-transparent border-b border-[#222]/40 text-[#eee] pl-0 pr-6 py-1 text-[10px] focus:outline-none focus:border-[#444] transition-colors font-mono"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm("")}
              className="absolute right-1.5 text-gray-500 hover:text-gray-300 text-[10px] cursor-pointer"
              title="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[9px] select-none">
          <span className="text-[#555]">visibility:</span>
          {(['all', 'personal', 'shared', 'agent'] as const).map((v, i) => {
            const isSelected = visibilityFilter === v
            const color =
              v === 'personal' ? 'text-yellow-400' :
              v === 'shared' ? 'text-purple-400' :
              v === 'agent' ? 'text-cyan-400' : ''
            return (
              <span key={v} className="flex items-center gap-x-2">
                {i > 0 && <span className="text-[#333]">•</span>}
                <button
                  onClick={() => setVisibilityFilter(v)}
                  className={`cursor-pointer transition-colors ${isSelected ? `text-[#94a3b8] ${color || ''}`.replace(/\s+$/, '') : "text-[#444] hover:text-[#777]"}`}
                >
                  {v}
                </button>
              </span>
            )
          })}
        </div>
      </div>

      {/* Notes timeline list */}
      {filteredNotes.length === 0 ? (
        <div className="text-[10px] text-[#444] py-2 font-mono italic">
          No notes matched this query filter.
        </div>
      ) : (
        <div className="space-y-1">
          {filteredNotes.map((note) => {
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
                    onClick={(e) => handleGoToNote(e, note)}
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
      )}
    </div>
  )
}

export const NotesSection = memo(NotesSectionComponent)
