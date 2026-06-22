import React, { memo } from "react"
import type { StepPreview } from "../../../../api/research"
import { JsonBlock, KeyValueGrid } from "../../../UI"

interface StepPreviewPanelProps {
  preview: StepPreview
  phaseLabel: string
  onReinitialize: () => void
  reinitLoading: boolean
}

export const StepPreviewPanel = memo(function StepPreviewPanel({
  preview, phaseLabel, onReinitialize, reinitLoading,
}: StepPreviewPanelProps) {
  return (
    <div className="space-y-3 text-[10px]">
      <div className="flex items-center justify-between">
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider font-mono">
          [ {phaseLabel} — preview ]
        </div>
        <button onClick={onReinitialize} disabled={reinitLoading}
          className="text-[#4ade80] hover:text-[#6ee7b0] text-[9px] font-mono disabled:text-[#333] cursor-pointer">
          [{reinitLoading ? "…" : "⟳ reinitialize"}]
        </button>
      </div>
      <div className="flex gap-3 border-b border-[#1a1a1a] pb-1">
        <span className="text-[#94a3b8] text-[9px] uppercase font-mono">input / upcoming state</span>
      </div>
      {preview.objective && (
        <div>
          <div className="text-[#555] text-[9px] mb-0.5 uppercase font-mono">objective:</div>
          <div className="text-[#94a3b8] pl-2">{preview.objective}</div>
        </div>
      )}
      {preview.max_depth != null && (
        <div className="flex gap-4 text-[#777] flex-wrap font-mono">
          <span>depth: {preview.max_depth}</span>
          <span>budget: ${preview.budget_limit_usd?.toFixed(2)}</span>
          {preview.model && <span>model: {preview.model}</span>}
          {preview.temperature != null && <span>temp: {preview.temperature}</span>}
          {preview.max_tokens && <span>tokens: {preview.max_tokens}</span>}
        </div>
      )}
      {preview.system_prompt && (
        <JsonBlock
          data={preview.system_prompt}
          variant="prompt"
          maxHeight="max-h-[350px]"
          collapsible={true}
          defaultCollapsed={true}
          label="system prompt"
        />
      )}
      {preview.user_prompt && (
        <JsonBlock
          data={preview.user_prompt}
          variant="prompt"
          maxHeight="max-h-[350px]"
          collapsible={true}
          defaultCollapsed={false}
          label="user prompt"
        />
      )}
      {preview.pending_queries && preview.pending_queries.length > 0 && (
        <div>
          <div className="text-[#555] text-[9px] mb-0.5 uppercase font-mono">pending queries:</div>
          {preview.pending_queries.map((q, i) => (
            <div key={i} className="text-[#94a3b8] pl-2">· {q}</div>
          ))}
        </div>
      )}
      {preview.urls_to_fetch && preview.urls_to_fetch.length > 0 && (
        <div>
          <div className="text-[#555] text-[9px] mb-1 uppercase font-mono">urls to parse ({preview.urls_to_fetch.length})</div>
          <div className="space-y-0.5 max-h-48 overflow-y-auto">
            {preview.urls_to_fetch.map((u, i) => (
              <div key={i} className="text-[#94a3b8] text-[9px] pl-2 border-l border-[#222] leading-relaxed">
                <span className="text-[#555]">{i+1}.</span>{" "}
                <a href={u.url} target="_blank" rel="noopener noreferrer"
                  className="text-[#4ade80] hover:text-[#6ee7b0] underline break-all">
                  {u.title || u.url || "—"}
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
      {preview.sources_to_digest && preview.sources_to_digest.length > 0 && (
        <div>
          <div className="text-[#555] text-[9px] mb-1 uppercase font-mono">sources to digest ({preview.sources_to_digest.length})</div>
          <div className="space-y-1.5 max-h-60 overflow-y-auto">
            {preview.sources_to_digest.map((s, i) => (
              <div key={i} className="text-[#94a3b8] text-[9px] pl-2 border-l border-[#222] leading-relaxed">
                <div className="flex gap-1.5 items-center">
                  <span className="text-[#555]">{i+1}.</span>
                  <a href={s.url} target="_blank" rel="noopener noreferrer"
                    className="text-[#4ade80] hover:text-[#6ee7b0] underline break-all font-semibold">
                    {s.title || s.url || "—"}
                  </a>
                </div>
                {s.snippet && (
                  <div className="text-[#777] text-[8px] pl-4 mt-0.5 leading-normal italic">
                    {s.snippet}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      {preview.phase === "reflecting" && (
        <div className="space-y-3">
          <div>
            <div className="text-[#555] text-[9px] uppercase font-mono mb-1">consolidation details</div>
            <KeyValueGrid items={[
              { key: "findings to consolidate", value: preview.findings_count ?? 0 },
              { key: "current depth", value: preview.current_depth ?? 0 },
              { key: "max depth", value: preview.max_depth ?? 0 },
              { key: "max consolidation rounds", value: preview.max_rounds ?? 0 },
            ]} />
          </div>

          {preview.parsed_urls && preview.parsed_urls.length > 0 && (
            <div>
              <div className="text-[#555] text-[9px] mb-1 uppercase font-mono">visited/parsed urls ({preview.parsed_urls.length})</div>
              <div className="space-y-0.5 max-h-36 overflow-y-auto pr-1 border border-[#1a1a1a] p-2 bg-[#080808]/30">
                {preview.parsed_urls.map((u, i) => {
                  const statusColor = u.status === "ok"
                    ? "#4ade80"
                    : u.status?.startsWith("failed")
                      ? "#ef4444"
                      : "#f59e0b"
                  return (
                    <div key={i} className="text-[#94a3b8] text-[9px] pl-2 border-l border-[#222] leading-relaxed flex items-center justify-between gap-2 max-w-full">
                      <div className="truncate flex-1 min-w-0">
                        <span className="text-[#555]">{i+1}.</span>{" "}
                        <a href={u.url} target="_blank" rel="noopener noreferrer"
                          className="text-[#4ade80] hover:text-[#6ee7b0] underline">
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
              <div className="text-[#555] text-[9px] mb-1 uppercase font-mono">accumulated findings ({preview.accumulated_findings.length})</div>
              <div className="space-y-0.5 max-h-48 overflow-y-auto pr-1 border border-[#1a1a1a] p-2 bg-[#080808]/30">
                {preview.accumulated_findings.map((f, i) => (
                  <div key={i} className="text-[#94a3b8] text-[9px] pl-2 border-l border-[#222] leading-relaxed">
                    <span className="text-[#555]">{i+1}.</span> {f}
                  </div>
                ))}
              </div>
            </div>
          )}

          {preview.digest_signals && (
            <div className="space-y-2">
              {preview.digest_signals.gaps && preview.digest_signals.gaps.length > 0 && (
                <div>
                  <div className="text-[#555] text-[9px] mb-1 uppercase font-mono">gaps to consolidate ({preview.digest_signals.gaps.length})</div>
                  <div className="space-y-0.5 max-h-32 overflow-y-auto pr-1 border border-[#1a1a1a] p-2 bg-[#080808]/30">
                    {preview.digest_signals.gaps.map((g, i) => (
                      <div key={i} className="text-[#f59e0b] text-[9px] pl-2 border-l border-[#222] leading-relaxed">
                        ◇ {g}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {preview.digest_signals.followups && preview.digest_signals.followups.length > 0 && (
                <div>
                  <div className="text-[#555] text-[9px] mb-1 uppercase font-mono">followups ({preview.digest_signals.followups.length})</div>
                  <div className="space-y-0.5 max-h-32 overflow-y-auto pr-1 border border-[#1a1a1a] p-2 bg-[#080808]/30">
                    {preview.digest_signals.followups.map((f, i) => (
                      <div key={i} className="text-[#a78bfa] text-[9px] pl-2 border-l border-[#222] leading-relaxed">
                        → {f}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
      {preview.phase === "evaluating" && (
        <div className="space-y-3">
          {/* Path indicator — hard rule or LLM */}
          {preview.eval_path && (
            <div className="flex items-center gap-2">
              <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded-sm border ${
                preview.eval_path === "hard_stop"
                  ? "text-[#ef4444] border-[#ef4444]/30 bg-[#ef4444]/5"
                  : preview.eval_path === "hard_continue"
                  ? "text-[#4ade80] border-[#4ade80]/30 bg-[#4ade80]/5"
                  : "text-[#f59e0b] border-[#f59e0b]/30 bg-[#f59e0b]/5"
              }`}>
                {preview.eval_path === "hard_stop" ? "■ HARD STOP" :
                 preview.eval_path === "hard_continue" ? "▶ HARD CONTINUE" :
                 "⚖ LLM BORDERLINE"}
              </span>
              <span className="text-[#555] text-[9px]">{preview.eval_path_reason}</span>
            </div>
          )}

          {/* Metrics */}
          <div>
            <div className="text-[#555] text-[9px] uppercase font-mono mb-1">evaluation metrics</div>
            <KeyValueGrid items={[
              { key: "current depth", value: `${preview.current_depth ?? 0} / ${preview.max_depth ?? 0}` },
              { key: "sources analyzed", value: preview.sources_analyzed ?? 0 },
              { key: "stagnation counter", value: preview.stagnation_counter ?? 0 },
            ]} />
          </div>

          {/* Completeness vs threshold */}
          <div>
            <div className="text-[#555] text-[9px] uppercase font-mono mb-1">completeness score</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 bg-[#1a1a1a] rounded-sm overflow-hidden relative">
                <div
                  className="h-full bg-[#4ade80] rounded-sm transition-all"
                  style={{ width: `${Math.round((preview.completeness_score ?? 0) * 100)}%` }}
                />
                {/* threshold marker */}
                {preview.satisfaction_threshold != null && (
                  <div
                    className="absolute top-0 bottom-0 w-px bg-[#f59e0b]"
                    style={{ left: `${Math.round(preview.satisfaction_threshold * 100)}%` }}
                    title={`threshold: ${Math.round(preview.satisfaction_threshold * 100)}%`}
                  />
                )}
              </div>
              <span className="text-[#4ade80] text-[9px] font-mono shrink-0">
                {Math.round((preview.completeness_score ?? 0) * 100)}%
                {preview.satisfaction_threshold != null && (
                  <span className="text-[#555]"> / {Math.round(preview.satisfaction_threshold * 100)}%</span>
                )}
              </span>
            </div>
            {preview.eval_path === "llm_borderline" && (
              <div className="text-[#f59e0b] text-[8px] mt-0.5 font-mono">
                ↑ in borderline zone — LLM evaluator will decide stop vs continue
              </div>
            )}
          </div>

          {/* Consolidation context passed to evaluator */}
          {preview.key_insights && preview.key_insights.length > 0 && (
            <details open>
              <summary className="text-[#4ade80] text-[9px] cursor-pointer hover:text-[#6ee7b0] font-mono">
                key insights ({preview.key_insights.length})
              </summary>
              <div className="mt-1 space-y-0.5 max-h-32 overflow-y-auto pr-1 border border-[#1a1a1a] p-1.5 bg-[#080808]/30">
                {preview.key_insights.map((ins: string, i: number) => (
                  <div key={i} className="text-[#94a3b8] text-[9px] pl-2 border-l border-[#1a3a1a] leading-relaxed">✓ {ins}</div>
                ))}
              </div>
            </details>
          )}

          {preview.remaining_gaps && preview.remaining_gaps.length > 0 && (
            <details open>
              <summary className="text-[#f59e0b] text-[9px] cursor-pointer hover:text-[#fbbf24] font-mono">
                remaining gaps ({preview.remaining_gaps.length})
              </summary>
              <div className="mt-1 space-y-0.5 max-h-28 overflow-y-auto pr-1 border border-[#1a1a1a] p-1.5 bg-[#080808]/30">
                {preview.remaining_gaps.map((g: string, i: number) => (
                  <div key={i} className="text-[#888] text-[9px] pl-2 border-l border-[#222] leading-relaxed">◇ {g}</div>
                ))}
              </div>
            </details>
          )}

          {preview.next_queries && preview.next_queries.length > 0 && (
            <details>
              <summary className="text-[#94a3b8] text-[9px] cursor-pointer hover:text-[#c4b5fd] font-mono">
                proposed next queries ({preview.next_queries.length})
              </summary>
              <div className="mt-1 space-y-0.5 pl-2">
                {preview.next_queries.map((q: string, i: number) => (
                  <div key={i} className="text-[#94a3b8] text-[9px] leading-relaxed">· {q}</div>
                ))}
              </div>
            </details>
          )}

          {preview.next_direct_urls && preview.next_direct_urls.length > 0 && (
            <details>
              <summary className="text-[#94a3b8] text-[9px] cursor-pointer hover:text-[#c4b5fd] font-mono">
                proposed direct URLs ({preview.next_direct_urls.length})
              </summary>
              <div className="mt-1 space-y-0.5 pl-2">
                {preview.next_direct_urls.map((u: string, i: number) => (
                  <div key={i} className="text-[9px]">
                    <a href={u} target="_blank" rel="noopener noreferrer"
                       className="text-[#4ade80] hover:text-[#6ee7b0] underline break-all">{u}</a>
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Show prompts only for LLM borderline mode */}
          {preview.eval_path === "llm_borderline" && preview.system_prompt && (
            <JsonBlock
              data={preview.system_prompt}
              variant="prompt"
              maxHeight="max-h-[300px]"
              collapsible={true}
              defaultCollapsed={true}
              label="evaluator system prompt"
            />
          )}
          {preview.eval_path === "llm_borderline" && preview.user_prompt && (
            <JsonBlock
              data={preview.user_prompt}
              variant="prompt"
              maxHeight="max-h-[350px]"
              collapsible={true}
              defaultCollapsed={false}
              label="evaluator user prompt"
            />
          )}
        </div>
      )}
      {preview.phase === "synthesizing" && (
        <div className="space-y-3">
          <div>
            <div className="text-[#555] text-[9px] uppercase font-mono mb-1">synthesis context</div>
            <KeyValueGrid items={[
              { key: "accumulated findings", value: preview.findings_count ?? 0 },
              { key: "sources analyzed", value: preview.sources_count ?? 0 },
            ]} />
          </div>

          {preview.sources && preview.sources.length > 0 && (
            <details>
              <summary className="text-[#4ade80] text-[9px] cursor-pointer hover:text-[#6ee7b0] font-mono">
                sources consulted ({preview.sources.length})
              </summary>
              <div className="mt-1 space-y-0.5 max-h-36 overflow-y-auto pr-1 border border-[#1a1a1a] p-2 bg-[#080808]/30">
                {preview.sources.map((u, i) => (
                  <div key={i} className="text-[#94a3b8] text-[9px] pl-2 border-l border-[#222] leading-relaxed flex items-center justify-between gap-2 max-w-full">
                    <div className="truncate flex-1 min-w-0">
                      <span className="text-[#555]">{i+1}.</span>{" "}
                      <a href={u.url} target="_blank" rel="noopener noreferrer"
                        className="text-[#4ade80] hover:text-[#6ee7b0] underline">
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
              <summary className="text-[#94a3b8] text-[9px] cursor-pointer hover:text-[#cbd5e1] font-mono">
                accumulated findings ({preview.findings.length})
              </summary>
              <div className="mt-1 space-y-0.5 max-h-48 overflow-y-auto pr-1 border border-[#1a1a1a] p-2 bg-[#080808]/30">
                {preview.findings.map((f, i) => (
                  <div key={i} className="text-[#94a3b8] text-[9px] pl-2 border-l border-[#222] leading-relaxed">
                    <span className="text-[#555]">{i+1}.</span> {f}
                  </div>
                ))}
              </div>
            </details>
          )}

          {preview.reflection && (
            <>
              {preview.reflection.key_insights && preview.reflection.key_insights.length > 0 && (
                <details>
                  <summary className="text-[#4ade80] text-[9px] cursor-pointer hover:text-[#6ee7b0] font-mono">
                    stabilized key insights ({preview.reflection.key_insights.length})
                  </summary>
                  <div className="mt-1 space-y-0.5 max-h-32 overflow-y-auto pr-1 border border-[#1a1a1a] p-1.5 bg-[#080808]/30">
                    {preview.reflection.key_insights.map((ins: string, i: number) => (
                      <div key={i} className="text-[#94a3b8] text-[9px] pl-2 border-l border-[#1a3a1a] leading-relaxed">✓ {ins}</div>
                    ))}
                  </div>
                </details>
              )}

              {preview.reflection.remaining_gaps && preview.reflection.remaining_gaps.length > 0 && (
                <details>
                  <summary className="text-[#f59e0b] text-[9px] cursor-pointer hover:text-[#fbbf24] font-mono">
                    remaining gaps ({preview.reflection.remaining_gaps.length})
                  </summary>
                  <div className="mt-1 space-y-0.5 max-h-28 overflow-y-auto pr-1 border border-[#1a1a1a] p-1.5 bg-[#080808]/30">
                    {preview.reflection.remaining_gaps.map((g: string, i: number) => (
                      <div key={i} className="text-[#888] text-[9px] pl-2 border-l border-[#222] leading-relaxed">◇ {g}</div>
                    ))}
                  </div>
                </details>
              )}
            </>
          )}
        </div>
      )}
      {preview.note && (
        <div className="text-[#444] italic text-[9px]">{preview.note}</div>
      )}
    </div>
  )
})
