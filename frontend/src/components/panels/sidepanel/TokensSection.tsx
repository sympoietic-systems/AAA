import { useState, memo } from "react"
import { useTelemetryTokens } from "../../../hooks/useTelemetry"

interface TokensSectionProps {
  conversationId?: string
  enabled?: boolean
  messageCount?: number
}

function TokensSectionComponent({ conversationId, enabled = false }: TokensSectionProps) {
  const { tokens, tokensLoading: loading, tokensError: error } = useTelemetryTokens(conversationId || null, enabled)
  const [detailOpen, setDetailOpen] = useState(false)

  if (error && !tokens) {
    return <p className="text-[9px] text-[#ef4444] font-mono">{error}</p>
  }

  if (loading && !tokens) {
    return <p className="text-[9px] text-[#444] font-mono animate-pulse">loading...</p>
  }

  if (!tokens) {
    return <p className="text-[9px] text-[#444] font-mono">waiting for data...</p>
  }

  const { conversations, system_prompt_tokens, grand_total_tokens } = tokens

  return (
    <div className="mt-2 pt-2 font-mono">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-[8px] leading-none text-[#60a5fa]">●</span>
        <span className="text-[10px] text-[#888]">tokens</span>
        <span className="text-[9px] ml-auto text-[#60a5fa]">
          {grand_total_tokens.toLocaleString()} total
        </span>
      </div>

      <div className="text-[9px] text-[#666] mb-1">
        system: {system_prompt_tokens.toLocaleString()}
      </div>

      {conversations.length === 0 && (
        <p className="text-[9px] text-[#555]">no messages in active conversation</p>
      )}

      {conversations.slice(0, detailOpen ? undefined : 3).map((c) => (
        <div key={c.conversation_id} className="py-1 border-b border-[#1a1a1a] last:border-b-0">
          <div className="flex items-center gap-1">
            <span className="text-[9px] text-[#aaa] truncate flex-1">
              {c.title || c.conversation_id.slice(0, 8)}
            </span>
            <span className="text-[8px] text-[#60a5fa] font-bold">
              {c.total_tokens.toLocaleString()}
            </span>
          </div>
          <div className="flex gap-3 mt-0.5">
            <span className="text-[8px] text-[#666]">
              usr:{c.user_tokens.toLocaleString()}
            </span>
            <span className="text-[8px] text-[#666]">
              agt:{c.agent_tokens.toLocaleString()}
            </span>
            {c.thinking_tokens > 0 && (
              <span className="text-[8px] text-[#666]">
                thk:{c.thinking_tokens.toLocaleString()}
              </span>
            )}
          </div>
        </div>
      ))}

      {conversations.length > 3 && (
        <button
          onClick={() => setDetailOpen(!detailOpen)}
          className="text-[8px] text-[#555] hover:text-[#888] mt-1"
        >
          {detailOpen ? "show less" : `+${conversations.length - 3} more`}
        </button>
      )}

      <div className="text-[8px] text-[#555] mt-1.5">
        grand total: {grand_total_tokens.toLocaleString()} tok
      </div>
    </div>
  )
}

export const TokensSection = memo(TokensSectionComponent)
