import { memo, useMemo } from "react"
import type { ResearchStep, ResearchStepResult } from "../../../../api/research"
import { JsonBlock } from "../../../UI"

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
  if (!content || content.trim().length === 0) return { icon: "✗", label: "empty", color: "#ef4444" }
  const c = content.trim()
  if (c.length < 200) return { icon: "○", label: "too short", color: "#f59e0b" }
  const junkPatterns = ["security check required", "cloudflare", "enable javascript", "please complete the security check"]
  if (junkPatterns.some(p => c.slice(0, 1000).toLowerCase().includes(p))) return { icon: "⚠", label: "blocked", color: "#f97316" }
  if (/^(skip|close|open navigation|sign in|sign up)/i.test(c.slice(0, 100).trim())) return { icon: "⛔", label: "paywall", color: "#f97316" }
  return { icon: "✓", label: "ok", color: "#4ade80" }
}

function sourceStatusLabel(analysis: any): { label: string; color: string } {
  if (!analysis) return { label: "no analysis", color: "#666" }
  if (analysis.learnings?.length > 0) return { label: `${analysis.learnings.length} learnings`, color: "#4ade80" }
  
  // Check gaps for known error messages
  const gaps = analysis.gaps || []
  for (const gap of gaps) {
    if (typeof gap === "string") {
      const g = gap.toLowerCase()
      if (g.includes("blocked by anti-bot") || g.includes("cloudflare") || g.includes("captcha")) {
        return { label: "blocked (anti-bot)", color: "#ef4444" }
      }
      if (g.includes("content too short") || g.includes("too short")) {
        return { label: "too short", color: "#f59e0b" }
      }
      if (g.includes("fetch failed")) {
        return { label: "fetch failed", color: "#ef4444" }
      }
    }
  }
  
  if (gaps.length > 0) return { label: `${gaps.length} gaps`, color: "#f59e0b" }
  return { label: "no learnings", color: "#f97316" }
}

export const StepResultTab = memo(function StepResultTab({
  selected, selectedResults, parsedResult, responseEntries, inputEntries,
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
    <div className="space-y-2">
      {selected.result_summary && <div className="text-[#94a3b8] text-[10px]">{selected.result_summary}</div>}

      {/* ── Search: queries + fetched URLs ── */}
      {selected.step_type === "search" && (
        <div className="border-t border-[#1a1a1a] pt-2 space-y-2">
          {searchQueries.length > 0 ? (
            <>
              <div className="text-[#555] text-[8px] uppercase">search queries ({searchQueries.length})</div>
              {searchQueries.map((sq, qi) => (
                <div key={qi} className="pl-2 border-l border-[#222]">
                  <div className="text-[#94a3b8] text-[9px] leading-relaxed">"{sq.query}"</div>
                  <div className="text-[#555] text-[8px]">{sq.resultsCount} results</div>
                </div>
              ))}
            </>
          ) : selected.query_text ? (
            <div className="pl-2 border-l border-[#222]">
              <div className="text-[#555] text-[8px] uppercase">search query</div>
              <div className="text-[#94a3b8] text-[9px] leading-relaxed">"{selected.query_text}"</div>
            </div>
          ) : null}

          {selectedResults.length > 0 ? (
            <div className="pt-1">
              <div className="text-[#555] text-[8px] mb-1 uppercase">urls to parse at next step ({selectedResults.length})</div>
              {selectedResults.map(r => (
                <div key={r.id} className="pl-2 py-0.5">
                  <a href={r.source_url || "#"} target="_blank" rel="noopener noreferrer"
                    className="text-[#4ade80] hover:text-[#6ee7b0] underline break-all text-[9px]">
                    {r.source_title || r.source_url?.slice(0, 100) || "—"}
                  </a>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[#444] italic text-[9px] pl-2">
              {searchQueries.some(sq => sq.resultsCount > 0)
                ? `${searchQueries.reduce((sum, sq) => sum + sq.resultsCount, 0)} links found — fetch + analysis in parse/digest steps`
                : "no urls found"}
            </div>
          )}
        </div>
      )}

      {/* ── Parse: per-URL status ── */}
      {selected.step_type === "parallel_parse" && selectedResults.length > 0 && (
        <div className="border-t border-[#1a1a1a] pt-2 space-y-1">
          <div className="text-[#555] text-[8px] uppercase mb-1">parsed pages ({selectedResults.length})</div>
          {selectedResults.map(r => {
            const errorMsg = (r as any).error
            const st = errorMsg
              ? { icon: "✗", label: "error", color: "#ef4444" }
              : parseStatus(r.content_preview)
            return (
              <div key={r.id} className="pl-2 flex items-start gap-1.5 py-0.5">
                <span style={{color: st.color}} className="text-[9px] shrink-0">{st.icon}</span>
                <div className="min-w-0">
                  <a href={r.source_url || "#"} target="_blank" rel="noopener noreferrer"
                    className="text-[#94a3b8] hover:text-[#c4b5fd] underline break-all text-[9px]">
                    {r.source_title || r.source_url?.slice(0, 100) || "—"}
                  </a>
                  {errorMsg ? (
                    <div className="text-[#ef4444] text-[7.5px] font-mono leading-tight pl-1">{errorMsg}</div>
                  ) : (
                    r.raw_file_path && <div className="text-[#555] text-[7px] truncate">saved: {r.raw_file_path}</div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
      {selected.step_type === "parallel_parse" && selectedResults.length === 0 && (
        <div className="text-[#444] italic text-[9px] border-t border-[#1a1a1a] pt-2">no parsed results</div>
      )}

      {/* ── Plan: generated queries ── */}
      {selected.step_type === "plan" && (parsedResult.queries.length > 0 || parsedResult.goal) && (
        <div className="border-t border-[#1a1a1a] pt-2 space-y-1">
          {parsedResult.goal && <div><div className="text-[#555] text-[8px]">goal:</div><div className="text-[#94a3b8] text-[9px] pl-2">{parsedResult.goal}</div></div>}
          {parsedResult.queries.length > 0 && <div>
            <div className="text-[#555] text-[8px] mb-0.5">search queries ({parsedResult.queries.length}):</div>
            {parsedResult.queries.map((q, i) => <div key={i} className="text-[#4ade80] text-[9px] pl-2 leading-relaxed">{i+1}. {q}</div>)}
          </div>}
        </div>
      )}

      {/* ── Digest: per-source analysis + combined summary ── */}
      {selected.step_type === "digest" && selectedResults.length > 0 && (
        <>
          <div className="border-t border-[#1a1a1a] pt-2 space-y-2">
            <div className="text-[#555] text-[8px] uppercase">per-source analysis ({selectedResults.length})</div>
            {selectedResults.map(r => {
              let analysis: any = null
              try { analysis = r.analyzed_json ? JSON.parse(r.analyzed_json) : null } catch {}
              const status = sourceStatusLabel(analysis)
              const hasContent = analysis?.learnings?.length > 0 || analysis?.gaps?.length > 0
              return (
                <details key={r.id} className="pl-2 border-l border-[#222]">
                  <summary className="text-[#94a3b8] text-[9px] cursor-pointer hover:text-[#c4b5fd] break-all flex items-center gap-1">
                    <span className="truncate">{r.source_title || r.source_url?.slice(0, 80) || "—"}</span>
                    <span style={{ color: status.color }} className="text-[8px] shrink-0 font-mono">({status.label})</span>
                  </summary>
                  {analysis?.learnings?.length > 0 && <div className="mt-1">
                    <div className="text-[#555] text-[8px] mb-0.5">learnings:</div>
                    {analysis.learnings.map((l: string, li: number) => (
                      <div key={li} className="text-[#888] text-[9px] pl-2 leading-relaxed">· {l}</div>
                    ))}
                  </div>}
                  {analysis?.gaps?.length > 0 && <div className="mt-1">
                    <div className="text-[#555] text-[8px] mb-0.5">gaps:</div>
                    {analysis.gaps.map((g: string, gi: number) => (
                      <div key={gi} className="text-[#f59e0b] text-[9px] pl-2 leading-relaxed">◇ {g}</div>
                    ))}
                  </div>}
                  {analysis?.followups?.length > 0 && <div className="mt-1">
                    <div className="text-[#555] text-[8px] mb-0.5">followups:</div>
                    {analysis.followups.map((f: string, fi: number) => (
                      <div key={fi} className="text-[#a78bfa] text-[9px] pl-2 leading-relaxed">→ {f}</div>
                    ))}
                  </div>}
                  {analysis && (
                    <details className="mt-1.5 pl-2 border-l border-[#1a1a1a]">
                      <summary className="text-[#555] text-[7.5px] cursor-pointer hover:text-[#777] uppercase">raw analysis payload (json)</summary>
                      <div className="mt-1">
                        <JsonBlock data={analysis} variant="json" maxHeight="max-h-36" />
                      </div>
                    </details>
                  )}
                  {!hasContent && <div className="text-[#f59e0b] text-[8px] mt-1 italic">no data extracted</div>}
                </details>
              )
            })}
          </div>

          {/* Combined digest summary */}
          {digestSummary && (digestSummary.learnings.length > 0 || digestSummary.gaps.length > 0) && (
            <div className="border-t border-[#1a1a1a] pt-2 space-y-1">
              <div className="text-[#6c6c8a] text-[9px] uppercase tracking-wider mb-1">
                → combined summary ({digestSummary.learnings.length} learnings, {digestSummary.gaps.length} gaps)
              </div>
              {digestSummary.learnings.length > 0 && (
                <details open>
                  <summary className="text-[#4ade80] text-[9px] cursor-pointer hover:text-[#6ee7b0]">
                    all learnings ({digestSummary.learnings.length})
                  </summary>
                  <div className="mt-1 space-y-0.5 max-h-48 overflow-y-auto">
                    {digestSummary.learnings.map((l, i) => (
                      <div key={i} className="text-[#94a3b8] text-[9px] pl-2 leading-relaxed border-l border-[#1a3a1a]">
                        {i+1}. {l}
                      </div>
                    ))}
                  </div>
                </details>
              )}
              {digestSummary.gaps.length > 0 && (
                <details>
                  <summary className="text-[#f59e0b] text-[9px] cursor-pointer hover:text-[#fbbf24]">
                    all gaps ({digestSummary.gaps.length})
                  </summary>
                  <div className="mt-1 space-y-0.5 max-h-32 overflow-y-auto">
                    {digestSummary.gaps.map((g, i) => (
                      <div key={i} className="text-[#888] text-[9px] pl-2 leading-relaxed">◇ {g}</div>
                    ))}
                  </div>
                </details>
              )}
              {digestSummary.followups.length > 0 && (
                <details>
                  <summary className="text-[#a78bfa] text-[9px] cursor-pointer hover:text-[#c4b5fd]">
                    all followups ({digestSummary.followups.length})
                  </summary>
                  <div className="mt-1 space-y-0.5 max-h-32 overflow-y-auto">
                    {digestSummary.followups.map((f, i) => (
                      <div key={i} className="text-[#a78bfa] text-[9px] pl-2 leading-relaxed">→ {f}</div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          )}

          {/* Collapsible raw database results block */}
          <details className="border-t border-[#1a1a1a] pt-2">
            <summary className="text-[#6c6c8a] text-[9px] uppercase tracking-wider cursor-pointer hover:text-[#94a3b8] mb-1">
              [+] view raw digested results ({selectedResults.length} sources)
            </summary>
            <div className="mt-2">
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
        <div className="text-[#444] italic text-[9px] border-t border-[#1a1a1a] pt-2">no digested results</div>
      )}

      {/* ── Reflect: completeness, insights, gaps, next actions ── */}
      {selected.step_type === "reflect" && (
        <div className="border-t border-[#1a1a1a] pt-2 space-y-3">
          {parsedResult.completeness > 0 && (
            <div>
              <div className="text-[#555] text-[8px]">completeness score:</div>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex-1 h-2 bg-[#1a1a1a] rounded-sm overflow-hidden">
                  <div className="h-full bg-[#4ade80] rounded-sm" style={{width: `${Math.round(parsedResult.completeness*100)}%`}} />
                </div>
                <span className="text-[#4ade80] text-[9px] font-mono">{Math.round(parsedResult.completeness*100)}%</span>
              </div>
            </div>
          )}

          {parsedResult.reflection && (
            <div>
              <div className="text-[#555] text-[8px] mb-1 uppercase font-mono">consolidated analysis</div>
              <div className="text-[#94a3b8] text-[9.5px] leading-relaxed whitespace-pre-wrap border border-[#1a1a1a] p-2 bg-[#080808]/30 rounded-sm">
                {parsedResult.reflection}
              </div>
            </div>
          )}

          {parsedResult.key_insights && parsedResult.key_insights.length > 0 && (
            <div>
              <div className="text-[#555] text-[8px] mb-1 uppercase font-mono">key insights ({parsedResult.key_insights.length})</div>
              <div className="space-y-0.5 max-h-36 overflow-y-auto pr-1 border border-[#1a1a1a] p-2 bg-[#080808]/30">
                {parsedResult.key_insights.map((insight, i) => (
                  <div key={i} className="text-[#4ade80] text-[9px] pl-2 border-l border-[#222] leading-relaxed">
                    ✓ {insight}
                  </div>
                ))}
              </div>
            </div>
          )}

          {parsedResult.remaining_gaps && parsedResult.remaining_gaps.length > 0 && (
            <div>
              <div className="text-[#555] text-[8px] mb-1 uppercase font-mono">remaining gaps ({parsedResult.remaining_gaps.length})</div>
              <div className="space-y-0.5 max-h-36 overflow-y-auto pr-1 border border-[#1a1a1a] p-2 bg-[#080808]/30">
                {parsedResult.remaining_gaps.map((gap, i) => (
                  <div key={i} className="text-[#f59e0b] text-[9px] pl-2 border-l border-[#222] leading-relaxed">
                    ◇ {gap}
                  </div>
                ))}
              </div>
            </div>
          )}

          {parsedResult.next_queries && parsedResult.next_queries.length > 0 && (
            <div>
              <div className="text-[#555] text-[8px] mb-1 uppercase font-mono">planned next search queries ({parsedResult.next_queries.length})</div>
              <div className="space-y-0.5 pl-2">
                {parsedResult.next_queries.map((q, i) => (
                  <div key={i} className="text-[#94a3b8] text-[9px]">· {q}</div>
                ))}
              </div>
            </div>
          )}

          {parsedResult.next_direct_urls && parsedResult.next_direct_urls.length > 0 && (
            <div>
              <div className="text-[#555] text-[8px] mb-1 uppercase font-mono">planned direct URLs to parse ({parsedResult.next_direct_urls.length})</div>
              <div className="space-y-0.5 pl-2">
                {parsedResult.next_direct_urls.map((u, i) => (
                  <div key={i} className="text-[#94a3b8] text-[9px] leading-relaxed">
                    <span className="text-[#555]">{i+1}.</span>{" "}
                    <a href={u} target="_blank" rel="noopener noreferrer"
                      className="text-[#4ade80] hover:text-[#6ee7b0] underline break-all">
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
        <div className="border-t border-[#1a1a1a] pt-2">
          <div className="text-[#555] text-[8px] mb-1">
            answer{parsedResult.confidence > 0 ? ` (confidence: ${Math.round(parsedResult.confidence*100)}%)` : ""}:
          </div>
          <div className="text-[#94a3b8] text-[9px] leading-relaxed whitespace-pre-wrap">{parsedResult.answer}</div>
        </div>
      )}

      {/* ── Evaluate: reason ── */}
      {selected.step_type === "evaluate" && selected.result_summary && (
        <div className="border-t border-[#1a1a1a] pt-2">
          <div className="text-[#555] text-[8px] uppercase mb-1">decision</div>
          <div className="text-[#22d3ee] text-[9px]">{selected.result_summary}</div>
        </div>
      )}

      {/* ── LLM response(s) from meta-log ── */}
      {responseEntries.length > 0 && (
        <div className="border-t border-[#1a1a1a] pt-2">
          <div className="text-[#555] text-[9px] mb-1">llm responses ({responseEntries.length}):</div>
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
                  <summary className="text-[#777] text-[9px] cursor-pointer hover:text-[#aaa]">
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
                <summary className="text-[#777] text-[9px] cursor-pointer hover:text-[#aaa]">
                  {entry.event_type.replace("orchestrator_","").replace("_response","")} ({entry.created_at?.slice(11,19)}) {resp.model && <span className="text-[#555]">— {resp.model}</span>} {resp.truncated && <span className="text-[#f59e0b] text-[8px]">[truncated]</span>}
                </summary>
                {jsonData && (
                  <div className="mt-2">
                    <div className="text-[#555] text-[7px] mb-0.5 uppercase">output:</div>
                    <JsonBlock data={jsonData} />
                  </div>
                )}
                {thinking && (
                  <details className="mt-1">
                    <summary className="text-[#555] text-[7px] cursor-pointer hover:text-[#888] uppercase">thinking trace ({thinking.length} chars)</summary>
                    <JsonBlock data={thinking} variant="dim" maxHeight="max-h-48" className="mt-1" />
                  </details>
                )}
                <details className="mt-1">
                  <summary className="text-[#444] text-[7px] cursor-pointer hover:text-[#666]">raw wrapper</summary>
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
        <div className="text-[#444] italic text-[9px]">no result data</div>
      )}
    </div>
  )
})
