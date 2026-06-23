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
    return <p className="text-[9px] text-semantic-red font-mono">{error}</p>
  }

  if (loading && !tokens) {
    return <p className="text-[9px] text-ui-dim font-mono animate-pulse">loading...</p>
  }

  if (!tokens) {
    return <p className="text-[9px] text-ui-dim font-mono">waiting for data...</p>
  }

  const { conversations, system_prompt_tokens, grand_total_tokens } = tokens

  return (
    <div className="mt-2 pt-2 font-mono">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-[8px] leading-none text-semantic-blue">●</span>
        <span className="text-[10px] text-ui-secondary">tokens</span>
        <span className="text-[9px] ml-auto text-semantic-blue">
          {grand_total_tokens.toLocaleString()} total
        </span>
      </div>

      <div className="text-[9px] text-ui-dim mb-1">
        system: {system_prompt_tokens.toLocaleString()}
      </div>

      {conversations.length === 0 && (
        <p className="text-[9px] text-ui-dim">no messages in active conversation</p>
      )}

      {conversations.slice(0, detailOpen ? undefined : 3).map((c) => (
        <div key={c.conversation_id} className="py-1 border-b border-ui-border last:border-b-0">
          <div className="flex items-center gap-1">
            <span className="text-[9px] text-ui-secondary truncate flex-1">
              {c.title || c.conversation_id.slice(0, 8)}
            </span>
            <span className="text-[8px] text-semantic-blue font-bold">
              {c.total_tokens.toLocaleString()}
            </span>
          </div>
          <div className="flex gap-3 mt-0.5">
            <span className="text-[8px] text-ui-dim">
              usr:{c.user_tokens.toLocaleString()}
            </span>
            <span className="text-[8px] text-ui-dim">
              agt:{c.agent_tokens.toLocaleString()}
            </span>
            {c.thinking_tokens > 0 && (
              <span className="text-[8px] text-ui-dim">
                thk:{c.thinking_tokens.toLocaleString()}
              </span>
            )}
          </div>
        </div>
      ))}

      {conversations.length > 3 && (
        <button
          onClick={() => setDetailOpen(!detailOpen)}
          className="text-[8px] text-ui-dim hover:text-action-hover mt-1"
        >
          {detailOpen ? "show less" : `+${conversations.length - 3} more`}
        </button>
      )}

      <div className="text-[8px] text-ui-dim mt-1.5">
        grand total: {grand_total_tokens.toLocaleString()} tok
      </div>
    </div>
  )
}

export const TokensSection = memo(TokensSectionComponent)
