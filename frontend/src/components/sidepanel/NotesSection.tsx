import type { NoteInfo } from "../../api/client"

interface NotesSectionProps {
  notes: NoteInfo[]
  onDeleteNote?: (noteId: string) => void
  onUpdateNote?: (noteId: string, comment?: string, visibility?: "personal" | "shared") => void
  scrollToNoteRef?: React.MutableRefObject<((noteId: string) => void) | null>
}

export function NotesSection({
  notes,
  scrollToNoteRef,
}: NotesSectionProps) {
  const handleNoteClick = (noteId: string) => {
    if (scrollToNoteRef?.current) {
      scrollToNoteRef.current(noteId)
      setTimeout(() => {
        const el = document.getElementById(`note-highlight-${noteId}`)
        if (el) el.click()
      }, 100)
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
        const isShared = note.visibility === "shared"
        const label = isShared ? "SH" : "P"
        const labelColor = isShared ? "text-purple-400" : "text-yellow-400"

        return (
          <div
            key={note.id}
            onClick={() => handleNoteClick(note.id)}
            className="flex flex-col gap-0.5 py-1 px-1.5 hover:bg-[#121212]/50 cursor-pointer select-none transition-colors border border-transparent rounded-[2px]"
          >
            <div className="flex items-start gap-1 font-mono text-[10px] leading-tight">
              <span className={`${labelColor} font-bold shrink-0 w-3.5`}>{label}</span>
              <span className="text-gray-500 font-bold shrink-0">&gt;&gt;</span>
              <span className="text-gray-300 break-words flex-1 min-w-0 font-mono">
                "{note.selected_text}"
              </span>
            </div>
            {note.comment && (
              <div className="flex items-start gap-1 pl-4 font-mono text-[9px] leading-tight text-gray-500">
                <span className="shrink-0 font-bold">&gt;&gt;</span>
                <span className="break-words flex-1 min-w-0 italic font-mono">
                  {note.comment}
                </span>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
