import { memo } from "react"
import { JsonBlock } from "../../../../UI"
import type { ResultRendererProps } from "./types"
import { repairTruncatedJson } from "./helpers"

export const LlmMetaLog = memo(function LlmMetaLog({ responseEntries }: ResultRendererProps) {
  if (responseEntries.length === 0) return null
  return (
    <div className="border-t border-ui-border pt-2 font-mono">
      <div className="text-ui-dim text-[9px] mb-1">llm responses ({responseEntries.length}):</div>
      {responseEntries.map((entry, ei) => {
        const d = entry.event_data as any
        const rawStr = d?.raw_response || d?.raw || d?.response || ""
        if (!rawStr || rawStr === "{}") return null
        let resp: any = null
        if (typeof rawStr === "object" && rawStr !== null) {
          resp = rawStr
        } else {
          try {
            resp = JSON.parse(rawStr)
          } catch {
            try {
              resp = JSON.parse(repairTruncatedJson(rawStr))
            } catch {}
          }
        }

        if (!resp || typeof resp !== "object") {
          const displayData = typeof rawStr === "string" ? rawStr : JSON.stringify(rawStr, null, 2)
          let parsedJson = null
          try {
            let cleaned = displayData.trim()
            if (cleaned.includes("```json")) {
              const match = cleaned.match(/```json\s*([\s\S]*?)\s*```/)
              if (match) cleaned = match[1].trim()
            } else if (cleaned.includes("```")) {
              const match = cleaned.match(/```\s*([\s\S]*?)\s*```/)
              if (match) cleaned = match[1].trim()
            }
            try {
              parsedJson = JSON.parse(cleaned)
            } catch {
              parsedJson = JSON.parse(repairTruncatedJson(cleaned))
            }
          } catch {}
          return (
            <details key={ei} className="mb-1">
              <summary className="text-ui-dim text-[9px] cursor-pointer hover:text-ui-secondary">
                {entry.event_type.replace("orchestrator_", "").replace("_response", "")} ({entry.created_at?.slice(11, 19)})
              </summary>
              <div className="mt-1">
                <JsonBlock data={parsedJson || displayData.slice(0, 4000)} variant={parsedJson ? "json" : "raw"} />
              </div>
            </details>
          )
        }

        let jsonData = resp.json_data || resp.content
        if (typeof jsonData === "string") {
          let cleaned = jsonData.trim()
          if (cleaned.includes("```json")) {
            const match = cleaned.match(/```json\s*([\s\S]*?)\s*```/)
            if (match) cleaned = match[1].trim()
          } else if (cleaned.includes("```")) {
            const match = cleaned.match(/```\s*([\s\S]*?)\s*```/)
            if (match) cleaned = match[1].trim()
          }
          try {
            jsonData = JSON.parse(cleaned)
          } catch {
            try {
              jsonData = JSON.parse(repairTruncatedJson(cleaned))
            } catch {}
          }
        }
        const thinking = resp.thinking || ""
        const wrapper = { model: resp.model, provider_used: resp.provider_used, truncated: resp.truncated, finish_reason: resp.finish_reason }

        return (
          <details key={ei} className="mb-2" open>
            <summary className="text-ui-dim text-[9px] cursor-pointer hover:text-ui-secondary transition-colors">
              {entry.event_type.replace("orchestrator_", "").replace("_response", "")} ({entry.created_at?.slice(11, 19)}) {resp.model && <span className="text-ui-dim">— {resp.model}</span>} {resp.truncated && <span className="text-semantic-gold text-[8px] font-mono">[truncated]</span>}
            </summary>
            {jsonData && (
              <div className="mt-2 font-sans">
                <div className="text-ui-dim text-[7px] mb-0.5 uppercase font-mono">output:</div>
                <JsonBlock data={jsonData} />
              </div>
            )}
            {thinking && (
              <details className="mt-1">
                <summary className="text-ui-dim text-[7px] cursor-pointer hover:text-ui-secondary uppercase transition-colors">thinking trace ({thinking.length} chars)</summary>
                <JsonBlock data={thinking} variant="dim" maxHeight="max-h-48" className="mt-1" />
              </details>
            )}
            <details className="mt-1">
              <summary className="text-ui-dim text-[7px] cursor-pointer hover:text-ui-secondary uppercase transition-colors">raw wrapper</summary>
              <div className="mt-1">
                <JsonBlock data={wrapper} variant="dim" maxHeight="max-h-24" />
              </div>
            </details>
          </details>
        )
      })}
    </div>
  )
})
