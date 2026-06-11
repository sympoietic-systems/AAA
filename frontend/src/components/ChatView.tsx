import { useEffect, useRef, useState } from "react"
import type { ConversationFile, ChatMessage, NoteInfo, ConversationTagInfo } from "../api/client"
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
  onRegenerate?: (userMsgId?: number) => void
  onRenameTitle: (title: string) => void
  onGenerateTitle: () => void
  className?: string
  // Pagination props
  hasMore?: boolean
  loadingMore?: boolean
  onLoadMore?: () => void
  notes?: NoteInfo[]
  isPassword?: boolean
  onAddNote?: (messageId: number, selectedText: string, comment: string, visibility: "personal" | "shared" | "agent", startOffset?: number) => void
  onDeleteNote?: (noteId: string) => void
  onUpdateNote?: (noteId: string, comment?: string, visibility?: "personal" | "shared" | "agent") => void
  tags?: ConversationTagInfo[]
  onAddTag?: (tag: string) => void
  onRemoveTag?: (tag: string) => void
  onBranch?: (messageId: number) => void
  fullTreeMessages?: ChatMessage[]
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
  onRegenerate,
  onRenameTitle,
  onGenerateTitle,
  className = "",
  hasMore = false,
  loadingMore = false,
  onLoadMore,
  isPassword = false,
  notes = [],
  onAddNote,
  onDeleteNote,
  onUpdateNote,
  tags = [],
  onAddTag,
  onRemoveTag,
  onBranch,
  fullTreeMessages = [],
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const [editing, setEditing] = useState(false)
  const [editValue, setEditValue] = useState("")
  const [generating, setGenerating] = useState(false)
  const [newTagVal, setNewTagVal] = useState("")

  const handleAddTagSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = newTagVal.trim().toLowerCase()
    if (trimmed && onAddTag) {
      onAddTag(trimmed)
      setNewTagVal("")
    }
  }

  const prevScrollHeightRef = useRef<number>(0)
  const prevScrollTopRef = useRef<number>(0)
  const isPrependingRef = useRef<boolean>(false)
  const prevMessagesLengthRef = useRef<number>(messages.length)
  const prevLastMessageIdRef = useRef<number | string | undefined>(
    messages.length > 0 ? messages[messages.length - 1].id : undefined
  )
  const prevConversationIdRef = useRef<string>(conversationId)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const isNewConversation = conversationId !== prevConversationIdRef.current
    prevConversationIdRef.current = conversationId

    if (isNewConversation) {
      bottomRef.current?.scrollIntoView({ behavior: "auto" })
      prevMessagesLengthRef.current = messages.length
      prevLastMessageIdRef.current = messages.length > 0 ? messages[messages.length - 1].id : undefined
      isPrependingRef.current = false
      return
    }

    if (isPrependingRef.current) {
      const newScrollHeight = container.scrollHeight
      const heightDifference = newScrollHeight - prevScrollHeightRef.current
      container.scrollTop = prevScrollTopRef.current + heightDifference
      isPrependingRef.current = false
    } else {
      const lastMsg = messages[messages.length - 1]
      const lastMsgId = lastMsg?.id
      const lengthIncreased = messages.length > prevMessagesLengthRef.current
      const lastIdChanged = lastMsgId !== prevLastMessageIdRef.current

      if (lengthIncreased || lastIdChanged) {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" })
      }
    }

    prevMessagesLengthRef.current = messages.length
    prevLastMessageIdRef.current = messages.length > 0 ? messages[messages.length - 1].id : undefined
  }, [messages, conversationId])

  const handleScroll = () => {
    const container = containerRef.current
    if (!container) return
    if (container.scrollTop > 10) return

    if (hasMore && !loadingMore && onLoadMore) {
      prevScrollHeightRef.current = container.scrollHeight
      prevScrollTopRef.current = container.scrollTop
      isPrependingRef.current = true
      onLoadMore()
    }
  }

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
        <span className="text-[#888]">{isPassword ? "authentication" : agentName}</span>
        {conversationId ? (
          <>
            <span className="text-[#444]">{">>"}</span>
            {(() => {
              const structural = tags?.find(t => t.tag_type === "structural")
              let letterColor = "text-[#6bc28c]"
              let letter = "U"
              if (structural) {
                if (structural.tag === "dreams") { letterColor = "text-[#a892ee]"; letter = "D" }
                else if (structural.tag === "other agents") { letterColor = "text-[#e09b67]"; letter = "A" }
              }
              return <span className={`text-sm ${letterColor} font-mono font-bold shrink-0`}>[{letter}]</span>
            })()}
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
                {(() => {
                  const structural = tags?.find(t => t.tag_type === "structural")
                  const title = conversationTitle || "untitled"
                  if (structural?.tag === "dreams") return title.replace(/^Dream Log:\s*/i, "")
                  return title
                })()}
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

      {conversationId && tags && (
        <div className="flex flex-wrap items-center gap-1.5 px-4 py-1.5 border-b border-[#222] bg-[#090909] shrink-0">
          <span className="text-[9px] text-[#555] uppercase font-mono tracking-wider mr-1">tags:</span>
          {tags.map((t, i) => {
            let tagStyle = "text-[#888]"
            const isDeletable = t.tag_type === "semantic"
            if (t.tag_type === "structural") {
              if (t.tag === "dreams") {
                tagStyle = "text-[#a892ee]"
              } else if (t.tag === "other agents") {
                tagStyle = "text-[#e09b67]"
              } else {
                tagStyle = "text-[#6bc28c]"
              }
            } else if (t.tag_type === "keyword") {
              tagStyle = "text-[#6fafe2]"
            } else if (t.tag_type === "diffractive") {
              tagStyle = "text-[#4ec9b0]"
            }
            return (
              <span
                key={t.tag}
                className={`text-[9px] ${tagStyle} font-mono`}
              >
                {i > 0 && <span className="text-[#444] select-none">{" // "}</span>}
                {t.tag}
                {isDeletable && onRemoveTag && (
                  <button
                    onClick={() => onRemoveTag(t.tag)}
                    className="text-[10px] text-[#888] hover:text-[#ef4444] transition-colors cursor-pointer font-bold select-none ml-0.5"
                    title="Remove tag"
                  >
                    &times;
                  </button>
                )}
              </span>
            )
          })}
          {onAddTag && (
            <form onSubmit={handleAddTagSubmit} className="flex items-center ml-1">
              <input
                type="text"
                placeholder="+ tag"
                value={newTagVal}
                onChange={(e) => setNewTagVal(e.target.value)}
                className="bg-transparent border-0 text-[9px] text-[#888] font-mono outline-none focus:text-[#aaa] w-14 focus:w-24 transition-all duration-150 placeholder:text-[#444] border-b border-transparent focus:border-[#4ade80]"
              />
            </form>
          )}
        </div>
      )}

      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-4 flex flex-col"
      >
        {isPassword ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6 select-none max-w-sm mx-auto my-auto border border-[#222] bg-[#0c0c0c] rounded-sm">
            <span className="text-2xl text-[#ef4444] mb-3 animate-pulse">⚙</span>
            <h2 className="text-[#ddd] text-xs font-mono tracking-widest mb-1.5 uppercase">SYSTEM LOCK</h2>
            <p className="text-[#555] text-[10px] font-mono leading-relaxed uppercase">
              Authentication required. Enter credentials in prompt below.
            </p>
          </div>
        ) : (
          <>
            {loadingMore && (
              <div className="flex justify-center items-center py-2 text-xs text-[#555] border-b border-[#1a1a1a] mb-4">
                <span className="animate-pulse">Loading previous messages...</span>
              </div>
            )}
            {messages.length === 0 && !loading && (
              <div className="text-[#555] text-sm mt-20">
                <p>{agentName} v0.1.0 — type a message below.</p>
              </div>
            )}
            {messages.map((msg, idx) => {
              const prevMsg = idx > 0 ? messages[idx - 1] : null
              const msgNotes = notes.filter((n) => n.message_id === msg.id)
              return (
                <MessageBubble 
                  key={msg.id} 
                  msg={msg} 
                  previousSignature={prevMsg?.structural_signature}
                  notes={msgNotes}
                  onAddNote={onAddNote}
                  onDeleteNote={onDeleteNote}
                  onUpdateNote={onUpdateNote}
                  onBranch={onBranch}
                  onRegenerate={onRegenerate}
                  fullTreeMessages={fullTreeMessages}
                />
              )
            })}
            {loading && (
              <div className="flex items-center gap-2 py-1 text-[#4ade80]">
                <span className="animate-pulse">▊</span>
              </div>
            )}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="mx-4 mb-1 flex items-center gap-2 bg-[#1a1010] border border-[#3a1a1a] px-4 py-2 text-sm text-[#ef4444]">
          <span className="flex-1 truncate">{error}</span>
          {onRegenerate && (
            <button
              onClick={() => onRegenerate()}
              className="text-[#4ade80] hover:text-[#22c55e] border border-[#276a3e]/50 px-2.5 py-0.5 rounded-sm text-xs tracking-wider font-mono mr-2 bg-[#0d1c12] hover:bg-[#122b1c] transition-colors"
            >
              retry
            </button>
          )}
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
        isPassword={isPassword}
      />
    </div>
  )
}
