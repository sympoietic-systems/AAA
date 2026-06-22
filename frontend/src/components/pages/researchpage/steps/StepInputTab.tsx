import React, { memo } from "react"
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
  const phaseLabel = (PHASE_LABELS[stepPhase] || stepPhase).toLowerCase()

  return (
    <div className="space-y-3">
      {/* ── Parse input: URLs to fetch ── */}
      {isParse && parentInputUrls && parentInputUrls.length > 0 && (
        <div>
          <div className="text-[#555] text-[9px] mb-1 uppercase">
            urls to parse ({parentInputUrls.length})
          </div>
          <div className="space-y-0.5 max-h-48 overflow-y-auto">
            {parentInputUrls.map((u, i) => (
              <div key={i} className="text-[#94a3b8] text-[9px] pl-2 border-l border-[#222] leading-relaxed">
                <span className="text-[#555]">{i+1}.</span>{" "}
                <a href={u.url} target="_blank" rel="noopener noreferrer"
                  className="text-[#4ade80] hover:text-[#6ee7b0] underline break-all">
                  {u.title || u.url?.slice(0, 100) || "—"}
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
      {isParse && (!parentInputUrls || parentInputUrls.length === 0) && (
        <div className="text-[#444] italic text-[9px]">no urls from previous search step</div>
      )}

      {/* ── Digest input: pages to analyze ── */}
      {isDigest && parentInputUrls && parentInputUrls.length > 0 && (
        <div>
          <div className="text-[#555] text-[9px] mb-1 uppercase">
            pages to digest ({parentInputUrls.length})
          </div>
          <div className="space-y-0.5 max-h-48 overflow-y-auto">
            {parentInputUrls.map((u, i) => {
              const errorMsg = u.error
              const st = errorMsg
                ? { icon: "✗", label: errorMsg.toLowerCase().replace("error: ", ""), color: "#ef4444" }
                : parseStatus(u.content_preview)
              return (
                <div key={i} className="text-[#94a3b8] text-[9px] pl-2 border-l border-[#222] leading-relaxed flex items-center justify-between gap-2 max-w-full">
                  <div className="truncate flex-1 min-w-0">
                     <span className="text-[#555]">{i+1}.</span>{" "}
                     <a href={u.url} target="_blank" rel="noopener noreferrer"
                       className="text-[#4ade80] hover:text-[#6ee7b0] underline">
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
        <div className="text-[#444] italic text-[9px]">no parsed pages from previous parse step</div>
      )}

      {/* ── Live input preview (for LLM steps: plan/search/reflect/digest/synthesize) ── */}
      {stepPhase && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <div className="text-[#555] text-[9px]">live input preview ({phaseLabel})</div>
            <button onClick={reinitLiveInput} disabled={reinitLoading}
              className="text-[#4ade80] hover:text-[#6ee7b0] text-[9px] font-mono disabled:text-[#333] cursor-pointer">
              [{reinitLoading ? "…" : "⟳ reinitialize"}]
            </button>
          </div>
          {reinitLoading ? (
            <div className="text-[#555] text-[9px] animate-pulse">regenerating…</div>
          ) : liveInput ? (
            <div className="space-y-2">
              {liveInput.objective && <div><div className="text-[#555] text-[8px]">objective:</div><div className="text-[#94a3b8] text-[9px] pl-2">{liveInput.objective}</div></div>}
              {liveInput.max_depth != null && <div className="flex gap-3 text-[#777] text-[9px] flex-wrap"><span>depth:{liveInput.max_depth}</span><span>budget:${liveInput.budget_limit_usd?.toFixed(2)}</span>{liveInput.model && <span>model:{liveInput.model}</span>}{liveInput.temperature != null && <span>temp:{liveInput.temperature}</span>}</div>}
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
              {liveInput.pending_queries && liveInput.pending_queries.length > 0 && <div><div className="text-[#555] text-[8px] mb-0.5">queries:</div>{liveInput.pending_queries.map((q,i)=><div key={i} className="text-[#94a3b8] text-[9px] pl-2">· {q}</div>)}</div>}
              {stepPhase === "reflecting" && (
                <div className="space-y-3 border-t border-[#1a1a1a] pt-2 mt-2">
                  {liveInput.parsed_urls && liveInput.parsed_urls.length > 0 && (
                    <div>
                      <div className="text-[#555] text-[8px] mb-1 uppercase font-mono font-semibold">visited/parsed urls ({liveInput.parsed_urls.length})</div>
                      <div className="space-y-0.5 max-h-36 overflow-y-auto pr-1 border border-[#1a1a1a] p-2 bg-[#080808]/30">
                        {liveInput.parsed_urls.map((u, i) => {
                          const statusColor = u.status === "ok"
                            ? "#4ade80"
                            : u.status?.startsWith("failed")
                              ? "#ef4444"
                              : "#f59e0b"
                          return (
                            <div key={i} className="text-[#94a3b8] text-[8px] pl-2 border-l border-[#222] leading-relaxed flex items-center justify-between gap-2 max-w-full">
                              <div className="truncate flex-1 min-w-0">
                                <span className="text-[#555]">{i+1}.</span>{" "}
                                <a href={u.url} target="_blank" rel="noopener noreferrer"
                                  className="text-[#4ade80] hover:text-[#6ee7b0] underline">
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
                      <div className="text-[#555] text-[8px] mb-1 uppercase font-mono font-semibold">accumulated findings ({liveInput.accumulated_findings.length})</div>
                      <div className="space-y-0.5 max-h-48 overflow-y-auto pr-1 border border-[#1a1a1a] p-2 bg-[#080808]/30">
                        {liveInput.accumulated_findings.map((f, i) => (
                          <div key={i} className="text-[#94a3b8] text-[8px] pl-2 border-l border-[#222] leading-relaxed">
                            <span className="text-[#555]">{i+1}.</span> {f}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {liveInput.digest_signals && (
                    <div className="space-y-2">
                      {liveInput.digest_signals.gaps && liveInput.digest_signals.gaps.length > 0 && (
                        <div>
                          <div className="text-[#555] text-[8px] mb-1 uppercase font-mono font-semibold">gaps to consolidate ({liveInput.digest_signals.gaps.length})</div>
                          <div className="space-y-0.5 max-h-32 overflow-y-auto pr-1 border border-[#1a1a1a] p-2 bg-[#080808]/30">
                            {liveInput.digest_signals.gaps.map((g, i) => (
                              <div key={i} className="text-[#f59e0b] text-[8px] pl-2 border-l border-[#222] leading-relaxed">
                                ◇ {g}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {liveInput.digest_signals.followups && liveInput.digest_signals.followups.length > 0 && (
                        <div>
                          <div className="text-[#555] text-[8px] mb-1 uppercase font-mono font-semibold">followups ({liveInput.digest_signals.followups.length})</div>
                          <div className="space-y-0.5 max-h-32 overflow-y-auto pr-1 border border-[#1a1a1a] p-2 bg-[#080808]/30">
                            {liveInput.digest_signals.followups.map((f, i) => (
                              <div key={i} className="text-[#a78bfa] text-[8px] pl-2 border-l border-[#222] leading-relaxed">
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
              {liveInput.note && <div className="text-[#444] italic text-[8px]">{liveInput.note}</div>}
            </div>
          ) : (
            <div className="text-[#444] italic text-[9px]">click reinitialize to load</div>
          )}
        </div>
      )}

      {/* ── Logged inputs (prompts from meta-log) ── */}
      {inputEntries.length > 0 && (
        <div>
          <div className="text-[#444] uppercase text-[8px] mb-1 tracking-wider">logged inputs ({inputEntries.length}):</div>
          <LogEntries entries={inputEntries} loading={false} emptyMsg="" />
        </div>
      )}
      {inputEntries.length === 0 && !stepPhase && !(isParse || isDigest) && (
        <div className="text-[#444] italic text-[9px]">no input data for this step</div>
      )}
    </div>
  )
})
