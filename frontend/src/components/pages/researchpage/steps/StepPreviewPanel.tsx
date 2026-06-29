import { memo } from "react"
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
        <div className="text-semantic-header uppercase text-[9px] tracking-wider font-mono">
          [ {phaseLabel} — preview ]
        </div>
        <button onClick={onReinitialize} disabled={reinitLoading}
          className="text-action-dim hover:text-action-hover text-[9px] font-mono disabled:text-[#333] cursor-pointer transition-colors">
          [{reinitLoading ? "…" : "⟳ reinitialize"}]
        </button>
      </div>
      <div className="flex gap-3 border-b border-ui-border pb-1">
        <span className="text-ui-secondary text-[9px] uppercase font-mono">input / upcoming state</span>
      </div>
      {preview.objective && (
        <div>
          <div className="text-ui-dim text-[9px] mb-0.5 uppercase font-mono">objective:</div>
          <div className="text-ui-secondary pl-2 font-mono">{preview.objective}</div>
        </div>
      )}
      {preview.phase === "document_digestion" && (
        <div className="space-y-3 font-mono">
          {preview.file_id && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-semantic-purple text-[8px] font-mono px-1 py-0.5 bg-semantic-purple/10 border border-semantic-purple/30 rounded-sm">
                file
              </span>
              <span className="text-ui-secondary text-[9px] truncate">{preview.file_id}</span>
            </div>
          )}
          {preview.mode && (
            <div className="flex items-center gap-2 text-ui-dim text-[9px]">
              <span>mode:</span>
              <span className="text-ui-secondary">{preview.mode}</span>
              {preview.mode === "chunks" && preview.chunk_limit != null && (
                <span className="text-ui-dim">(top {preview.chunk_limit} chunks)</span>
              )}
              {preview.mode === "full" && (
                <span className="text-ui-dim">(entire document)</span>
              )}
            </div>
          )}
          {preview.doc_summary && (
            <div>
              <div className="text-ui-dim text-[9px] mb-0.5 uppercase font-mono">document summary</div>
              <div className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed max-h-32 overflow-y-auto">
                {preview.doc_summary}
              </div>
            </div>
          )}
          {preview.mode === "chunks" && preview.doc_chunks && preview.doc_chunks.length > 0 && (
            <div>
              <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">
                top chunks ({preview.doc_chunks.length})
              </div>
              <div className="space-y-1 border border-ui-border p-2 bg-[#080808]/30 max-h-64 overflow-y-auto">
                {preview.doc_chunks.map((chunk, i) => {
                  const simDisplay = chunk.sim > 0 ? ` (sim=${chunk.sim.toFixed(2)})` : ""
                  return (
                    <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                      <div className="text-ui-dim text-[8px] mb-0.5">chunk {i + 1}{simDisplay}</div>
                      <div className="whitespace-pre-wrap break-all text-[8px]">{chunk.content.slice(0, 500)}{chunk.content.length > 500 ? "…" : ""}</div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
          {preview.mode === "full" && preview.doc_chunks && preview.doc_chunks.length > 0 && (
            <div>
              <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">
                document text ({preview.doc_chunks.length} chunks)
              </div>
              <div className="border border-ui-border p-2 bg-[#080808]/30 max-h-64 overflow-y-auto">
                <div className="text-ui-secondary text-[8px] whitespace-pre-wrap break-all leading-relaxed">
                  {preview.doc_chunks.map(c => c.content).join("\n\n").slice(0, 1500)}
                  {preview.doc_chunks.reduce((acc, c) => acc + c.content.length, 0) > 1500 ? "…" : ""}
                </div>
              </div>
            </div>
          )}
          {(!preview.doc_chunks || preview.doc_chunks.length === 0) && (
            <div className="text-ui-dim italic text-[9px]">
              {preview.document_digested ? "document already digested" : "no document chunks available"}
            </div>
          )}
        </div>
      )}
      {preview.max_depth != null && (
        <div className="flex gap-4 text-ui-dim flex-wrap font-mono">
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
          <div className="text-ui-dim text-[9px] mb-0.5 uppercase font-mono">pending queries:</div>
          {preview.pending_queries.map((q, i) => (
            <div key={i} className="text-ui-secondary pl-2 font-mono">· {q}</div>
          ))}
        </div>
      )}
      {preview.urls_to_fetch && preview.urls_to_fetch.length > 0 && (
        <div>
          <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">urls to parse ({preview.urls_to_fetch.length})</div>
          <div className="space-y-0.5 max-h-48 overflow-y-auto">
            {preview.urls_to_fetch.map((u, i) => (
              <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                <span className="text-ui-dim">{i+1}.</span>{" "}
                <a href={u.url} target="_blank" rel="noopener noreferrer"
                  className="text-action-dim hover:text-action-hover underline break-all font-mono transition-colors">
                  {u.title || u.url || "—"}
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
      {preview.sources_to_digest && preview.sources_to_digest.length > 0 && (
        <div>
          <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">sources to digest ({preview.sources_to_digest.length})</div>
          <div className="space-y-1.5 max-h-60 overflow-y-auto">
            {preview.sources_to_digest.map((s, i) => (
              <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                <div className="flex gap-1.5 items-center">
                  <span className="text-ui-dim">{i+1}.</span>
                  <a href={s.url} target="_blank" rel="noopener noreferrer"
                    className="text-action-dim hover:text-action-hover underline break-all font-mono font-semibold transition-colors">
                    {s.title || s.url || "—"}
                  </a>
                </div>
                {s.snippet && (
                  <div className="text-ui-dim text-[8px] pl-4 mt-0.5 leading-normal italic font-mono">
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
              <div className="space-y-0.5 max-h-36 overflow-y-auto pr-1 border border-ui-border p-2 bg-[#080808]/30 font-mono">
                {preview.parsed_urls.map((u, i) => {
                  const statusColor = u.status === "ok"
                    ? "var(--color-semantic-green)"
                    : u.status?.startsWith("failed")
                      ? "var(--color-semantic-red)"
                      : "var(--color-semantic-gold)"
                  return (
                    <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed flex items-center justify-between gap-2 max-w-full">
                      <div className="truncate flex-1 min-w-0">
                        <span className="text-ui-dim">{i+1}.</span>{" "}
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
              <div className="space-y-0.5 max-h-48 overflow-y-auto pr-1 border border-ui-border p-2 bg-[#080808]/30 font-mono">
                {preview.accumulated_findings.map((f, i) => (
                  <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                    <span className="text-ui-dim">{i+1}.</span> {f}
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
                  <div className="space-y-0.5 max-h-32 overflow-y-auto pr-1 border border-ui-border p-2 bg-[#080808]/30 font-mono">
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
                  <div className="space-y-0.5 max-h-32 overflow-y-auto pr-1 border border-ui-border p-2 bg-[#080808]/30 font-mono">
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
      )}
      {preview.phase === "evaluating" && (
        <div className="space-y-3 font-mono">
          {/* Path indicator — hard rule or LLM */}
          {preview.eval_path && (
            <div className="flex items-center gap-2">
              <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded-sm border ${
                preview.eval_path === "hard_stop"
                  ? "text-semantic-red border-semantic-red/30 bg-semantic-red/5"
                  : preview.eval_path === "hard_continue"
                  ? "text-semantic-green border-semantic-green/30 bg-semantic-green/5"
                  : "text-semantic-gold border-semantic-gold/30 bg-semantic-gold/5"
              }`}>
                {preview.eval_path === "hard_stop" ? "■ HARD STOP" :
                 preview.eval_path === "hard_continue" ? "▶ HARD CONTINUE" :
                 "⚖ LLM BORDERLINE"}
              </span>
              <span className="text-ui-dim text-[9px]">{preview.eval_path_reason}</span>
            </div>
          )}

          {/* Metrics */}
          <div>
            <div className="text-ui-dim text-[9px] uppercase font-mono mb-1">evaluation metrics</div>
            <KeyValueGrid items={[
              { key: "current depth", value: `${preview.current_depth ?? 0} / ${preview.max_depth ?? 0}` },
              { key: "sources analyzed", value: preview.sources_analyzed ?? 0 },
              { key: "stagnation counter", value: preview.stagnation_counter ?? 0 },
            ]} />
          </div>

          {/* Completeness vs threshold */}
          <div>
            <div className="text-ui-dim text-[9px] uppercase font-mono mb-1">completeness score</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 bg-ui-border rounded-sm overflow-hidden relative">
                <div
                  className="h-full bg-semantic-green rounded-sm transition-all"
                  style={{ width: `${Math.round((preview.completeness_score ?? 0) * 100)}%` }}
                />
                {/* threshold marker */}
                {preview.satisfaction_threshold != null && (
                  <div
                    className="absolute top-0 bottom-0 w-px bg-semantic-gold"
                    style={{ left: `${Math.round(preview.satisfaction_threshold * 100)}%` }}
                    title={`threshold: ${Math.round(preview.satisfaction_threshold * 100)}%`}
                  />
                )}
              </div>
              <span className="text-semantic-green text-[9px] font-mono shrink-0">
                {Math.round((preview.completeness_score ?? 0) * 100)}%
                {preview.satisfaction_threshold != null && (
                  <span className="text-ui-dim"> / {Math.round(preview.satisfaction_threshold * 100)}%</span>
                )}
              </span>
            </div>
            {preview.eval_path === "llm_borderline" && (
              <div className="text-semantic-gold text-[8px] mt-0.5 font-mono">
                ↑ in borderline zone — LLM evaluator will decide stop vs continue
              </div>
            )}
          </div>

          {/* Consolidation context passed to evaluator */}
          {preview.key_insights && preview.key_insights.length > 0 && (
            <details open>
              <summary className="text-semantic-green text-[9px] cursor-pointer hover:text-semantic-green/80 font-mono transition-colors">
                key insights ({preview.key_insights.length})
              </summary>
              <div className="mt-1 space-y-0.5 max-h-32 overflow-y-auto pr-1 border border-ui-border p-1.5 bg-[#080808]/30">
                {preview.key_insights.map((ins: string, i: number) => (
                  <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">✓ {ins}</div>
                ))}
              </div>
            </details>
          )}

          {/* Remaining gaps */}
          {preview.remaining_gaps && preview.remaining_gaps.length > 0 && (
            <details open>
              <summary className="text-semantic-gold text-[9px] cursor-pointer hover:text-semantic-gold/80 font-mono transition-colors">
                remaining gaps ({preview.remaining_gaps.length})
              </summary>
              <div className="mt-1 space-y-0.5 max-h-28 overflow-y-auto pr-1 border border-ui-border p-1.5 bg-[#080808]/30">
                {preview.remaining_gaps.map((g: string, i: number) => (
                  <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed font-mono">◇ {g}</div>
                ))}
              </div>
            </details>
          )}

          {/* Proposed next queries */}
          {preview.next_queries && preview.next_queries.length > 0 && (
            <details>
              <summary className="text-ui-secondary text-[9px] cursor-pointer hover:text-ui-primary font-mono transition-colors">
                proposed next queries ({preview.next_queries.length})
              </summary>
              <div className="mt-1 space-y-0.5 pl-2">
                {preview.next_queries.map((q: string, i: number) => (
                  <div key={i} className="text-ui-secondary text-[9px] leading-relaxed">· {q}</div>
                ))}
              </div>
            </details>
          )}

          {/* Proposed direct URLs */}
          {preview.next_direct_urls && preview.next_direct_urls.length > 0 && (
            <details>
              <summary className="text-ui-secondary text-[9px] cursor-pointer hover:text-ui-primary font-mono transition-colors">
                proposed direct URLs ({preview.next_direct_urls.length})
              </summary>
              <div className="mt-1 space-y-0.5 pl-2">
                {preview.next_direct_urls.map((u: string, i: number) => (
                  <div key={i} className="text-[9px]">
                    <a href={u} target="_blank" rel="noopener noreferrer"
                       className="text-action-dim hover:text-action-hover underline break-all transition-colors">{u}</a>
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
              <div className="mt-1 space-y-0.5 max-h-36 overflow-y-auto pr-1 border border-ui-border p-2 bg-[#080808]/30">
                {preview.sources.map((u, i) => (
                  <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed flex items-center justify-between gap-2 max-w-full">
                    <div className="truncate flex-1 min-w-0">
                      <span className="text-ui-dim">{i+1}.</span>{" "}
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
              <div className="mt-1 space-y-0.5 max-h-48 overflow-y-auto pr-1 border border-ui-border p-2 bg-[#080808]/30">
                {preview.findings.map((f, i) => (
                  <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                    <span className="text-ui-dim">{i+1}.</span> {f}
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
                  <div className="mt-1 space-y-0.5 max-h-32 overflow-y-auto pr-1 border border-ui-border p-1.5 bg-[#080808]/30 font-mono">
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
                  <div className="mt-1 space-y-0.5 max-h-28 overflow-y-auto pr-1 border border-ui-border p-1.5 bg-[#080808]/30 font-mono">
                    {preview.reflection.remaining_gaps.map((g: string, i: number) => (
                      <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">◇ {g}</div>
                    ))}
                  </div>
                </details>
              )}
            </>
          )}
        </div>
      )}
      {preview.note && (
        <div className="text-ui-dim italic text-[9px] font-mono">{preview.note}</div>
      )}
    </div>
  )
})
