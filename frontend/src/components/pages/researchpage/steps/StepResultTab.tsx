import React, { memo } from "react"
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
  }
  responseEntries: any[]
  inputEntries?: any[]
}

export const StepResultTab = memo(function StepResultTab({
  selected, selectedResults, parsedResult, responseEntries, inputEntries,
}: StepResultTabProps) {
  // Extract search queries from orchestrator_search events
  const searchQueries = inputEntries
    ?.filter(e => e.event_type === "orchestrator_search")
    .map(e => ({
      query: (e.event_data as any)?.query || "",
      resultsCount: (e.event_data as any)?.results_count ?? 0,
    })) ?? []

  return (
    <div className="space-y-2">
      {selected.result_summary && <div className="text-[#94a3b8] text-[10px]">{selected.result_summary}</div>}

      {/* ── Search: queries + fetched URLs ── */}
      {selected.step_type === "search" && searchQueries.length > 0 && (
        <div className="border-t border-[#1a1a1a] pt-2 space-y-2">
          <div className="text-[#555] text-[8px] uppercase">search queries ({searchQueries.length})</div>
          {searchQueries.map((sq, qi) => (
            <div key={qi} className="pl-2 border-l border-[#222]">
              <div className="text-[#94a3b8] text-[9px] leading-relaxed">"{sq.query}"</div>
              <div className="text-[#555] text-[8px]">{sq.resultsCount} results</div>
            </div>
          ))}
          {selectedResults.length > 0 && (
            <div className="pt-1">
              <div className="text-[#555] text-[8px] mb-1 uppercase">fetched urls ({selectedResults.length})</div>
              {selectedResults.map(r => (
                <div key={r.id} className="pl-2 py-0.5">
                  <a href={r.source_url || "#"} target="_blank" rel="noopener noreferrer"
                    className="text-[#4ade80] hover:text-[#6ee7b0] underline break-all text-[9px]">
                    {r.source_title || r.source_url?.slice(0, 100) || "—"}
                  </a>
                </div>
              ))}
            </div>
          )}
          {selectedResults.length === 0 && (
            <div className="text-[#444] italic text-[9px] pl-2">no urls harvested yet</div>
          )}
        </div>
      )}

      {/* Plan: generated queries */}
      {selected.step_type === "plan" && (parsedResult.queries.length > 0 || parsedResult.goal) && (
        <div className="border-t border-[#1a1a1a] pt-2 space-y-1">
          {parsedResult.goal && <div><div className="text-[#555] text-[8px]">goal:</div><div className="text-[#94a3b8] text-[9px] pl-2">{parsedResult.goal}</div></div>}
          {parsedResult.queries.length > 0 && <div>
            <div className="text-[#555] text-[8px] mb-0.5">search queries ({parsedResult.queries.length}):</div>
            {parsedResult.queries.map((q, i) => <div key={i} className="text-[#4ade80] text-[9px] pl-2 leading-relaxed">{i+1}. {q}</div>)}
          </div>}
        </div>
      )}

      {/* Digest/Parse: per-source learnings */}
      {selected.step_type !== "search" && selectedResults.length > 0 && selectedResults.map(r => {
        let analysis: any = null
        try { analysis = r.analyzed_json ? JSON.parse(r.analyzed_json) : null } catch {}
        return (
          <div key={r.id} className="border-t border-[#1a1a1a] pt-2">
            <a href={r.source_url || "#"} target="_blank" rel="noopener noreferrer"
              className="text-[#4ade80] hover:text-[#6ee7b0] underline break-all font-bold">{r.source_title || r.source_url?.slice(0, 100) || "—"}</a>
            {analysis?.learnings?.length > 0 && <div className="mt-1">
              <div className="text-[#555] text-[9px] mb-0.5">learnings:</div>
              {analysis.learnings.map((l: string, li: number) => (
                <div key={li} className="text-[#888] text-[9px] pl-2 leading-relaxed">· {l}</div>
              ))}
            </div>}
            {analysis?.gaps?.length > 0 && <div className="mt-1">
              <div className="text-[#555] text-[9px] mb-0.5">gaps:</div>
              {analysis.gaps.map((g: string, gi: number) => (
                <div key={gi} className="text-[#f59e0b] text-[9px] pl-2 leading-relaxed">◇ {g}</div>
              ))}
            </div>}
            {r.raw_file_path && <div className="text-[#555] text-[8px] mt-1">saved: {r.raw_file_path}</div>}
          </div>
        )
      })}

      {/* Reflect: completeness */}
      {selected.step_type === "reflect" && parsedResult.completeness > 0 && (
        <div className="border-t border-[#1a1a1a] pt-2">
          <div className="text-[#555] text-[8px]">completeness score:</div>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-2 bg-[#1a1a1a] rounded-sm overflow-hidden">
              <div className="h-full bg-[#4ade80] rounded-sm" style={{width: `${Math.round(parsedResult.completeness*100)}%`}} />
            </div>
            <span className="text-[#4ade80] text-[9px] font-mono">{Math.round(parsedResult.completeness*100)}%</span>
          </div>
        </div>
      )}

      {/* Synthesize: answer */}
      {selected.step_type === "synthesize" && parsedResult.answer && (
        <div className="border-t border-[#1a1a1a] pt-2">
          <div className="text-[#555] text-[8px] mb-1">
            answer{parsedResult.confidence > 0 ? ` (confidence: ${Math.round(parsedResult.confidence*100)}%)` : ""}:
          </div>
          <div className="text-[#94a3b8] text-[9px] leading-relaxed whitespace-pre-wrap">{parsedResult.answer}</div>
        </div>
      )}

      {/* LLM response(s) from meta-log — full detail with thinking trace, wrapper */}
      {responseEntries.length > 0 && (
        <div className="border-t border-[#1a1a1a] pt-2">
          <div className="text-[#555] text-[9px] mb-1">llm responses ({responseEntries.length}):</div>
          {responseEntries.map((entry, ei) => {
            const d = entry.event_data as any
            const rawStr = d?.raw_response || d?.response || ""
            if (!rawStr || rawStr === "{}") return null
            let resp: any = null
            try { resp = JSON.parse(rawStr) } catch { /* raw text, fallback */ }

            if (!resp || typeof resp !== "object") {
              return (
                <details key={ei} className="mb-1">
                  <summary className="text-[#777] text-[9px] cursor-pointer hover:text-[#aaa]">
                    {entry.event_type.replace("orchestrator_","").replace("_response","")} ({entry.created_at?.slice(11,19)})
                  </summary>
                  <div className="mt-1">
                    <JsonBlock data={rawStr.slice(0, 4000)} variant="raw" />
                  </div>
                </details>
              )
            }

            const jsonData = resp.json_data || resp.content
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
        && !(selected.step_type === "search" && searchQueries.length > 0) && (
        <div className="text-[#444] italic text-[9px]">no result data</div>
      )}
    </div>
  )
})
