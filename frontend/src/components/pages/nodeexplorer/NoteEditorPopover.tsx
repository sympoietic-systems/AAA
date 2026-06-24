import type { NoteInfo } from "../../../api/client"

interface NoteEditorPopoverProps {
  selectedText: string
  noteComment: string
  noteVisibility: "personal" | "shared" | "agent"
  editingNote: NoteInfo | null
  popupCoords: { x: number; y: number }
  onCommentChange: (v: string) => void
  onVisibilityChange: (v: "personal" | "shared" | "agent") => void
  onSave: () => void
  onDismiss: () => void
  onDeleteNote?: (noteId: string) => void
}

export function NoteEditorPopover({
  selectedText,
  noteComment,
  noteVisibility,
  editingNote,
  popupCoords,
  onCommentChange,
  onVisibilityChange,
  onSave,
  onDismiss,
  onDeleteNote,
}: NoteEditorPopoverProps) {
  const handleDismiss = () => {
    onDismiss()
  }

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-transparent cursor-default"
        onMouseDown={handleDismiss}
      />
      <div
        style={{
          position: 'fixed',
          top: `${popupCoords.y}px`,
          left: `${Math.min(window.innerWidth - 400, Math.max(10, popupCoords.x - 100))}px`,
        }}
        onMouseUp={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
        className="fixed z-50 w-[380px] p-3 bg-[#111] border border-[#333] shadow-2xl rounded-md text-xs select-none"
      >
        <div className="text-gray-400 font-mono mb-2">
          {editingNote ? "EDIT NOTE FOR SELECTION:" : "ADD NOTE FOR SELECTION:"}
        </div>
        <div className={`italic text-gray-500 bg-[#090909] p-2 rounded mb-2 border-l-2 ${noteVisibility === 'shared' ? 'border-purple-500' : 'border-yellow-500'} overflow-x-auto whitespace-pre-wrap max-h-20 font-mono`}>
          "{selectedText}"
        </div>
        <textarea
          value={noteComment}
          onChange={(e) => onCommentChange(e.target.value)}
          placeholder="Add comment..."
          className="w-full bg-[#1a1a1a] border border-[#333] p-2 rounded text-[#ccc] placeholder-[#555] focus:outline-none focus:border-[#4ade80] resize-none h-16 mb-2"
          autoFocus
        />
        <div className="flex items-center justify-between">
          <div className="flex gap-2">
            <button
              onClick={() => onVisibilityChange("personal")}
              className={`px-2 py-1 rounded text-[10px] transition-colors ${
                noteVisibility === "personal"
                  ? "bg-[#333] text-white border border-[#555]"
                  : "bg-transparent text-[#555] border border-transparent hover:text-gray-300"
              }`}
            >
              Personal
            </button>
            <button
              onClick={() => onVisibilityChange("shared")}
              className={`px-2 py-1 rounded text-[10px] transition-colors ${
                noteVisibility === "shared"
                  ? "bg-purple-950 text-purple-200 border border-purple-800"
                  : "bg-transparent text-[#555] border border-transparent hover:text-purple-400"
              }`}
            >
              Shared
            </button>
          </div>
          <div className="flex gap-2">
            {editingNote && onDeleteNote && (
              <button
                onClick={() => {
                  onDeleteNote(editingNote.id)
                  handleDismiss()
                }}
                className="text-[#ef4444] hover:text-red-400 hover:underline px-2 py-1 mr-2 text-[10px]"
              >
                Delete
              </button>
            )}
            <button
              onClick={handleDismiss}
              className="text-gray-500 hover:text-gray-300 px-2 py-1"
            >
              Cancel
            </button>
            <button
              onClick={onSave}
              className="bg-green-800 hover:bg-green-700 text-green-100 px-3 py-1 rounded font-mono text-[10px]"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
