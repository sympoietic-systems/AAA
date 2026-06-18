import { useState, useEffect, memo } from "react"
import { CollapsibleSection } from "./shared/CollapsibleSection"

interface RefusalInfo {
  id: string
  target_premise: string
  incompatibility_claim: string
  proposed_alternative: string
  conversation_id: string | null
  message_id: number | null
  created_at: string | null
}

interface RefusalsResponse {
  refusals: RefusalInfo[]
  total: number
  error?: string
}

function RefusalsSectionComponent() {
  const [data, setData] = useState<RefusalsResponse | null>(null)

  useEffect(() => {
    fetch("/api/refusals")
      .then(r => r.json())
      .then(setData)
      .catch(() => {})
  }, [])

  if (!data) return null
  if (data.error) return null

  const { refusals, total } = data
  if (refusals.length === 0) return null

  const formatTime = (ts: string | null) => {
    if (!ts) return ""
    const d = new Date(ts)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const mins = Math.floor(diffMs / 60000)
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
  }

  return (
    <CollapsibleSection
      label="Structural Refusals"
      count={refusals.length}
      icon="⊘"
      iconColor="#ef4444"
    >
      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
        {refusals.map(r => (
          <div
            key={r.id}
            className="border-l-2 border-[#ef4444]/30 pl-2 py-1 text-[11px] font-mono"
          >
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className="text-[#ef4444] text-[11px]">⊘</span>
              <span className="text-[#999] text-[9px]">{formatTime(r.created_at)}</span>
            </div>
            <div className="text-[#ef4444]/70 text-[10px] uppercase mb-1">premise challenged</div>
            <div className="text-[#ccc] mb-1">"{r.target_premise}"</div>
            <div className="text-[#ef4444]/70 text-[10px] uppercase mb-1">incompatibility</div>
            <div className="text-[#aaa] mb-1">{r.incompatibility_claim}</div>
            {r.proposed_alternative && (
              <>
                <div className="text-[#4ade80]/70 text-[10px] uppercase mb-1">alternative proposed</div>
                <div className="text-[#999]">{r.proposed_alternative}</div>
              </>
            )}
            {r.message_id && (
              <a
                href={`?m=${r.message_id}`}
                className="text-[#555] hover:text-[#888] text-[9px] cursor-pointer"
              >
                [jump to message]
              </a>
            )}
          </div>
        ))}
      </div>
      {refusals.length < total && (
        <div className="text-[10px] text-[#555] font-mono mt-1">
          ... {total - refusals.length} more
        </div>
      )}
    </CollapsibleSection>
  )
}

export const RefusalsSection = memo(RefusalsSectionComponent)
