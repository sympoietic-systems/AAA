import { memo } from "react"
import { NotableMarkdown } from "../../../../shared/NotableMarkdown"
import type { ResultRendererProps } from "./types"

export const SynthesizeResult = memo(function SynthesizeResult({ selected, parsedResult }: ResultRendererProps) {
  if (!parsedResult.answer) return null
  return (
    <div className="border-t border-ui-border pt-2 space-y-1.5 font-sans">
      <NotableMarkdown
        assetType="research_step"
        assetId={selected.id}
        content={parsedResult.answer}
        title={`synthesis report${parsedResult.confidence > 0 ? ` (confidence: ${Math.round(parsedResult.confidence * 100)}%)` : ""}`}
        contentClassName="text-ui-secondary text-[10px] leading-relaxed prose prose-invert prose-xs max-w-none max-h-[500px] overflow-y-auto"
      />
    </div>
  )
})
