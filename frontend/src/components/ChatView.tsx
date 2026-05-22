import { useEffect, useRef, useState } from "react"
import type { ConversationFile, ChatMessage } from "../api/client"
import { InputBar } from "./InputBar"
import { MessageBubble } from "./MessageBubble"

interface Props {
  messages: ChatMessage[]
  loading: boolean
  error: string | null
  agentName: string
  conversationId: string
  conversationTitle: string
  uploadedFiles: ConversationFile[]
  onSend: (text: string) => void
  onUploadFiles: (files: File[]) => void
  isIndexing: boolean
  onClearError: () => void
  onRenameTitle: (title: string) => void
  onGenerateTitle: () => void
  className?: string
}

export function ChatView({
  messages,
  loading,
  error,
  agentName,
  conversationId,
  conversationTitle,
  uploadedFiles,
  onSend,
  onUploadFiles,
  isIndexing,
  onClearError,
  onRenameTitle,
  onGenerateTitle,
  className = "",
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const [editing, setEditing] = useState(false)
  const [editValue, setEditValue] = useState("")
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const startEdit = () => {
    setEditValue(conversationTitle || "")
    setEditing(true)
  }

  const saveEdit = () => {
    const trimmed = editValue.trim()
    if (trimmed && trimmed !== conversationTitle) {
      onRenameTitle(trimmed)
    }
    setEditing(false)
  }

  const handleGenerate = async () => {
    setGenerating(true)
    await onGenerateTitle()
    setGenerating(false)
  }

  return (
    <div className={`flex flex-col h-full max-w-5xl mx-auto w-full ${className}`}>
      <header className="flex items-center gap-1.5 px-4 py-3 border-b border-[#222] text-sm">
        <span className="text-[#4ade80]">{'>'}</span>
        <span className="text-[#888]">{agentName}</span>
        {conversationId ? (
          <>
            <span className="text-[#444]">{'>'}</span>
            {editing ? (
              <input
                className="flex-1 text-[#aaa] bg-[#1a1a1a] border border-[#333] px-1.5 py-0.5 text-sm outline-none focus:border-[#4ade80] min-w-0 max-w-md"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onBlur={saveEdit}
                onKeyDown={(e) => {
                  if (e.key === "Enter") saveEdit()
                  if (e.key === "Escape") setEditing(false)
                }}
                autoFocus
              />
            ) : (
              <span className="text-[#aaa] truncate flex-1 min-w-0">
                {conversationTitle || "untitled"}
              </span>
            )}
            <div className="ml-auto flex items-center gap-1 shrink-0">
              <button
                onClick={startEdit}
                className="text-[#555] hover:text-[#888] text-xs transition-colors px-1"
              >
                #RN
              </button>
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="text-[#555] hover:text-[#4ade80] text-xs transition-colors disabled:text-[#333] px-1"
              >
                #{generating ? "..." : "GEN"}
              </button>
            </div>
          </>
        ) : (
          <>
            {uploadedFiles.length > 0 && (
              <span className="text-[#555] text-xs ml-auto shrink-0">
                {uploadedFiles.length} file{uploadedFiles.length > 1 ? "s" : ""}
              </span>
            )}
          </>
        )}
      </header>

      <div className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-4">
        {messages.length === 0 && !loading && (
          <div className="text-[#555] text-sm mt-20">
            <p>{agentName} v0.1.0 — type a message below.</p>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}
        {loading && (
          <div className="flex items-center gap-2 py-1 text-[#4ade80]">
            <span className="animate-pulse">\u258B</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="mx-4 mb-1 flex items-center gap-2 bg-[#1a1010] border border-[#3a1a1a] px-4 py-2 text-sm text-[#ef4444]">
          <span className="flex-1 truncate">{error}</span>
          <button onClick={onClearError} className="text-[#884444] hover:text-[#ef4444]">
            dismiss
          </button>
        </div>
      )}

      <InputBar
        onSend={onSend}
        onUploadFiles={onUploadFiles}
        disabled={loading}
        isIndexing={isIndexing}
      />
    </div>
  )
}
