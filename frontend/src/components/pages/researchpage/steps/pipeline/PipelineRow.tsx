import { memo } from "react"

interface PipelineRowProps {
  label: string
  stepId?: string | null
  isDone: boolean
  isCurrent: boolean
  isStale: boolean
  isSelected: boolean
  rationale?: string | null
  onSelect: (id: string | null) => void
  onDoStep: () => void
  stepping: boolean
}

export const PipelineRow = memo(function PipelineRow({
  label, stepId, isDone, isCurrent, isStale, isSelected, rationale, onSelect, onDoStep, stepping,
}: PipelineRowProps) {
  const sc = isStale ? "var(--color-semantic-sand)" : isDone ? "var(--color-semantic-green)" : isCurrent ? "var(--color-semantic-gold)" : "var(--color-ui-dim)"
  const canClick = (isDone || isStale) ? !!stepId : isCurrent

  const handleClick = () => {
    if (!canClick) return
    if (isSelected) {
      onSelect(null)
    } else if (stepId) {
      onSelect(stepId)
    } else {
      onSelect(null)
    }
  }

  const edge = isSelected
    ? "border-l-2 border-action-hover bg-action-hover/5"
    : isCurrent
    ? "border-l-2 border-semantic-gold bg-action-hover/5"
    : isStale
    ? "border-l-2 border-semantic-sand bg-action-hover/5"
    : "border-l-2 border-transparent"

  return (
    <div className="space-y-0.5">
      <div
        onClick={handleClick}
        className={`flex items-center gap-2 text-[10px] px-2 py-1 transition-colors ${edge} ${canClick ? "cursor-pointer hover:bg-[#111]" : ""}`}
      >
        <span style={{ color: sc }} className="text-[8px] shrink-0 w-3 font-mono">
          {isStale ? "⟳" : isDone ? "✔" : isCurrent ? "▶" : "○"}
        </span>
        <span className={`font-mono flex-1 ${isSelected ? "text-action-hover" : isStale ? "text-semantic-sand/80" : isDone ? "text-ui-secondary" : isCurrent ? "text-semantic-gold" : "text-ui-dim"}`}>
          {label}{isStale ? " (stale)" : ""}
        </span>
        {isCurrent && (
          <button onClick={e => { e.stopPropagation(); onDoStep() }} disabled={stepping}
            className="text-action-dim hover:text-action-hover text-[9px] font-mono disabled:text-[#333] cursor-pointer transition-colors">
            [{stepping ? "…" : "▶ run"}]
          </button>
        )}
      </div>
      {rationale && (
        <div className="text-[8.5px] text-ui-dim/80 italic pl-5 pb-0.5 font-mono leading-tight whitespace-pre-wrap">
          ↳ {rationale}
        </div>
      )}
    </div>
  )
})
