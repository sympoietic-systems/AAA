import { memo } from "react"
import type { StepPreview } from "../../../../api/research"
import { JsonBlock } from "../../../UI"
import { LogEntries } from "./LogEntries"
import { parseStatus } from "./StepResultTab"
import { PHASE_LABELS } from "../constants/taskConstants"

interface StepInputTabProps {
  stepPhase: string
  liveInput: StepPreview | null
  reinitLoading: boolean
  reinitLiveInput: () => void
  inputEntries: any[]
  /** URLs from the previous step (search → parse, parse → digest) */
  parentInputUrls?: { url: string; title: string; error?: string; raw_file_path?: string | null; content_preview?: string }[]
  /** The current step's type */
  stepType?: string
}

export const StepInputTab = memo(function StepInputTab({
  stepPhase, liveInput, reinitLoading, reinitLiveInput, inputEntries,
  parentInputUrls, stepType,
}: StepInputTabProps) {
  const isParse = stepType === "parallel_parse"
  const isDigest = stepType === "digest"
  const isDocDigest = stepType === "document_digestion"
  const phaseLabel = (PHASE_LABELS[stepPhase] || stepPhase).toLowerCase()

  return (
    <div className="space-y-3">
      {/* ── Document Digestion input: doc summary + chunks ── */}
      {isDocDigest && (
        <div className="space-y-3">
          {!liveInput ? (
            <div className="text-ui-dim italic text-[9px] font-mono">click reinitialize to load document preview</div>
          ) : (
            <>
          {liveInput.file_id && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-semantic-purple text-[8px] font-mono px-1 py-0.5 bg-semantic-purple/10 border border-semantic-purple/30 rounded-sm">
                file
              </span>
              <span className="text-ui-secondary text-[9px] truncate">{liveInput.file_id}</span>
            </div>
          )}
          {liveInput?.mode && (
            <div className="flex items-center gap-2 text-ui-dim text-[9px] font-mono">
              <span className="text-ui-dim">mode:</span>
              <span className="text-ui-secondary">{liveInput.mode}</span>
              {liveInput.mode === "chunks" && liveInput.chunk_limit != null && (
                <span className="text-ui-dim">(top {liveInput.chunk_limit} chunks)</span>
              )}
              {liveInput.mode === "full" && (
                <span className="text-ui-dim">(entire document)</span>
              )}
            </div>
          )}
          {liveInput?.objective && (
            <div>
              <div className="text-ui-dim text-[8px] uppercase mb-0.5 font-mono">objective</div>
              <div className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">{liveInput.objective}</div>
            </div>
          )}
          {liveInput?.doc_summary && (
            <div>
              <div className="text-ui-dim text-[8px] uppercase mb-0.5 font-mono">document summary</div>
              <div className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed max-h-32 overflow-y-auto">
                {liveInput.doc_summary}
              </div>
            </div>
          )}
          {liveInput?.mode === "chunks" && liveInput?.doc_chunks && liveInput.doc_chunks.length > 0 && (
            <div>
              <div className="text-ui-dim text-[8px] uppercase mb-1 font-mono">
                top chunks ({liveInput.doc_chunks.length})
              </div>
              <div className="space-y-1 border border-ui-border p-2 bg-[#080808]/30 max-h-64 overflow-y-auto">
                {liveInput.doc_chunks.map((chunk, i) => {
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
          {liveInput?.mode === "full" && liveInput?.doc_chunks && liveInput.doc_chunks.length > 0 && (
            <div>
              <div className="text-ui-dim text-[8px] uppercase mb-1 font-mono">
                document text ({liveInput.doc_chunks.length} chunks)
              </div>
              <div className="border border-ui-border p-2 bg-[#080808]/30 max-h-64 overflow-y-auto">
                <div className="text-ui-secondary text-[8px] whitespace-pre-wrap break-all leading-relaxed">
                  {liveInput.doc_chunks.map(c => c.content).join("\n\n").slice(0, 1500)}
                  {liveInput.doc_chunks.reduce((acc, c) => acc + c.content.length, 0) > 1500 ? "…" : ""}
                </div>
              </div>
            </div>
          )}
          </>
          )}
          <div className="text-ui-dim italic text-[9px] font-mono border-t border-ui-border pt-2">
            {liveInput?.doc_chunks && liveInput.doc_chunks.length > 0
              ? `${liveInput.doc_chunks.length} chunks will be combined and analyzed via LLM`
              : "no document chunks available"}
          </div>
        </div>
      )}
      {/* ── Parse input: URLs to fetch ── */}
      {isParse && parentInputUrls && parentInputUrls.length > 0 && (
        <div>
          <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">
            urls to parse ({parentInputUrls.length})
          </div>
          <div className="space-y-0.5 max-h-48 overflow-y-auto">
            {parentInputUrls.map((u, i) => (
              <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                <span className="text-ui-dim">{i+1}.</span>{" "}
                <a href={u.url} target="_blank" rel="noopener noreferrer"
                  className="text-action-dim hover:text-action-hover underline break-all font-mono transition-colors">
                  {u.title || u.url?.slice(0, 100) || "—"}
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
      {isParse && (!parentInputUrls || parentInputUrls.length === 0) && (
        <div className="text-ui-dim italic text-[9px] font-mono">no urls from previous search step</div>
      )}

      {/* ── Digest input: pages to analyze ── */}
      {isDigest && parentInputUrls && parentInputUrls.length > 0 && (
        <div>
          <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">
            pages to digest ({parentInputUrls.length})
          </div>
          <div className="space-y-0.5 max-h-48 overflow-y-auto">
            {parentInputUrls.map((u, i) => {
              const errorMsg = u.error
              const st = errorMsg
                ? { icon: "✗", label: errorMsg.toLowerCase().replace("error: ", ""), color: "#b86a6a" }
                : parseStatus(u.content_preview)
              return (
                <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed flex items-center justify-between gap-2 max-w-full">
                  <div className="truncate flex-1 min-w-0">
                     <span className="text-ui-dim">{i+1}.</span>{" "}
                     <a href={u.url} target="_blank" rel="noopener noreferrer"
                       className="text-action-dim hover:text-action-hover underline font-mono transition-colors">
                       {u.title || u.url?.slice(0, 100) || "—"}
                     </a>
                  </div>
                  <span style={{ color: st.color }} className="text-[8px] font-mono shrink-0 select-none">
                    [{st.label}]
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
      {isDigest && (!parentInputUrls || parentInputUrls.length === 0) && (
        <div className="text-ui-dim italic text-[9px] font-mono">no parsed pages from previous parse step</div>
      )}

      {/* ── Live input preview (for LLM steps: plan/search/reflect/digest/synthesize) ── */}
      {stepPhase && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <div className="text-ui-dim text-[9px] font-mono">live input preview ({phaseLabel})</div>
            <button onClick={reinitLiveInput} disabled={reinitLoading}
              className="text-action-dim hover:text-action-hover text-[9px] font-mono disabled:text-[#333] cursor-pointer transition-colors">
              [{reinitLoading ? "…" : "⟳ reinitialize"}]
            </button>
          </div>
          {reinitLoading ? (
            <div className="text-ui-dim text-[9px] animate-pulse font-mono">regenerating…</div>
          ) : liveInput ? (
            <div className="space-y-2">
              {liveInput.objective && <div><div className="text-ui-dim text-[8px] font-mono">objective:</div><div className="text-ui-secondary text-[9px] pl-2 font-mono">{liveInput.objective}</div></div>}
              {liveInput.max_depth != null && <div className="flex gap-3 text-ui-dim text-[9px] flex-wrap font-mono"><span>depth:{liveInput.max_depth}</span><span>budget:${liveInput.budget_limit_usd?.toFixed(2)}</span>{liveInput.model && <span>model:{liveInput.model}</span>}{liveInput.temperature != null && <span>temp:{liveInput.temperature}</span>}</div>}
              {liveInput.system_prompt && (
                <JsonBlock
                  data={liveInput.system_prompt}
                  variant="prompt"
                  maxHeight="max-h-[300px]"
                  collapsible={true}
                  defaultCollapsed={true}
                  label="system prompt"
                />
              )}
              {liveInput.user_prompt && (
                <JsonBlock
                  data={liveInput.user_prompt}
                  variant="prompt"
                  maxHeight="max-h-[300px]"
                  collapsible={true}
                  defaultCollapsed={false}
                  label="user prompt"
                />
              )}
              {liveInput.pending_queries && liveInput.pending_queries.length > 0 && <div><div className="text-ui-dim text-[8px] mb-0.5 font-mono">queries:</div>{liveInput.pending_queries.map((q,i)=><div key={i} className="text-ui-secondary text-[9px] pl-2 font-mono">· {q}</div>)}</div>}
              {stepPhase === "reflecting" && (
                <div className="space-y-3 border-t border-ui-border pt-2 mt-2">
                  {liveInput.parsed_urls && liveInput.parsed_urls.length > 0 && (
                    <div>
                      <div className="text-ui-dim text-[8px] mb-1 uppercase font-mono font-semibold">visited/parsed urls ({liveInput.parsed_urls.length})</div>
                      <div className="space-y-0.5 max-h-36 overflow-y-auto pr-1 border border-ui-border p-2 bg-[#080808]/30">
                        {liveInput.parsed_urls.map((u, i) => {
                          const statusColor = u.status === "ok"
                            ? "var(--color-semantic-green)"
                            : u.status?.startsWith("failed")
                              ? "var(--color-semantic-red)"
                              : "var(--color-semantic-gold)"
                          return (
                            <div key={i} className="text-ui-secondary text-[8px] pl-2 border-l border-ui-border leading-relaxed flex items-center justify-between gap-2 max-w-full">
                              <div className="truncate flex-1 min-w-0">
                                <span className="text-ui-dim">{i+1}.</span>{" "}
                                <a href={u.url} target="_blank" rel="noopener noreferrer"
                                  className="text-action-dim hover:text-action-hover underline font-mono transition-colors">
                                  {u.title || u.url}
                                </a>
                              </div>
                              {u.status && (
                                <span style={{ color: statusColor }} className="text-[7px] font-mono shrink-0 select-none">
                                  [{u.status}]
                                </span>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {liveInput.accumulated_findings && liveInput.accumulated_findings.length > 0 && (
                    <div>
                      <div className="text-ui-dim text-[8px] mb-1 uppercase font-mono font-semibold">accumulated findings ({liveInput.accumulated_findings.length})</div>
                      <div className="space-y-0.5 max-h-48 overflow-y-auto pr-1 border border-ui-border p-2 bg-[#080808]/30">
                        {liveInput.accumulated_findings.map((f, i) => (
                          <div key={i} className="text-ui-secondary text-[8px] pl-2 border-l border-ui-border leading-relaxed font-mono">
                            <span className="text-ui-dim">{i+1}.</span> {f}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {liveInput.digest_signals && (
                    <div className="space-y-2">
                      {liveInput.digest_signals.gaps && liveInput.digest_signals.gaps.length > 0 && (
                        <div>
                          <div className="text-ui-dim text-[8px] mb-1 uppercase font-mono font-semibold">gaps to consolidate ({liveInput.digest_signals.gaps.length})</div>
                          <div className="space-y-0.5 max-h-32 overflow-y-auto pr-1 border border-ui-border p-2 bg-[#080808]/30 font-mono">
                            {liveInput.digest_signals.gaps.map((g, i) => (
                              <div key={i} className="text-semantic-gold text-[8px] pl-2 border-l border-ui-border leading-relaxed">
                                ◇ {g}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {liveInput.digest_signals.followups && liveInput.digest_signals.followups.length > 0 && (
                        <div>
                          <div className="text-ui-dim text-[8px] mb-1 uppercase font-mono font-semibold">followups ({liveInput.digest_signals.followups.length})</div>
                          <div className="space-y-0.5 max-h-32 overflow-y-auto pr-1 border border-ui-border p-2 bg-[#080808]/30 font-mono">
                            {liveInput.digest_signals.followups.map((f, i) => (
                              <div key={i} className="text-semantic-purple text-[8px] pl-2 border-l border-ui-border leading-relaxed">
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
              {liveInput.note && <div className="text-ui-dim italic text-[8px] font-mono">{liveInput.note}</div>}
            </div>
          ) : (
            <div className="text-ui-dim italic text-[9px] font-mono">click reinitialize to load</div>
          )}
        </div>
      )}

      {/* ── Logged inputs (prompts from meta-log) ── */}
      {inputEntries.length > 0 && (
        <div>
          <div className="text-ui-dim uppercase text-[8px] mb-1 tracking-wider font-mono">logged inputs ({inputEntries.length}):</div>
          <LogEntries entries={inputEntries} loading={false} emptyMsg="" />
        </div>
      )}
      {inputEntries.length === 0 && !stepPhase && !(isParse || isDigest) && (
        <div className="text-ui-dim italic text-[9px] font-mono">no input data for this step</div>
      )}
    </div>
  )
})
