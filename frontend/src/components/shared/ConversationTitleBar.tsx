import { useState, useEffect } from "react"
import { HeaderActionButton } from "../UI"

interface ConversationTitleBarProps {
  title: string
  onRename: (title: string) => void
  onGenerateTitle: () => void
  variant?: "desktop" | "mobile"
  conversationId?: string
  onExport?: () => void
}

export function ConversationTitleBar({
  title,
  onRename,
  onGenerateTitle,
  variant = "desktop",
  conversationId,
  onExport,
}: ConversationTitleBarProps) {
  const [editing, setEditing] = useState(false)
  const [titleVal, setTitleVal] = useState(title)

  useEffect(() => {
    setTitleVal(title)
  }, [title])

  const isMobile = variant === "mobile"
  const generateLabel = isMobile ? "#gen" : "#generate_title"
  const displayTitle = title || "Untitled Entanglement"

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    setEditing(false)
    if (titleVal.trim() && titleVal !== title) {
      onRename(titleVal)
    }
  }

  const editForm = (
    <form onSubmit={handleSubmit} className={isMobile ? "w-full" : "inline-block"}>
      <input
        type="text"
        value={titleVal}
        onChange={(e) => setTitleVal(e.target.value)}
        onBlur={() => handleSubmit()}
        className={`bg-transparent border-b border-[#222]/40 px-1 py-0.5 text-xs text-[#ddd] font-mono outline-none focus:border-action-hover/50 ${isMobile ? "w-full" : "w-32 sm:w-48 md:w-64"}`}
        autoFocus
      />
    </form>
  )

  const displayView = (
    <div className={`flex items-center gap-2 ${isMobile ? "min-w-0" : ""}`}>
      {isMobile && <span className="text-[#444]">title:</span>}
      <h1
        onClick={() => setEditing(true)}
        className={`text-xs font-mono font-bold tracking-wider text-semantic-header hover:text-[#aaa] cursor-pointer truncate uppercase ${isMobile ? "flex-1" : "max-w-[120px] md:max-w-xs"}`}
        title={displayTitle}
      >
        {displayTitle}
      </h1>
      <HeaderActionButton
        onClick={onGenerateTitle}
        title="Auto-generate title"
        className={isMobile ? "shrink-0" : undefined}
      >
        {generateLabel}
      </HeaderActionButton>
    </div>
  )

  const titleArea = editing ? editForm : displayView

  if (isMobile) {
    return (
      <div className="sm:hidden flex items-center justify-between px-4 py-2 border-b border-[#1a1a1a] shrink-0 font-mono text-[11px] bg-[#0d0d0d]">
        <div className="min-w-0 flex-1">
          {titleArea}
        </div>
        {conversationId && onExport && (
          <HeaderActionButton
            onClick={onExport}
            title="Export conversation as Markdown"
            className="shrink-0 ml-2"
          >
            #export
          </HeaderActionButton>
        )}
      </div>
    )
  }

  return (
    <div className="min-w-0 flex-1 sm:flex-initial hidden sm:block">
      {titleArea}
    </div>
  )
}
