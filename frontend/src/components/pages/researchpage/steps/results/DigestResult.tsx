import { memo, useMemo } from "react"
import { JsonBlock } from "../../../../UI"
import type { ResultRendererProps } from "./types"
import { sourceStatusLabel } from "./helpers"

export const DigestResult = memo(function DigestResult({ selectedResults }: ResultRendererProps) {
  const digestSummary = useMemo(() => {
    const allLearnings: string[] = []
    const allGaps: string[] = []
    const allFollowups: string[] = []
    for (const r of selectedResults) {
      let a: any = null
      try { a = r.analyzed_json ? JSON.parse(r.analyzed_json) : null } catch {}
      if (a?.learnings) allLearnings.push(...a.learnings)
      if (a?.gaps) allGaps.push(...a.gaps)
      if (a?.followups) allFollowups.push(...a.followups)
    }
    return { learnings: allLearnings, gaps: allGaps, followups: allFollowups }
  }, [selectedResults])

  if (selectedResults.length === 0) {
    return <div className="text-ui-dim italic text-[9px] border-t border-ui-border pt-2">no digested results</div>
  }

  return (
    <>
      <div className="border-t border-ui-border pt-2 space-y-2">
        <div className="text-ui-dim text-[8px] uppercase">per-source analysis ({selectedResults.length})</div>
        {selectedResults.map(r => {
          let analysis: any = null
          try { analysis = r.analyzed_json ? JSON.parse(r.analyzed_json) : null } catch {}
          const status = sourceStatusLabel(analysis)
          const hasContent = analysis?.learnings?.length > 0 || analysis?.gaps?.length > 0
          return (
            <details key={r.id} className="pl-2 border-l border-ui-border">
              <summary className="text-ui-secondary text-[9px] cursor-pointer hover:text-action-hover break-all flex items-center gap-1 transition-colors">
                <span className="truncate">{r.source_title || r.source_url?.slice(0, 80) || "—"}</span>
                <span style={{ color: status.color }} className="text-[8px] shrink-0 font-mono">({status.label})</span>
              </summary>
              {analysis?.learnings?.length > 0 && (
                <div className="mt-1">
                  <div className="text-ui-dim text-[8px] mb-0.5">learnings:</div>
                  {analysis.learnings.map((l: string, li: number) => (
                    <div key={li} className="text-ui-secondary text-[9px] pl-2 leading-relaxed">· {l}</div>
                  ))}
                </div>
              )}
              {analysis?.gaps?.length > 0 && (
                <div className="mt-1">
                  <div className="text-ui-dim text-[8px] mb-0.5">gaps:</div>
                  {analysis.gaps.map((g: string, gi: number) => (
                    <div key={gi} className="text-semantic-gold text-[9px] pl-2 leading-relaxed">◇ {g}</div>
                  ))}
                </div>
              )}
              {analysis?.followups?.length > 0 && (
                <div className="mt-1">
                  <div className="text-ui-dim text-[8px] mb-0.5">followups:</div>
                  {analysis.followups.map((f: string, fi: number) => (
                    <div key={fi} className="text-semantic-purple text-[9px] pl-2 leading-relaxed">→ {f}</div>
                  ))}
                </div>
              )}
              {analysis && (
                <details className="mt-1.5 pl-2 border-l border-ui-border">
                  <summary className="text-ui-dim text-[7.5px] cursor-pointer hover:text-ui-secondary uppercase">raw analysis payload (json)</summary>
                  <div className="mt-1 font-sans">
                    <JsonBlock data={analysis} variant="json" maxHeight="max-h-36" />
                  </div>
                </details>
              )}
              {!hasContent && <div className="text-semantic-gold text-[8px] mt-1 italic font-mono">no data extracted</div>}
            </details>
          )
        })}
      </div>

      {(digestSummary.learnings.length > 0 || digestSummary.gaps.length > 0) && (
        <div className="border-t border-ui-border pt-2 space-y-1">
          <div className="text-semantic-header text-[9px] uppercase tracking-wider mb-1">
            → combined summary ({digestSummary.learnings.length} learnings, {digestSummary.gaps.length} gaps)
          </div>
          {digestSummary.learnings.length > 0 && (
            <details open>
              <summary className="text-semantic-green text-[9px] cursor-pointer hover:text-semantic-green/80 transition-colors">
                all learnings ({digestSummary.learnings.length})
              </summary>
              <div className="mt-1 space-y-0.5 max-h-48 overflow-y-auto">
                {digestSummary.learnings.map((l, i) => (
                  <div key={i} className="text-ui-secondary text-[9px] pl-2 leading-relaxed border-l border-ui-border/50">
                    {i + 1}. {l}
                  </div>
                ))}
              </div>
            </details>
          )}
          {digestSummary.gaps.length > 0 && (
            <details>
              <summary className="text-semantic-gold text-[9px] cursor-pointer hover:text-semantic-gold/80 transition-colors">
                all gaps ({digestSummary.gaps.length})
              </summary>
              <div className="mt-1 space-y-0.5 max-h-32 overflow-y-auto">
                {digestSummary.gaps.map((g, i) => (
                  <div key={i} className="text-ui-secondary text-[9px] pl-2 leading-relaxed">◇ {g}</div>
                ))}
              </div>
            </details>
          )}
          {digestSummary.followups.length > 0 && (
            <details>
              <summary className="text-semantic-purple text-[9px] cursor-pointer hover:text-semantic-purple/80 transition-colors">
                all followups ({digestSummary.followups.length})
              </summary>
              <div className="mt-1 space-y-0.5 max-h-32 overflow-y-auto">
                {digestSummary.followups.map((f, i) => (
                  <div key={i} className="text-semantic-purple text-[9px] pl-2 leading-relaxed font-mono">→ {f}</div>
                ))}
              </div>
            </details>
          )}
        </div>
      )}

      <details className="border-t border-ui-border pt-2">
        <summary className="text-semantic-header text-[9px] uppercase tracking-wider cursor-pointer hover:text-ui-secondary mb-1">
          [+] view raw digested results ({selectedResults.length} sources)
        </summary>
        <div className="mt-2 font-sans">
          <JsonBlock data={selectedResults.map(r => {
            let analysis: any = null
            try { analysis = r.analyzed_json ? JSON.parse(r.analyzed_json) : r.analyzed_json } catch {}
            return { title: r.source_title, url: r.source_url, analysis }
          })} variant="json" maxHeight="max-h-64" />
        </div>
      </details>
    </>
  )
})
