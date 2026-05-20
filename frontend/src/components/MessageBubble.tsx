import { useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import type { ChatMessage } from "../api/client"

export function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isHuman = msg.speaker === "human"
  const [thinkingOpen, setThinkingOpen] = useState(false)

  return (
    <div className={`mb-3 ${isHuman ? "" : "pl-4"}`}>
      <div className={`text-sm leading-relaxed ${isHuman ? "text-[#777]" : "text-[#c8c8c8]"}`}>
        {isHuman ? (
          <span>
            <span className="text-[#555] select-none">&gt; </span>
            {msg.content}
          </span>
        ) : (
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {msg.content}
            </ReactMarkdown>
          </div>
        )}
      </div>

      {msg.thinking && (
        <div className="mt-1">
          <button
            onClick={() => setThinkingOpen(!thinkingOpen)}
            className="text-[10px] text-[#555] hover:text-[#888] transition-colors flex items-center gap-1"
          >
            <span>{thinkingOpen ? "▼" : "▶"}</span>
            <span>thinking</span>
          </button>
          {thinkingOpen && (
            <div className="mt-1 pl-3 border-l border-[#2a2a2a] text-xs text-[#666] leading-relaxed whitespace-pre-wrap">
              {msg.thinking}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
