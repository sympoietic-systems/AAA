import { memo, useMemo } from "react"
import type { ResearchStep, ResearchStepResult } from "../../../../api/research"
import { JsonBlock } from "../../../UI"
import { NotableMarkdown } from "../../../shared/NotableMarkdown"
import { NotableContent } from "../../../shared/NotableContent"
import type { NotableContentHooks } from "../../../shared/NotableContent"

interface StepResultTabProps {
  selected: ResearchStep
  selectedResults: ResearchStepResult[]
  parsedResult: {
    queries: string[]
    goal: string
    completeness: number
    answer: string
    confidence: number
    learnings: string[]
    reflection?: string
    key_insights?: string[]
    remaining_gaps?: string[]
    next_queries?: string[]
    next_direct_urls?: string[]
  }
  responseEntries: any[]
  inputEntries?: any[]
  parentInputUrls?: { url: string; title: string }[]
  noteHook: NotableContentHooks
}

/** Repair a JSON string that has been truncated by balancing braces, brackets, and quotes. */
export function repairTruncatedJson(str: string): string {
  let cleaned = str.trim()
  if (!cleaned) return ""
  
  let inString = false
  let escaped = false
  const stack: ("{" | "[")[] = []
  
  for (let i = 0; i < cleaned.length; i++) {
    const char = cleaned[i]
    if (escaped) {
      escaped = false
      continue
    }
    if (char === "\\") {
      escaped = true
      continue
    }
    if (char === '"') {
      inString = !inString
      continue
    }
    if (inString) {
      continue
    }
    if (char === "{") {
      stack.push("{")
    } else if (char === "[") {
      stack.push("[")
    } else if (char === "}") {
      if (stack[stack.length - 1] === "{") {
        stack.pop()
      }
    } else if (char === "]") {
      if (stack[stack.length - 1] === "[") {
        stack.pop()
      }
    }
  }
  
  let repaired = cleaned
  if (inString) {
    repaired += '"'
  }
  for (let i = stack.length - 1; i >= 0; i--) {
    const openChar = stack[i]
    if (openChar === "{") {
      repaired += "}"
    } else if (openChar === "[") {
      repaired += "]"
    }
  }
  
  return repaired
}

/** Classify a parse result by its raw_content. */
export function parseStatus(content: string | null | undefined): { icon: string; label: string; color: string } {
  if (!content || content.trim().length === 0) return { icon: "✗", label: "empty", color: "var(--color-semantic-red)" }
  const c = content.trim()
  if (c.length < 200) return { icon: "○", label: "too short", color: "var(--color-semantic-gold)" }
  const junkPatterns = ["security check required", "cloudflare", "enable javascript", "please complete the security check"]
  if (junkPatterns.some(p => c.slice(0, 1000).toLowerCase().includes(p))) return { icon: "⚠", label: "blocked", color: "var(--color-semantic-sand)" }
  if (/^(skip|close|open navigation|sign in|sign up)/i.test(c.slice(0, 100).trim())) return { icon: "⛔", label: "paywall", color: "var(--color-semantic-sand)" }
  return { icon: "✓", label: "ok", color: "var(--color-semantic-green)" }
}

function sourceStatusLabel(analysis: any): { label: string; color: string } {
  if (!analysis) return { label: "no analysis", color: "var(--color-ui-dim)" }
  if (analysis.learnings?.length > 0) return { label: `${analysis.learnings.length} learnings`, color: "var(--color-semantic-green)" }
  
  // Check gaps for known error messages
  const gaps = analysis.gaps || []
  for (const gap of gaps) {
    if (typeof gap === "string") {
      const g = gap.toLowerCase()
      if (g.includes("blocked by anti-bot") || g.includes("cloudflare") || g.includes("captcha")) {
        return { label: "blocked (anti-bot)", color: "var(--color-semantic-red)" }
      }
      if (g.includes("content too short") || g.includes("too short")) {
        return { label: "too short", color: "var(--color-semantic-gold)" }
      }
      if (g.includes("fetch failed")) {
        return { label: "fetch failed", color: "var(--color-semantic-red)" }
      }
    }
  }
  
  if (gaps.length > 0) return { label: `${gaps.length} gaps`, color: "var(--color-semantic-gold)" }
  return { label: "no learnings", color: "var(--color-semantic-sand)" }
}

export const StepResultTab = memo(function StepResultTab({
  selected, selectedResults, parsedResult, responseEntries, inputEntries, noteHook,
}: StepResultTabProps) {
  const searchQueries = inputEntries
    ?.filter(e => e.event_type === "orchestrator_search")
    .map(e => ({
      query: (e.event_data as any)?.query || "",
      resultsCount: (e.event_data as any)?.results_count ?? 0,
    })) ?? []

  // ── Digest: aggregate learnings/gaps/followups across all sources ──
  const digestSummary = useMemo(() => {
    if (selected.step_type !== "digest") return null
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
  }, [selectedResults, selected.step_type])

  return (
    <div className="space-y-2 font-mono">
      {selected.result_summary && <div className="text-ui-secondary text-[10px] leading-relaxed">{selected.result_summary}</div>}

      {/* ── Search: queries + fetched URLs ── */}
      {selected.step_type === "search" && (() => {
        // Check if this is a direct-URL bypass group
        const directEntry = inputEntries?.find(e =>
          e.event_type === "orchestrator_search" &&
          (e.event_data as any)?.query === "direct_urls"
        )
        const directUrls: string[] = directEntry ? ((directEntry.event_data as any)?.urls ?? []) : []
        const isDirectGroup = directUrls.length > 0 ||
          selected.query_text?.startsWith("Direct:")

        if (isDirectGroup) {
          return (
            <div className="border-t border-ui-border pt-2 space-y-2">
              <div className="flex items-center gap-1.5">
                <span className="text-semantic-purple text-[8px] font-mono px-1 py-0.5 bg-semantic-purple/10 border border-semantic-purple/30 rounded-sm">
                  ⤷ direct fetch
                </span>
                <span className="text-ui-dim text-[8px]">bypass search engine</span>
              </div>
              <div>
                <div className="text-ui-dim text-[8px] uppercase mb-1">urls to fetch directly ({directUrls.length || selectedResults.length})</div>
                <div className="space-y-0.5">
                  {(directUrls.length > 0 ? directUrls : selectedResults.map(r => r.source_url)).map((u, i) => (
                    <div key={i} className="pl-2 py-0.5 border-l border-ui-border">
                      <a href={u || "#"} target="_blank" rel="noopener noreferrer"
                        className="text-action-dim hover:text-action-hover underline break-all text-[9px] transition-colors">
                        {u || "—"}
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )
        }

        return (
          <div className="border-t border-ui-border pt-2 space-y-2">
            {searchQueries.length > 0 ? (
              <>
                <div className="text-ui-dim text-[8px] uppercase">search queries ({searchQueries.length})</div>
                {searchQueries.map((sq, qi) => (
                  <div key={qi} className="pl-2 border-l border-ui-border">
                    <div className="text-ui-secondary text-[9px] leading-relaxed">"{sq.query}"</div>
                    <div className="text-ui-dim text-[8px]">{sq.resultsCount} results</div>
                  </div>
                ))}
              </>
            ) : selected.query_text ? (
              <div className="pl-2 border-l border-ui-border">
                <div className="text-ui-dim text-[8px] uppercase">search query</div>
                <div className="text-ui-secondary text-[9px] leading-relaxed font-mono">"{selected.query_text}"</div>
              </div>
            ) : null}

            {selectedResults.length > 0 ? (
              <div className="pt-1">
                <div className="text-ui-dim text-[8px] mb-1 uppercase">urls to parse at next step ({selectedResults.length})</div>
                {selectedResults.map(r => (
                  <div key={r.id} className="pl-2 py-0.5">
                    <a href={r.source_url || "#"} target="_blank" rel="noopener noreferrer"
                      className="text-action-dim hover:text-action-hover underline break-all text-[9px] transition-colors">
                      {r.source_title || r.source_url?.slice(0, 100) || "—"}
                    </a>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-ui-dim italic text-[9px] pl-2">
                {searchQueries.some(sq => sq.resultsCount > 0)
                  ? `${searchQueries.reduce((sum, sq) => sum + sq.resultsCount, 0)} links found — fetch + analysis in parse/digest steps`
                  : "no urls found"}
              </div>
            )}
          </div>
        )
      })()}

      {/* ── Parse: per-URL status ── */}
      {selected.step_type === "parallel_parse" && selectedResults.length > 0 && (
        <div className="border-t border-ui-border pt-2 space-y-1">
          <div className="text-ui-dim text-[8px] uppercase mb-1">parsed pages ({selectedResults.length})</div>
          {selectedResults.map(r => {
            const errorMsg = (r as any).error
            const st = errorMsg
              ? { icon: "✗", label: "error", color: "#b86a6a" }
              : parseStatus(r.content_preview)
            return (
              <div key={r.id} className="pl-2 flex items-start gap-1.5 py-0.5">
                <span style={{color: st.color}} className="text-[9px] shrink-0">{st.icon}</span>
                <div className="min-w-0">
                  <a href={r.source_url || "#"} target="_blank" rel="noopener noreferrer"
                    className="text-ui-secondary hover:text-action-hover underline break-all text-[9px] transition-colors">
                    {r.source_title || r.source_url?.slice(0, 100) || "—"}
                  </a>
                  {errorMsg ? (
                    <div className="text-semantic-red text-[7.5px] font-mono leading-tight pl-1">{errorMsg}</div>
                  ) : (
                    r.raw_file_path && <div className="text-ui-dim text-[7px] truncate">saved: {r.raw_file_path}</div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
      {selected.step_type === "parallel_parse" && selectedResults.length === 0 && (
        <div className="text-ui-dim italic text-[9px] border-t border-ui-border pt-2 font-mono">no parsed results</div>
      )}

      {/* ── Plan: generated queries ── */}
      {selected.step_type === "plan" && (parsedResult.queries.length > 0 || parsedResult.goal) && (
        <div className="border-t border-ui-border pt-2 space-y-1">
          {parsedResult.goal && <div><div className="text-ui-dim text-[8px] uppercase">goal:</div><div className="text-ui-secondary text-[9px] pl-2 font-mono">{parsedResult.goal}</div></div>}
          {parsedResult.queries.length > 0 && <div>
            <div className="text-ui-dim text-[8px] mb-0.5 uppercase">search queries ({parsedResult.queries.length}):</div>
            {parsedResult.queries.map((q, i) => <div key={i} className="text-semantic-green text-[9px] pl-2 leading-relaxed">{i+1}. {q}</div>)}
          </div>}
        </div>
      )}

      {/* ── Digest: per-source analysis + combined summary ── */}
      {selected.step_type === "digest" && selectedResults.length > 0 && (
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
                  {analysis?.learnings?.length > 0 && <div className="mt-1">
                    <div className="text-ui-dim text-[8px] mb-0.5">learnings:</div>
                    {analysis.learnings.map((l: string, li: number) => (
                      <div key={li} className="text-ui-secondary text-[9px] pl-2 leading-relaxed">· {l}</div>
                    ))}
                  </div>}
                  {analysis?.gaps?.length > 0 && <div className="mt-1">
                    <div className="text-ui-dim text-[8px] mb-0.5">gaps:</div>
                    {analysis.gaps.map((g: string, gi: number) => (
                      <div key={gi} className="text-semantic-gold text-[9px] pl-2 leading-relaxed">◇ {g}</div>
                    ))}
                  </div>}
                  {analysis?.followups?.length > 0 && <div className="mt-1">
                    <div className="text-ui-dim text-[8px] mb-0.5">followups:</div>
                    {analysis.followups.map((f: string, fi: number) => (
                      <div key={fi} className="text-semantic-purple text-[9px] pl-2 leading-relaxed">→ {f}</div>
                    ))}
                  </div>}
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

          {/* Combined digest summary */}
          {digestSummary && (digestSummary.learnings.length > 0 || digestSummary.gaps.length > 0) && (
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
                        {i+1}. {l}
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

          {/* Collapsible raw database results block */}
          <details className="border-t border-ui-border pt-2">
            <summary className="text-semantic-header text-[9px] uppercase tracking-wider cursor-pointer hover:text-ui-secondary mb-1">
              [+] view raw digested results ({selectedResults.length} sources)
            </summary>
            <div className="mt-2 font-sans">
              <JsonBlock data={selectedResults.map(r => {
                let analysis: any = null
                try { analysis = r.analyzed_json ? JSON.parse(r.analyzed_json) : r.analyzed_json } catch {}
                return {
                  title: r.source_title,
                  url: r.source_url,
                  analysis
                }
              })} variant="json" maxHeight="max-h-64" />
            </div>
          </details>
        </>
      )}
      {selected.step_type === "digest" && selectedResults.length === 0 && (
        <div className="text-ui-dim italic text-[9px] border-t border-ui-border pt-2">no digested results</div>
      )}

      {/* ── Reflect: completeness, insights, gaps, next actions ── */}
      {selected.step_type === "reflect" && (
        <div className="border-t border-ui-border pt-2 space-y-3">
          {parsedResult.completeness > 0 && (
            <div>
              <div className="text-ui-dim text-[8px] uppercase">completeness score:</div>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex-1 h-2 bg-ui-border rounded-sm overflow-hidden">
                  <div className="h-full bg-semantic-green rounded-sm" style={{width: `${Math.round(parsedResult.completeness*100)}%`}} />
                </div>
                <span className="text-semantic-green text-[9px] font-mono">{Math.round(parsedResult.completeness*100)}%</span>
              </div>
            </div>
          )}

          {parsedResult.reflection && (
            <NotableContent hooks={noteHook} title="consolidated analysis">
              <div className="text-ui-secondary text-[9.5px] leading-relaxed whitespace-pre-wrap border border-ui-border p-2 bg-[#080808]/30 rounded-sm">
                {parsedResult.reflection}
              </div>
            </NotableContent>
          )}

          {parsedResult.key_insights && parsedResult.key_insights.length > 0 && (
            <NotableContent hooks={noteHook} title={`key insights (${parsedResult.key_insights.length})`}>
              <div className="space-y-0.5 max-h-36 overflow-y-auto pr-1 border border-ui-border p-2 bg-[#080808]/30">
                {parsedResult.key_insights.map((insight, i) => (
                  <div key={i} className="text-semantic-green text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                    ✓ {insight}
                  </div>
                ))}
              </div>
            </NotableContent>
          )}

          {parsedResult.remaining_gaps && parsedResult.remaining_gaps.length > 0 && (
            <NotableContent hooks={noteHook} title={`remaining gaps (${parsedResult.remaining_gaps.length})`}>
              <div className="space-y-0.5 max-h-36 overflow-y-auto pr-1 border border-ui-border p-2 bg-[#080808]/30">
                {parsedResult.remaining_gaps.map((gap, i) => (
                  <div key={i} className="text-semantic-gold text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                    ◇ {gap}
                  </div>
                ))}
              </div>
            </NotableContent>
          )}

          {parsedResult.next_queries && parsedResult.next_queries.length > 0 && (
            <NotableContent hooks={noteHook} title={`planned next search queries (${parsedResult.next_queries.length})`}>
              <div className="space-y-0.5 pl-2">
                {parsedResult.next_queries.map((q, i) => (
                  <div key={i} className="text-ui-secondary text-[9px]">· {q}</div>
                ))}
              </div>
            </NotableContent>
          )}

          {parsedResult.next_direct_urls && parsedResult.next_direct_urls.length > 0 && (
            <div>
              <div className="text-ui-dim text-[8px] mb-1 uppercase font-mono font-semibold">planned direct URLs to parse ({parsedResult.next_direct_urls.length})</div>
              <div className="space-y-0.5 pl-2 font-mono">
                {parsedResult.next_direct_urls.map((u, i) => (
                  <div key={i} className="text-ui-secondary text-[9px] leading-relaxed">
                    <span className="text-ui-dim">{i+1}.</span>{" "}
                    <a href={u} target="_blank" rel="noopener noreferrer"
                      className="text-action-dim hover:text-action-hover underline break-all transition-colors">
                      {u}
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Synthesize: answer ── */}
      {selected.step_type === "synthesize" && parsedResult.answer && (
        <div className="border-t border-ui-border pt-2 space-y-1.5 font-sans">
          <NotableMarkdown
            assetType="research_step"
            assetId={selected.id}
            content={parsedResult.answer}
            title={`synthesis report${parsedResult.confidence > 0 ? ` (confidence: ${Math.round(parsedResult.confidence*100)}%)` : ""}`}
            contentClassName="text-ui-secondary text-[10px] leading-relaxed prose prose-invert prose-xs max-w-none max-h-[500px] overflow-y-auto border border-ui-border p-2 bg-[#080808]/30"
          />
        </div>
      )}

      {/* ── Evaluate: decision + reasoning ── */}
      {selected.step_type === "evaluate" && (() => {
        // Parse evaluate meta-log entry for structured fields
        const evalEntry = inputEntries?.find(e =>
          e.event_type === "orchestrator_evaluate"
        ) ?? responseEntries.find(e =>
          e.event_type === "orchestrator_evaluate"
        )
        const evalData = evalEntry?.event_data as any
        const decision: string = evalData?.decision ?? (
          selected.result_summary?.startsWith("STOP") ? "stop" : "continue"
        )
        const isStop = decision === "stop"
        const reason: string = evalData?.reason ?? selected.result_summary ?? ""
        const completeness: number = evalData?.completeness ?? evalData?.completeness_score ?? 0
        const hadLlm = responseEntries.some(e =>
          e.event_type === "orchestrator_evaluate_response"
        )

        return (
          <div className="border-t border-ui-border pt-2 space-y-3 font-mono">
            {/* Decision badge */}
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-sm border ${
                isStop
                  ? "text-semantic-red border-semantic-red/40 bg-semantic-red/8"
                  : "text-semantic-green border-semantic-green/40 bg-semantic-green/8"
              }`}>
                {isStop ? "■ STOP" : "▶ CONTINUE"}
              </span>
              <span className={`text-[8px] font-mono px-1 py-0.5 rounded-sm ${
                hadLlm
                  ? "text-semantic-gold bg-semantic-gold/10"
                  : "text-ui-dim bg-ui-border"
              }`}>
                {hadLlm ? "via LLM" : "hard rule"}
              </span>
            </div>

            {/* Reason */}
            {reason && (
              <div>
                <div className="text-ui-dim text-[8px] uppercase mb-0.5">reason</div>
                <div className="text-ui-secondary text-[9px] leading-relaxed border border-ui-border p-2 bg-[#080808]/30 rounded-sm">
                  {reason.replace(/^(STOP|CONTINUE):\s*/i, "")}
                </div>
              </div>
            )}

            {/* Completeness bar */}
            {completeness > 0 && (
              <div>
                <div className="text-ui-dim text-[8px] uppercase mb-1">completeness at decision</div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-ui-border rounded-sm overflow-hidden">
                    <div
                      className={`h-full rounded-sm ${isStop ? "bg-semantic-green" : "bg-semantic-gold"}`}
                      style={{ width: `${Math.round(completeness * 100)}%` }}
                    />
                  </div>
                  <span className="text-ui-secondary text-[9px] font-mono">{Math.round(completeness * 100)}%</span>
                </div>
              </div>
            )}

            {/* LLM parsed output (only when LLM was called) */}
            {hadLlm && (() => {
              const llmEntry = responseEntries.find(e => e.event_type === "orchestrator_evaluate_response")
              if (!llmEntry) return null
              const d = llmEntry.event_data as any
              const rawStr = d?.raw_response || d?.raw || ""
              let llmJson: any = null
              try {
                const parsed = typeof rawStr === "string" ? JSON.parse(rawStr) : rawStr
                const inner = parsed?.json_data || parsed?.content
                llmJson = typeof inner === "string" ? JSON.parse(inner) : inner
              } catch {}
              if (!llmJson) return null
              return (
                <div className="space-y-1">
                  <div className="text-ui-dim text-[8px] uppercase">llm evaluator output</div>
                  <JsonBlock data={llmJson} variant="json" maxHeight="max-h-32" />
                </div>
              )
            })()}
          </div>
        )
      })()}

      {/* ── LLM response(s) from meta-log ── */}
      {responseEntries.length > 0 && (
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
                    {entry.event_type.replace("orchestrator_","").replace("_response","")} ({entry.created_at?.slice(11,19)})
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
                  {entry.event_type.replace("orchestrator_","").replace("_response","")} ({entry.created_at?.slice(11,19)}) {resp.model && <span className="text-ui-dim">— {resp.model}</span>} {resp.truncated && <span className="text-semantic-gold text-[8px] font-mono">[truncated]</span>}
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
      )}

      {selectedResults.length === 0 && !selected.result_summary && responseEntries.length === 0
        && selected.step_type !== "evaluate" && !(selected.step_type === "search" && searchQueries.length > 0) && (
        <div className="text-ui-dim italic text-[9px]">no result data</div>
      )}
    </div>
  )
})
