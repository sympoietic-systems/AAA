import { useEffect, useRef } from "react"
import type { ChatMessage } from "../api/client"
import { InputBar } from "./InputBar"
import { MessageBubble } from "./MessageBubble"

interface Props {
  messages: ChatMessage[]
  loading: boolean
  error: string | null
  agentName: string
  onSend: (text: string) => void
  onClearError: () => void
}

export function ChatView({ messages, loading, error, agentName, onSend, onClearError }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto">
      <header className="flex items-center gap-2 px-4 py-3 border-b border-[#222] text-sm">
        <span className="text-[#4ade80]">{'>'}</span>
        <span className="text-[#888]">{agentName}</span>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-4">
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
            <span className="animate-pulse">▋</span>
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

      <InputBar onSend={onSend} disabled={loading} />
    </div>
  )
}
