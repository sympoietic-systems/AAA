import { memo } from "react"
import type { StepPreview } from "../../../../../api/research"
import { KeyValueGrid } from "../../../../UI"

export const SynthesizingPreview = memo(function SynthesizingPreview({ preview }: { preview: StepPreview }) {
  return (
    <div className="space-y-3 font-mono">
      <div>
        <div className="text-ui-dim text-[9px] uppercase font-mono mb-1">synthesis context</div>
        <KeyValueGrid items={[
          { key: "accumulated findings", value: preview.findings_count ?? 0 },
          { key: "sources analyzed", value: preview.sources_count ?? 0 },
        ]} />
      </div>

      {preview.sources && preview.sources.length > 0 && (
        <details>
          <summary className="text-semantic-green text-[9px] cursor-pointer hover:text-semantic-green/80 font-mono transition-colors">
            sources consulted ({preview.sources.length})
          </summary>
          <div className="mt-1 space-y-0.5 max-h-36 overflow-y-auto pr-1">
            {preview.sources.map((u, i) => (
              <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed flex items-center justify-between gap-2 max-w-full">
                <div className="truncate flex-1 min-w-0">
                  <span className="text-ui-dim">{i + 1}.</span>{" "}
                  <a href={u.url} target="_blank" rel="noopener noreferrer"
                    className="text-action-dim hover:text-action-hover underline transition-colors">
                    {u.title || u.url}
                  </a>
                </div>
              </div>
            ))}
          </div>
        </details>
      )}

      {preview.findings && preview.findings.length > 0 && (
        <details open>
          <summary className="text-ui-secondary text-[9px] cursor-pointer hover:text-ui-primary font-mono transition-colors">
            accumulated findings ({preview.findings.length})
          </summary>
          <div className="mt-1 space-y-0.5 max-h-48 overflow-y-auto pr-1">
            {preview.findings.map((f, i) => (
              <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                <span className="text-ui-dim">{i + 1}.</span> {f}
              </div>
            ))}
          </div>
        </details>
      )}

      {preview.reflection && (
        <>
          {preview.reflection.key_insights && preview.reflection.key_insights.length > 0 && (
            <details>
              <summary className="text-semantic-green text-[9px] cursor-pointer hover:text-semantic-green/80 font-mono transition-colors">
                stabilized key insights ({preview.reflection.key_insights.length})
              </summary>
              <div className="mt-1 space-y-0.5 max-h-32 overflow-y-auto pr-1 font-mono">
                {preview.reflection.key_insights.map((ins: string, i: number) => (
                  <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">✓ {ins}</div>
                ))}
              </div>
            </details>
          )}

          {preview.reflection.remaining_gaps && preview.reflection.remaining_gaps.length > 0 && (
            <details>
              <summary className="text-semantic-gold text-[9px] cursor-pointer hover:text-semantic-gold/80 font-mono transition-colors">
                remaining gaps ({preview.reflection.remaining_gaps.length})
              </summary>
              <div className="mt-1 space-y-0.5 max-h-28 overflow-y-auto pr-1 font-mono">
                {preview.reflection.remaining_gaps.map((g: string, i: number) => (
                  <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">◇ {g}</div>
                ))}
              </div>
            </details>
          )}
        </>
      )}
    </div>
  )
})
