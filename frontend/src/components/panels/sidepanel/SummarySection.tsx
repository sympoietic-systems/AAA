import { memo } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"

interface SummarySectionProps {
  summary?: string
  humanSummary?: string
}

function SummarySectionComponent({ summary, humanSummary }: SummarySectionProps) {
  if (!summary && !humanSummary) {
    return (
      <div className="text-[10px] text-ui-dim py-2 font-mono italic">
        No summary checkpoint yet — sedimentation occurs after sufficient dialogue.
      </div>
    )
  }

  const display = humanSummary || summary || ""
  const label = humanSummary ? "Sedimentation Summary" : "Autopoietic Summary Checkpoint"

  return (
    <div className="mt-1.5 pt-1.5 text-[10px] text-ui-secondary font-mono leading-relaxed markdown-body max-h-64 overflow-y-auto">
      <div className="text-[8px] text-ui-dim mb-1 uppercase tracking-wider select-none font-bold">
        {label}
      </div>
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
        {display}
      </ReactMarkdown>
    </div>
  )
}

export const SummarySection = memo(SummarySectionComponent)
