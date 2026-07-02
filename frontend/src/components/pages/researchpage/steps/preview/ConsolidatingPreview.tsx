import { memo } from "react"
import type { StepPreview } from "../../../../../api/research"
import { KeyValueGrid } from "../../../../UI"

export const ConsolidatingPreview = memo(function ConsolidatingPreview({ preview }: { preview: StepPreview }) {
  return (
    <div className="space-y-3">
      <div>
        <div className="text-ui-dim text-[9px] uppercase font-mono mb-1">consolidation details</div>
        <KeyValueGrid items={[
          { key: "findings to consolidate", value: preview.findings_count ?? 0 },
          { key: "current depth", value: preview.current_depth ?? 0 },
          { key: "max depth", value: preview.max_depth ?? 0 },
          { key: "max consolidation rounds", value: preview.max_rounds ?? 0 },
        ]} />
      </div>

      {preview.parsed_urls && preview.parsed_urls.length > 0 && (
        <div>
          <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">visited/parsed urls ({preview.parsed_urls.length})</div>
          <div className="space-y-0.5 max-h-36 overflow-y-auto pr-1 font-mono">
            {preview.parsed_urls.map((u, i) => {
              const statusColor = u.status === "ok"
                ? "var(--color-semantic-green)"
                : u.status?.startsWith("failed")
                  ? "var(--color-semantic-red)"
                  : "var(--color-semantic-gold)"
              return (
                <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed flex items-center justify-between gap-2 max-w-full">
                  <div className="truncate flex-1 min-w-0">
                    <span className="text-ui-dim">{i + 1}.</span>{" "}
                    <a href={u.url} target="_blank" rel="noopener noreferrer"
                      className="text-action-dim hover:text-action-hover underline transition-colors">
                      {u.title || u.url}
                    </a>
                  </div>
                  {u.status && (
                    <span style={{ color: statusColor }} className="text-[8px] font-mono shrink-0 select-none">
                      [{u.status}]
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {preview.accumulated_findings && preview.accumulated_findings.length > 0 && (
        <div>
          <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">accumulated findings ({preview.accumulated_findings.length})</div>
          <div className="space-y-0.5 max-h-48 overflow-y-auto pr-1 font-mono">
            {preview.accumulated_findings.map((f, i) => (
              <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                <span className="text-ui-dim">{i + 1}.</span> {f}
              </div>
            ))}
          </div>
        </div>
      )}

      {preview.digest_signals && (
        <div className="space-y-2">
          {preview.digest_signals.gaps && preview.digest_signals.gaps.length > 0 && (
            <div>
              <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">gaps to consolidate ({preview.digest_signals.gaps.length})</div>
              <div className="space-y-0.5 max-h-32 overflow-y-auto pr-1 font-mono">
                {preview.digest_signals.gaps.map((g, i) => (
                  <div key={i} className="text-semantic-gold text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                    ◇ {g}
                  </div>
                ))}
              </div>
            </div>
          )}
          {preview.digest_signals.followups && preview.digest_signals.followups.length > 0 && (
            <div>
              <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">followups ({preview.digest_signals.followups.length})</div>
              <div className="space-y-0.5 max-h-32 overflow-y-auto pr-1 font-mono">
                {preview.digest_signals.followups.map((f, i) => (
                  <div key={i} className="text-semantic-purple text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                    → {f}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
})
