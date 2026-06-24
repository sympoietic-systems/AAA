import { copyToClipboard } from "../../../utils/clipboard"

interface SelectionToolbarProps {
  selectedText: string
  popupCoords: { x: number; y: number }
  onDismiss: () => void
  onOpenNoteEditor: () => void
  copied: boolean
  onCopied: (v: boolean) => void
}

export function SelectionToolbar({
  selectedText,
  popupCoords,
  onDismiss,
  onOpenNoteEditor,
  copied,
  onCopied,
}: SelectionToolbarProps) {
  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-transparent cursor-default"
        onMouseDown={onDismiss}
      />
      <div
        style={{
          position: 'fixed',
          top: `${popupCoords.y}px`,
          left: `${Math.min(window.innerWidth - 180, Math.max(10, popupCoords.x))}px`,
        }}
        onMouseUp={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
        className="fixed z-50 flex items-center gap-0 bg-[#1a1a1a] border border-[#333] shadow-xl rounded-md px-1 py-1 select-none"
      >
        <button
          onClick={async () => {
            const success = await copyToClipboard(selectedText)
            if (success) {
              onCopied(true)
              setTimeout(() => {
                onDismiss()
                onCopied(false)
              }, 800)
            }
          }}
          className="text-[#888] hover:text-[#4ade80] px-2 py-0.5 text-[10px] font-mono transition-colors whitespace-nowrap"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
        <span className="text-[#333] text-[10px] px-0.5">|</span>
        <button
          onClick={() => {
            onDismiss()
            onOpenNoteEditor()
          }}
          className="text-[#888] hover:text-[#e09b67] px-2 py-0.5 text-[10px] font-mono transition-colors whitespace-nowrap"
        >
          Note
        </button>
      </div>
    </>
  )
}
