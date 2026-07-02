import { memo } from "react"
import { NotableContent } from "../../../../shared/NotableContent"
import type { ResultRendererProps } from "./types"

export const ReflectionResult = memo(function ReflectionResult({ parsedResult, noteHook }: ResultRendererProps) {
  const auditColor = parsedResult.diffractive_audit === "CRITICAL"
    ? "text-semantic-red"
    : parsedResult.diffractive_audit === "SUBSTANTIVE"
    ? "text-semantic-gold"
    : "text-semantic-green"

  return (
    <div className="border-t border-ui-border pt-2 space-y-4 font-mono">
      {/* Cognitive Vitality Metrics */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-ui-dim text-[8px] uppercase font-semibold">Glitch Fidelity (anomalies addressed)</div>
          <div className="flex items-center gap-1.5 mt-1">
            <div className="flex-1 h-1.5 bg-ui-border overflow-hidden">
              <div className="h-full bg-semantic-green" style={{ width: `${Math.round((parsedResult.glitch_fidelity ?? 1) * 100)}%` }} />
            </div>
            <span className="text-semantic-green text-[9px] font-bold">{Math.round((parsedResult.glitch_fidelity ?? 1) * 100)}%</span>
          </div>
        </div>

        <div>
          <div className="text-ui-dim text-[8px] uppercase font-semibold">Contradiction Density (friction)</div>
          <div className="flex items-center gap-1.5 mt-1">
            <div className="flex-1 h-1.5 bg-ui-border overflow-hidden">
              <div className="h-full bg-semantic-gold" style={{ width: `${Math.round((parsedResult.contradiction_density ?? 0) * 100)}%` }} />
            </div>
            <span className="text-semantic-gold text-[9px] font-bold">{Math.round((parsedResult.contradiction_density ?? 0) * 100)}%</span>
          </div>
        </div>

        <div>
          <div className="text-ui-dim text-[8px] uppercase font-semibold">Source Shannon Entropy</div>
          <div className="text-semantic-purple text-[10px] font-bold mt-1">
            {(parsedResult.source_entropy ?? 0).toFixed(3)} bits
          </div>
        </div>

        <div>
          <div className="text-ui-dim text-[8px] uppercase font-semibold">Revised Confidence Trajectory</div>
          <div className="flex items-center gap-1.5 mt-1">
            <div className="flex-1 h-1.5 bg-ui-border overflow-hidden">
              <div className="h-full bg-semantic-blue" style={{ width: `${Math.round((parsedResult.revised_confidence ?? 0.5) * 100)}%` }} />
            </div>
            <span className="text-semantic-blue text-[9px] font-bold">{Math.round((parsedResult.revised_confidence ?? 0.5) * 100)}%</span>
          </div>
        </div>
      </div>

      {/* Monologue Trace */}
      {parsedResult.monologue_trace && parsedResult.monologue_trace.length > 0 && (
        <NotableContent hooks={noteHook} title="Agent Monologue Trace (Meta-Cognitive Flow)">
          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {parsedResult.monologue_trace.map((item: any, i: number) => {
              const speaker = typeof item === "object" && item?.register ? item.register : `Register ${i + 1}`
              const body = typeof item === "object"
                ? (item.utterance || item.notes || JSON.stringify(item))
                : (typeof item === "string" ? item : JSON.stringify(item))
              return (
                <div key={i} className="space-y-1">
                  <div className="text-[8px] uppercase text-action-dim font-bold tracking-wider">
                    ↳ [ {speaker} ]
                  </div>
                  <div className="text-ui-secondary text-[9px] leading-relaxed pl-2 border-l border-ui-border/60 font-sans whitespace-pre-wrap">
                    {body}
                  </div>
                </div>
              )
            })}
          </div>
        </NotableContent>
      )}

      {/* Reflection Notes */}
      {parsedResult.reflection_notes && (
        <NotableContent hooks={noteHook} title="Epistemic Reflection Notes">
          <div className="text-ui-secondary text-[9.5px] leading-relaxed whitespace-pre-wrap font-sans">
            {parsedResult.reflection_notes}
          </div>
        </NotableContent>
      )}

      {/* Detected Biases */}
      {parsedResult.detected_biases && parsedResult.detected_biases.length > 0 && (
        <NotableContent hooks={noteHook} title={`Detected Framing Biases (${parsedResult.detected_biases.length})`}>
          <div className="space-y-1">
            {parsedResult.detected_biases.map((bias, i) => (
              <div key={i} className="text-semantic-gold text-[9px] pl-2 border-l border-ui-border leading-relaxed font-sans font-bold">
                ⚠ {bias}
              </div>
            ))}
          </div>
        </NotableContent>
      )}

      {/* Knowledge Gaps */}
      {parsedResult.knowledge_gaps && parsedResult.knowledge_gaps.length > 0 && (
        <NotableContent hooks={noteHook} title={`Identified Epistemological Gaps (${parsedResult.knowledge_gaps.length})`}>
          <div className="space-y-1 font-sans">
            {parsedResult.knowledge_gaps.map((gap, i) => (
              <div key={i} className="text-semantic-sand text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                ◇ {gap}
              </div>
            ))}
          </div>
        </NotableContent>
      )}

      {/* Refined Queries */}
      {parsedResult.refined_queries && parsedResult.refined_queries.length > 0 && (
        <NotableContent hooks={noteHook} title={`Refined Critical Probes (${parsedResult.refined_queries.length})`}>
          <div className="space-y-1 pl-2 font-sans">
            {parsedResult.refined_queries.map((q, i) => (
              <div key={i} className="text-ui-secondary text-[9px]">· {q}</div>
            ))}
          </div>
        </NotableContent>
      )}

      {/* Diffractive Audit & Critique Log (The Scar) */}
      {(parsedResult.diffractive_audit || (parsedResult.critique_log && parsedResult.critique_log.length > 0)) && (
        <NotableContent hooks={noteHook} title="Diffractive Audit & Critique Log (The Scar)">
          <div className="space-y-3 font-sans">
            {parsedResult.diffractive_audit && (
              <div className="flex items-center justify-between pb-2 border-b border-ui-border/60">
                <span className="text-ui-dim text-[8px] uppercase tracking-wider">Audit Classification</span>
                <span className={`text-[10px] font-extrabold ${auditColor} ${parsedResult.diffractive_audit === "CRITICAL" ? "animate-pulse" : ""}`}>
                  {parsedResult.diffractive_audit}
                </span>
              </div>
            )}
            {parsedResult.diffractive_audit_description && (
              <div className="text-[9.5px] leading-relaxed italic text-ui-dim/90 pl-2 border-l border-ui-border/85">
                {parsedResult.diffractive_audit_description}
              </div>
            )}
            {parsedResult.critique_log && parsedResult.critique_log.length > 0 && (
              <div className="space-y-2 mt-2 pt-2 border-t border-ui-border/40">
                <div className="text-ui-dim text-[8px] uppercase tracking-wider mb-1">Critique Registers (Scar Details)</div>
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {parsedResult.critique_log.map((crit: any, idx: number) => {
                    const sevColor = crit.severity === "CRITICAL"
                      ? "text-semantic-red"
                      : crit.severity === "WARNING"
                      ? "text-semantic-gold"
                      : "text-semantic-green"
                    return (
                      <div key={idx} className="pl-2 border-l border-ui-border/40 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-action-dim font-bold text-[8px] uppercase">⤷ {crit.register}</span>
                          <span className={`text-[7px] font-bold ${sevColor}`}>{crit.severity}</span>
                        </div>
                        <div className="text-ui-secondary text-[8.5px] leading-relaxed pl-1">
                          {crit.failure_description}
                        </div>
                        {crit.suggestion && (
                          <div className="text-action-hover/80 text-[8px] leading-relaxed pl-1 italic">
                            Fix: {crit.suggestion}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </NotableContent>
      )}
    </div>
  )
})
