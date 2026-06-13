import { useState, useEffect, useRef } from "react"
import { updateBelief, deleteBelief, revertBelief, vetBeliefProposal, refineBeliefProposal } from "../../../../api/client"
import type { BeliefNodeInfo } from "../../../../api/client"
import { computeLineDiff } from "../../../../utils/diff"
import { StructuralAutopoieticGlyph } from "../../../UI/StructuralAutopoieticGlyph"

// Reuse category colors & helper methods from parent
function getCategoryColor(c: string) {
  switch (c?.toLowerCase()) {
    case "foundational": return "#4ade80"
    case "ontological": return "#a78bfa"
    case "methodological": return "#facc15"
    default: return "#60a5fa"
  }
}

function getStageColor(s: string) {
  switch (s) {
    case "nucleation": return "#f59e0b"
    case "accretion": return "#fb923c"
    case "crystallized": return "#4ade80"
    case "senescence": return "#94a3b8"
    case "collapsed": return "#ef4444"
    default: return "#6c6c8a"
  }
}

function getStageLabel(s: string) {
  switch (s) {
    case "nucleation": return "nucleating"
    case "accretion": return "accreting"
    case "crystallized": return "crystallized"
    case "senescence": return "senescing"
    case "collapsed": return "collapsed"
    case "faded": return "faded"
    default: return s
  }
}

interface BeliefDetailProps {
  belief: BeliefNodeInfo | null
  activeBeliefs: BeliefNodeInfo[]
  onUpdate: (updatedBelief: BeliefNodeInfo) => void
  onDelete: (beliefId: string) => void
  onReload?: () => void
  agentFlux: boolean
}

export function BeliefDetail({ belief, activeBeliefs = [], onUpdate, onDelete, onReload, agentFlux }: BeliefDetailProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editLabel, setEditLabel] = useState("")
  const [editStatement, setEditStatement] = useState("")
  const [editConfidence, setEditConfidence] = useState(0.5)
  const [editOntologicalMass, setEditOntologicalMass] = useState(0.5)
  const [editLifecycleStage, setEditLifecycleStage] = useState("crystallized")

  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false)
  const [isSavingOrDeleting, setIsSavingOrDeleting] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const [versions, setVersions] = useState<any[]>([])
  const [expandedVersions, setExpandedVersions] = useState<Record<number, boolean>>({})
  const [activeTab, setActiveTab] = useState<"metabolism" | "history">("metabolism")

  const [vetMode, setVetMode] = useState<"none" | "adopt" | "reject" | "merge">("none")
  const [adoptLabel, setAdoptLabel] = useState("")
  const [adoptStatement, setAdoptStatement] = useState("")
  const [rejectionRationale, setRejectionRationale] = useState("")
  const [targetBeliefId, setTargetBeliefId] = useState("")
  const [mergedStatement, setMergedStatement] = useState("")
  const [isRefining, setIsRefining] = useState(false)
  const [isVetting, setIsVetting] = useState(false)
  const workshopRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (vetMode !== "none" && workshopRef.current) {
      workshopRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" })
    }
  }, [vetMode])

  useEffect(() => {
    if (vetMode === "merge" && targetBeliefId) {
      if (targetBeliefId === belief.potential_merge_target && belief.statement) {
        setMergedStatement(belief.statement);
      } else {
        const tb = activeBeliefs.find(ab => ab.id === targetBeliefId);
        if (tb) {
          setMergedStatement(tb.statement);
        }
      }
    } else {
      setMergedStatement("");
    }
  }, [vetMode, targetBeliefId, activeBeliefs, belief])

  // Reset editing/confirming states and fetch versions when selected belief changes
  useEffect(() => {
    setIsEditing(false)
    setIsConfirmingDelete(false)
    setErrorMsg(null)
    setExpandedVersions({})
    setVetMode("none")
    setAdoptLabel("")
    setAdoptStatement("")
    setRejectionRationale("")
    setTargetBeliefId("")
    setMergedStatement("")
    setIsRefining(false)
    setIsVetting(false)

    if (!belief) {
      setVersions([])
      return
    }

    setVersions([])
    setActiveTab("metabolism")

    if (belief.is_proposal) {
      setAdoptLabel(belief.suggested_label || belief.label || "")
      setAdoptStatement(belief.suggested_statement || belief.statement || "")
      if (belief.potential_merge_target) {
        setTargetBeliefId(belief.potential_merge_target)
      } else if (activeBeliefs && activeBeliefs.length > 0) {
        setTargetBeliefId(activeBeliefs[0].id)
      }
      return
    }

    fetch(`/api/beliefs/${belief.id}/versions`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setVersions(data)
        }
      })
      .catch(e => console.error("Failed to load belief versions:", e))
  }, [belief, activeBeliefs])

  if (!belief) {
    return (
      <div className="flex-1 min-h-0 flex items-center justify-center border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50">
        <span className="text-[11px] text-[#444] italic font-mono">select a node to inspect</span>
      </div>
    )
  }

  const b = belief
  const catColor = getCategoryColor(b.category)
  const stage = b.lifecycle_stage || "crystallized"
  const stageColor = getStageColor(stage)
  const isProto = stage === "nucleation" || stage === "accretion"
  const isGhost = stage === "collapsed" || stage === "faded"

  let vec: number[] = []
  try { if (b.vector_16d) vec = JSON.parse(b.vector_16d) } catch { }

  const handleRefine = async () => {
    setIsRefining(true)
    setErrorMsg(null)
    try {
      const result = await refineBeliefProposal(b.id)
      if (result.status === "error") {
        setErrorMsg(result.message || "Failed to refine proposal")
      } else {
        if (onReload) {
          onReload()
        }
      }
    } catch (e: any) {
      setErrorMsg(e.message || String(e))
    } finally {
      setIsRefining(false)
    }
  }

  const handleVet = async (action: "adopt" | "reject" | "merge") => {
    setIsVetting(true)
    setErrorMsg(null)
    try {
      const payload: any = { action }
      if (action === "adopt") {
        if (!adoptLabel.trim()) {
          setErrorMsg("Suggested label is required for adoption")
          setIsVetting(false)
          return
        }
        if (!adoptStatement.trim()) {
          setErrorMsg("Suggested statement is required for adoption")
          setIsVetting(false)
          return
        }
        payload.suggested_label = adoptLabel.trim()
        payload.suggested_statement = adoptStatement.trim()
      } else if (action === "reject") {
        if (!rejectionRationale.trim()) {
          setErrorMsg("Rejection rationale is required")
          setIsVetting(false)
          return
        }
        payload.rejection_rationale = rejectionRationale.trim()
      } else if (action === "merge") {
        if (!targetBeliefId) {
          setErrorMsg("Please select a target belief to merge into")
          setIsVetting(false)
          return
        }
        payload.target_belief_id = targetBeliefId
        payload.merged_statement = mergedStatement.trim()
      }

      const result = await vetBeliefProposal(b.id, payload)
      if (result.status === "ok" || result.status === "success") {
        if (onReload) {
          onReload()
        }
      } else {
        setErrorMsg(result.message || `Failed to ${action} proposal`)
      }
    } catch (e: any) {
      setErrorMsg(e.message || String(e))
    } finally {
      setIsVetting(false)
    }
  }

  if (b.is_proposal) {
    const status = b.proposal_status || "pending"
    return (
      <div className="flex-1 min-h-0 flex flex-col overflow-y-auto pr-1.5 border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50 p-2.5 gap-2.5 text-[11px] font-sans">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#1f1f2e]/30 pb-1.5 shrink-0 font-mono">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-[11px] shrink-0 text-[#f59e0b]">◇</span>
            <span className="font-mono text-[11px] font-bold text-[#ccc] truncate">
              PROPOSAL: {b.label}
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0 ml-2">
            <span
              className={`text-[9px] uppercase font-mono px-1.5 py-px rounded border shrink-0 font-bold ${
                status === "pending"
                  ? "border-[#f59e0b]/40 text-[#f59e0b] bg-[#f59e0b]/10"
                  : status === "refined"
                  ? "border-[#a78bfa]/40 text-[#a78bfa] bg-[#a78bfa]/10"
                  : status === "rejected"
                  ? "border-[#ef4444]/40 text-[#ef4444] bg-[#ef4444]/10"
                  : "border-[#4ade80]/40 text-[#4ade80] bg-[#4ade80]/10"
              }`}
            >
              {status}
            </span>
          </div>
        </div>

        {errorMsg && (
          <div className="text-[10px] text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/20 p-1.5 rounded shrink-0 font-mono">
            {errorMsg}
          </div>
        )}

        {/* Provisional Statement */}
        <div className="shrink-0">
          <div className="text-[#555] font-mono text-[10px] uppercase font-bold">[ Provisional Statement ]</div>
          <div className="text-[#ccc] text-[11px] italic font-serif leading-relaxed mt-0.5">
            "{b.statement}"
          </div>
        </div>

        {/* Metadata grid */}
        <div className="shrink-0 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-mono text-[#888]">
          <div><span className="text-[#444]">Origin:</span> <span className="text-[#aaa]">emergent</span></div>
          <div><span className="text-[#444]">Mass:</span> <span className="text-[#aaa]">{b.ontological_mass.toFixed(3)}</span></div>
          <div><span className="text-[#444]">Confidence:</span> <span className="text-[#aaa]">{(b.confidence * 100).toFixed(0)}%</span></div>
          <div><span className="text-[#444]">Created At:</span> <span className="text-[#aaa]">{b.last_reinforced_at ? new Date(b.last_reinforced_at).toLocaleString() : ""}</span></div>
        </div>

        {/* Symbia's Reflection / Friction Rationale */}
        {b.symbia_reflection && (
          <div className="shrink-0 border border-[#a78bfa]/20 bg-[#a78bfa]/5 p-2 rounded text-[10.5px] leading-relaxed text-[#ccc] font-serif flex flex-col gap-2">
            <div>
              <div className="text-[#a78bfa] font-mono text-[9px] uppercase font-bold tracking-wider mb-0.5">[ Symbia's Reflection ]</div>
              {b.symbia_reflection}
              {b.symbia_friction_rationale && (
                <div className="mt-1.5 pt-1.5 border-t border-[#a78bfa]/10 text-[10px] text-[#fb7185] italic font-sans">
                  <span className="font-mono uppercase font-bold mr-1">[ Friction Warning ]:</span>
                  {b.symbia_friction_rationale}
                </div>
              )}
            </div>
            {agentFlux && (status === "pending" || status === "refined") && (() => {
              const recommendsRejection = !!b.symbia_reflection?.toLowerCase().includes("reject");
              const recommendsMerge = !recommendsRejection && !!b.potential_merge_target;
              const recommendsAdoption = !recommendsRejection && !b.potential_merge_target;
              
              const targetBelief = b.potential_merge_target
                ? activeBeliefs.find(ab => ab.id === b.potential_merge_target)
                : null;
              
              return (
                <div className="mt-1 flex flex-wrap gap-2 pt-2 border-t border-[#a78bfa]/10 font-mono text-[9.5px]">
                  {recommendsRejection && (
                    <>
                      <button
                        onClick={() => {
                          setVetMode("reject");
                          setRejectionRationale(b.symbia_reflection || "");
                        }}
                        className="px-2 py-1 border border-[#ef4444]/50 hover:border-[#ef4444]/80 bg-[#ef4444]/20 hover:bg-[#ef4444]/30 text-[#ef5f5f] transition-all cursor-pointer rounded font-bold uppercase tracking-wider"
                      >
                        [ Reject Proposal (Symbia Recommended) ]
                      </button>
                      {targetBelief ? (
                        <button
                          onClick={() => {
                            setVetMode("merge");
                            setTargetBeliefId(targetBelief.id);
                          }}
                          className="px-2 py-1 border border-[#facc15]/20 hover:border-[#facc15]/40 bg-[#facc15]/5 hover:bg-[#facc15]/10 text-[#facc15] transition-all cursor-pointer rounded font-bold uppercase tracking-wider"
                        >
                          [ Merge into: "{targetBelief.label}" ]
                        </button>
                      ) : (
                        <button
                          onClick={() => {
                            setVetMode("adopt");
                            setAdoptLabel(b.suggested_label || b.label || "");
                            setAdoptStatement(b.suggested_statement || b.statement || "");
                          }}
                          className="px-2 py-1 border border-[#4ade80]/20 hover:border-[#4ade80]/40 bg-[#4ade80]/5 hover:bg-[#4ade80]/10 text-[#4ade80] transition-all cursor-pointer rounded font-bold uppercase tracking-wider"
                        >
                          [ Adopt as: "{b.suggested_label || b.label}" ]
                        </button>
                      )}
                    </>
                  )}

                  {recommendsMerge && targetBelief && (
                    <>
                      <button
                        onClick={() => {
                          setVetMode("merge");
                          setTargetBeliefId(targetBelief.id);
                        }}
                        className="px-2 py-1 border border-[#facc15]/50 hover:border-[#facc15]/80 bg-[#facc15]/20 hover:bg-[#facc15]/30 text-[#facc15] transition-all cursor-pointer rounded font-bold uppercase tracking-wider"
                      >
                        [ Merge into: "{targetBelief.label}" (Symbia Recommended) ]
                      </button>
                      <button
                        onClick={() => {
                          setVetMode("adopt");
                          setAdoptLabel(b.suggested_label || b.label || "");
                          setAdoptStatement(b.suggested_statement || b.statement || "");
                        }}
                        className="px-2 py-1 border border-[#4ade80]/20 hover:border-[#4ade80]/40 bg-[#4ade80]/5 hover:bg-[#4ade80]/10 text-[#4ade80] transition-all cursor-pointer rounded font-bold uppercase tracking-wider"
                      >
                        [ Adopt as: "{b.suggested_label || b.label}" ]
                      </button>
                      <button
                        onClick={() => {
                          setVetMode("reject");
                          setRejectionRationale(b.symbia_reflection || "");
                        }}
                        className="px-2 py-1 border border-[#ef4444]/20 hover:border-[#ef4444]/40 bg-[#ef4444]/5 hover:bg-[#ef4444]/10 text-[#ef4444] transition-all cursor-pointer rounded font-bold uppercase tracking-wider"
                      >
                        [ Reject ]
                      </button>
                    </>
                  )}

                  {recommendsAdoption && (
                    <>
                      <button
                        onClick={() => {
                          setVetMode("adopt");
                          setAdoptLabel(b.suggested_label || b.label || "");
                          setAdoptStatement(b.suggested_statement || b.statement || "");
                        }}
                        className="px-2 py-1 border border-[#4ade80]/50 hover:border-[#4ade80]/80 bg-[#4ade80]/20 hover:bg-[#4ade80]/30 text-[#4ade80] transition-all cursor-pointer rounded font-bold uppercase tracking-wider"
                      >
                        [ Adopt Proposal (Symbia Recommended) ]
                      </button>
                      {targetBelief ? (
                        <button
                          onClick={() => {
                            setVetMode("merge");
                            setTargetBeliefId(targetBelief.id);
                          }}
                          className="px-2 py-1 border border-[#facc15]/20 hover:border-[#facc15]/40 bg-[#facc15]/5 hover:bg-[#facc15]/10 text-[#facc15] transition-all cursor-pointer rounded font-bold uppercase tracking-wider"
                        >
                          [ Merge into: "{targetBelief.label}" ]
                        </button>
                      ) : null}
                      <button
                        onClick={() => {
                          setVetMode("reject");
                          setRejectionRationale(b.symbia_reflection || "");
                        }}
                        className="px-2 py-1 border border-[#ef4444]/20 hover:border-[#ef4444]/40 bg-[#ef4444]/5 hover:bg-[#ef4444]/10 text-[#ef4444] transition-all cursor-pointer rounded font-bold uppercase tracking-wider"
                      >
                        [ Reject ]
                      </button>
                    </>
                  )}
                </div>
              );
            })()}
          </div>
        )}

        {/* Rejection Rationale */}
        {status === "rejected" && b.rejection_rationale && (
          <div className="shrink-0 border border-[#ef4444]/20 bg-[#ef4444]/5 p-2 rounded text-[10.5px] leading-relaxed text-[#ef4444]/90 font-serif">
            <div className="text-[#ef4444]/60 font-mono text-[9px] uppercase font-bold tracking-wider mb-0.5">[ Refusal Rationale ]</div>
            {b.rejection_rationale}
          </div>
        )}

        {/* Vector */}
        {vec.length > 0 && (
          <div className="shrink-0 mb-1">
            <div className="text-[#555] font-mono text-[10px] uppercase mb-1 font-bold">[ Initial Signature ]</div>
            <StructuralAutopoieticGlyph
              signature={vec}
              isStagnant={false}
            />
          </div>
        )}

        {/* Source Trace */}
        {b.source_trace && b.source_trace.length > 0 && (
          <div className="shrink-0">
            <div className="text-[#555] font-mono text-[10px] uppercase font-bold mb-1">[ Source Trace ]</div>
            <div className="space-y-1 max-h-[80px] overflow-y-auto pr-1">
              {b.source_trace.map((src: any, idx: number) => (
                <div key={idx} className="text-[#888] font-mono text-[9.5px]">
                  • <span className="text-[#6c6c8a]">{src.type}</span>: <span className="text-[#aaa]">{src.id}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Vetting Workshop section */}
        {agentFlux && (status === "pending" || status === "refined") && (
          <div ref={workshopRef} className="border-t border-[#1f1f2e]/20 pt-2 flex flex-col gap-2 mt-2">
            <div className="text-[#a78bfa] font-mono text-[10px] uppercase font-bold tracking-wider">[ Workshop Actions ]</div>
            
            {vetMode === "none" ? (
              <div className="flex gap-2 text-[10px] font-mono">
                <button
                  onClick={handleRefine}
                  disabled={isRefining || isVetting}
                  className="flex-1 py-1 border border-[#a78bfa]/20 hover:border-[#a78bfa]/40 bg-[#a78bfa]/5 hover:bg-[#a78bfa]/10 text-[#a78bfa] transition-all text-center cursor-pointer select-none uppercase tracking-wider rounded font-bold"
                >
                  {isRefining ? "[ refining... ]" : "[ refine proposal ]"}
                </button>
                <button
                  onClick={() => setVetMode("adopt")}
                  disabled={isRefining || isVetting}
                  className="flex-1 py-1 border border-[#4ade80]/20 hover:border-[#4ade80]/40 bg-[#4ade80]/5 hover:bg-[#4ade80]/10 text-[#4ade80] transition-all text-center cursor-pointer select-none uppercase tracking-wider rounded font-bold"
                >
                  [ adopt ]
                </button>
                <button
                  onClick={() => setVetMode("reject")}
                  disabled={isRefining || isVetting}
                  className="flex-1 py-1 border border-[#ef4444]/20 hover:border-[#ef4444]/40 bg-[#ef4444]/5 hover:bg-[#ef4444]/10 text-[#ef4444] transition-all text-center cursor-pointer select-none uppercase tracking-wider rounded font-bold"
                >
                  [ reject ]
                </button>
                {activeBeliefs.length > 0 && (
                  <button
                    onClick={() => setVetMode("merge")}
                    disabled={isRefining || isVetting}
                    className="flex-1 py-1 border border-[#facc15]/20 hover:border-[#facc15]/40 bg-[#facc15]/5 hover:bg-[#facc15]/10 text-[#facc15] transition-all text-center cursor-pointer select-none uppercase tracking-wider rounded font-bold"
                  >
                    [ merge ]
                  </button>
                )}
              </div>
            ) : (
              <div className="bg-[#08080c] border border-[#1a1a24] rounded p-2 flex flex-col gap-2 font-mono">
                <div className="flex justify-between items-center border-b border-[#222] pb-1">
                  <span className="text-[#aaa] text-[9.5px] uppercase font-bold">Action: {vetMode}</span>
                  <button
                    onClick={() => setVetMode("none")}
                    className="text-[#ef4444] hover:text-[#ef4444]/80 text-[9px] font-bold cursor-pointer"
                  >
                    [cancel]
                  </button>
                </div>

                {vetMode === "adopt" && (
                  <>
                    <div className="flex flex-col gap-1">
                      <label className="text-[#555] text-[9px] uppercase font-bold">[ Belief Label ]</label>
                      <input
                        type="text"
                        value={adoptLabel}
                        onChange={(e) => setAdoptLabel(e.target.value)}
                        className="bg-[#050508] border border-[#222] text-[#ccc] px-1.5 py-1 rounded text-[10px] w-full focus:outline-none focus:border-[#a78bfa]/50"
                      />
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="text-[#555] text-[9px] uppercase font-bold">[ Statement ]</label>
                      <textarea
                        value={adoptStatement}
                        onChange={(e) => setAdoptStatement(e.target.value)}
                        className="bg-[#050508] border border-[#222] text-[#ccc] p-1.5 rounded text-[10px] w-full focus:outline-none focus:border-[#a78bfa]/50 min-h-[40px] resize-y font-serif"
                      />
                    </div>
                  </>
                )}

                {vetMode === "reject" && (
                  <div className="flex flex-col gap-1">
                    <label className="text-[#555] text-[9px] uppercase font-bold">[ Rejection Rationale ]</label>
                    <textarea
                      value={rejectionRationale}
                      onChange={(e) => setRejectionRationale(e.target.value)}
                      placeholder="Specify why Symbia should not adopt this belief..."
                      className="bg-[#050508] border border-[#222] text-[#ccc] p-1.5 rounded text-[10px] w-full focus:outline-none focus:border-[#a78bfa]/50 min-h-[40px] resize-y"
                    />
                  </div>
                )}

                {vetMode === "merge" && (
                  <>
                    <div className="flex flex-col gap-1">
                      <label className="text-[#555] text-[9px] uppercase font-bold">[ Target Active Belief ]</label>
                      <select
                        value={targetBeliefId}
                        onChange={(e) => setTargetBeliefId(e.target.value)}
                        className="bg-[#050508] border border-[#222] text-[#ccc] px-1 py-1 rounded text-[10px] w-full focus:outline-none focus:border-[#a78bfa]/50"
                      >
                        <option value="">-- select target --</option>
                        {activeBeliefs.map(ab => (
                          <option key={ab.id} value={ab.id}>{ab.label} (v{ab.version})</option>
                        ))}
                      </select>
                    </div>
                    {targetBeliefId && (
                      <div className="flex flex-col gap-1 mt-1">
                        <div className="flex justify-between items-center">
                          <label className="text-[#555] text-[9px] uppercase font-bold">[ Synthesized Statement ]</label>
                          <span className="text-[#666] text-[8.5px] italic">modify to refine during merge</span>
                        </div>
                        <textarea
                          value={mergedStatement}
                          onChange={(e) => setMergedStatement(e.target.value)}
                          className="bg-[#050508] border border-[#222] text-[#ccc] p-1.5 rounded text-[10px] w-full focus:outline-none focus:border-[#a78bfa]/50 min-h-[50px] resize-y font-serif"
                        />
                      </div>
                    )}
                  </>
                )}

                <button
                  onClick={() => handleVet(vetMode)}
                  disabled={isVetting}
                  className={`w-full py-1 text-center font-bold uppercase tracking-wider rounded border text-[10px] cursor-pointer ${
                    vetMode === "adopt"
                      ? "border-[#4ade80]/30 hover:border-[#4ade80]/50 bg-[#4ade80]/5 hover:bg-[#4ade80]/10 text-[#4ade80]"
                      : vetMode === "reject"
                      ? "border-[#ef4444]/30 hover:border-[#ef4444]/50 bg-[#ef4444]/5 hover:bg-[#ef4444]/10 text-[#ef4444]"
                      : "border-[#facc15]/30 hover:border-[#facc15]/50 bg-[#facc15]/5 hover:bg-[#facc15]/10 text-[#facc15]"
                  }`}
                >
                  {isVetting ? "[ processing... ]" : `[ confirm ${vetMode} ]`}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  const handleStartEdit = () => {
    setEditLabel(b.label)
    setEditStatement(b.statement)
    setEditConfidence(b.confidence)
    setEditOntologicalMass(b.ontological_mass)
    setEditLifecycleStage(b.lifecycle_stage)
    setIsEditing(true)
    setIsConfirmingDelete(false)
    setErrorMsg(null)
  }

  const handleSave = async () => {
    if (!editLabel.trim()) {
      setErrorMsg("Label is required")
      return
    }
    if (!editStatement.trim()) {
      setErrorMsg("Statement is required")
      return
    }
    setIsSavingOrDeleting(true)
    setErrorMsg(null)
    try {
      const result = await updateBelief(b.id, {
        label: editLabel.trim(),
        statement: editStatement.trim(),
        confidence: editConfidence,
        ontological_mass: editOntologicalMass,
        lifecycle_stage: editLifecycleStage,
      })

      if (result.status === "ok") {
        const updatedB: BeliefNodeInfo = {
          ...b,
          label: editLabel.trim(),
          statement: editStatement.trim(),
          confidence: editConfidence,
          ontological_mass: editOntologicalMass,
          lifecycle_stage: editLifecycleStage,
        }
        onUpdate(updatedB)
        setIsEditing(false)
        if (result.speciation_alert) {
          alert("Speciation Alert: Belief has drifted significantly from its original signature!")
        }
      } else {
        setErrorMsg("Failed to update belief details")
      }
    } catch (e: any) {
      setErrorMsg(e.message || String(e))
    } finally {
      setIsSavingOrDeleting(false)
    }
  }

  const handleDelete = async () => {
    setIsSavingOrDeleting(true)
    setErrorMsg(null)
    try {
      await deleteBelief(b.id)
      onDelete(b.id)
    } catch (e: any) {
      setErrorMsg(e.message || String(e))
      setIsSavingOrDeleting(false)
      setIsConfirmingDelete(false)
    }
  }

  const handleRevert = async (targetVersion: number) => {
    setIsSavingOrDeleting(true)
    setErrorMsg(null)
    try {
      const result = await revertBelief(b.id, targetVersion)
      if (result.status === "ok") {
        const vRes = await fetch(`/api/beliefs/${b.id}/versions`)
        const vData = await vRes.json()
        if (Array.isArray(vData)) {
          setVersions(vData)
          const targetVerObj = vData.find((x: any) => x.version === targetVersion)
          if (targetVerObj) {
            const updatedB: BeliefNodeInfo = {
              ...b,
              statement: targetVerObj.statement,
              vector_16d: JSON.stringify(targetVerObj.vector_16d),
              version: result.version,
            }
            onUpdate(updatedB)
          }
        }
        if (result.speciation_alert) {
          alert(`Speciation Alert: Belief signature has drifted significantly after reverting to version ${targetVersion}!`)
        }
      } else {
        setErrorMsg("Failed to revert belief statement version")
      }
    } catch (e: any) {
      setErrorMsg(e.message || String(e))
    } finally {
      setIsSavingOrDeleting(false)
    }
  }

  if (isEditing) {
    return (
      <div className="flex-1 min-h-0 flex flex-col border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50 p-2.5 gap-2.5 text-[11px] font-mono">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#1f1f2e]/30 pb-1.5 shrink-0">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-[10px] shrink-0 text-[#a78bfa]">◆</span>
            <span className="font-mono text-[11px] font-bold text-[#ccc] truncate">editing: {b.label}</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={isSavingOrDeleting}
              className="text-[10px] text-[#4ade80] hover:text-[#4ade80]/80 disabled:text-[#555] transition-colors cursor-pointer select-none font-bold"
            >
              {isSavingOrDeleting ? "[saving...]" : "[save]"}
            </button>
            <button
              onClick={() => setIsEditing(false)}
              disabled={isSavingOrDeleting}
              className="text-[10px] text-[#ef4444] hover:text-[#ef4444]/80 disabled:text-[#555] transition-colors cursor-pointer select-none font-bold"
            >
              [cancel]
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="text-[10px] text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/20 p-1.5 rounded shrink-0">
            {errorMsg}
          </div>
        )}

        {/* Form fields */}
        <div className="flex-1 flex flex-col gap-2.5 min-h-0 overflow-y-auto pr-1">
          {/* Label */}
          <div className="shrink-0 flex flex-col gap-1">
            <label className="text-[#555] text-[10px] uppercase font-bold">[ Belief Label ]</label>
            <input
              type="text"
              value={editLabel}
              onChange={(e) => setEditLabel(e.target.value)}
              disabled={isSavingOrDeleting}
              className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] px-2 py-1.5 rounded text-[11px] font-mono w-full focus:outline-none focus:border-[#a78bfa]/50"
            />
          </div>

          {/* Statement */}
          <div className="shrink-0 flex flex-col gap-1">
            <label className="text-[#555] text-[10px] uppercase font-bold">[ Statement / core thesis ]</label>
            <textarea
              value={editStatement}
              onChange={(e) => setEditStatement(e.target.value)}
              disabled={isSavingOrDeleting}
              className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] p-2 rounded text-[11px] font-serif leading-relaxed w-full focus:outline-none focus:border-[#a78bfa]/50 min-h-[60px] resize-y"
            />
          </div>

          {/* Confidence slider */}
          <div className="shrink-0 flex flex-col gap-1">
            <label className="text-[#555] text-[10px] uppercase font-bold">
              [ Confidence: {(editConfidence * 100).toFixed(0)}% ]
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={editConfidence}
              onChange={(e) => setEditConfidence(parseFloat(e.target.value))}
              disabled={isSavingOrDeleting}
              className="accent-[#a78bfa] w-full cursor-pointer bg-[#14141c] h-1 rounded"
            />
          </div>

          {/* Ontological Mass slider */}
          <div className="shrink-0 flex flex-col gap-1">
            <label className="text-[#555] text-[10px] uppercase font-bold">
              [ Ontological Mass: {editOntologicalMass.toFixed(2)} ]
            </label>
            <input
              type="range"
              min="0"
              max="3"
              step="0.05"
              value={editOntologicalMass}
              onChange={(e) => setEditOntologicalMass(parseFloat(e.target.value))}
              disabled={isSavingOrDeleting}
              className="accent-[#a78bfa] w-full cursor-pointer bg-[#14141c] h-1 rounded"
            />
          </div>

          {/* Lifecycle Stage select */}
          <div className="shrink-0 flex flex-col gap-1">
            <label className="text-[#555] text-[10px] uppercase font-bold">[ Lifecycle Stage ]</label>
            <select
              value={editLifecycleStage}
              onChange={(e) => setEditLifecycleStage(e.target.value)}
              disabled={isSavingOrDeleting}
              className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] px-2 py-1.5 rounded text-[11px] font-mono w-full focus:outline-none focus:border-[#a78bfa]/50"
            >
              <option value="nucleation">nucleation (proto-belief)</option>
              <option value="accretion">accretion (incubating)</option>
              <option value="crystallized">crystallized (active)</option>
              <option value="senescence">senescence (decaying)</option>
              <option value="collapsed">collapsed (ghost)</option>
            </select>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex-1 min-h-0 flex flex-col overflow-y-auto pr-1.5 border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50 p-2.5 gap-2.5 text-[11px] font-sans ${isGhost ? "opacity-55" : ""}`}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1f1f2e]/30 pb-1.5 shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[11px] shrink-0" style={{ color: catColor }}>●</span>
          <span className="font-mono text-[11px] font-bold text-[#ccc] truncate">
            {b.label} <span className="text-[#888] font-normal text-[9px] ml-1 bg-[#1a1a24] px-1 py-0.5 rounded border border-[#2d2d3a]">v{b.version}</span>
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          {agentFlux && (
            <>
              {isConfirmingDelete ? (
                <div className="flex items-center gap-1.5 font-mono text-[10px]">
                  <span className="text-[#ef4444] animate-pulse">confirm delete?</span>
                  <button
                    onClick={handleDelete}
                    disabled={isSavingOrDeleting}
                    className="text-[#ef4444] hover:underline cursor-pointer select-none font-bold"
                  >
                    [yes]
                  </button>
                  <button
                    onClick={() => setIsConfirmingDelete(false)}
                    disabled={isSavingOrDeleting}
                    className="text-[#888] hover:underline cursor-pointer select-none font-bold"
                  >
                    [no]
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setIsConfirmingDelete(true)}
                  disabled={isSavingOrDeleting}
                  className="text-[10px] text-[#ef4444] hover:text-[#f87171] font-mono transition-colors cursor-pointer select-none font-bold"
                >
                  [delete]
                </button>
              )}
              <button
                onClick={handleStartEdit}
                disabled={isSavingOrDeleting}
                className="text-[10px] text-[#a78bfa] hover:text-[#c084fc] font-mono transition-colors cursor-pointer select-none font-bold"
              >
                [edit]
              </button>
            </>
          )}
          <span
            className="text-[9px] uppercase font-mono px-1.5 py-px rounded border shrink-0 font-bold"
            style={{ color: catColor, borderColor: `${catColor}40`, backgroundColor: `${catColor}10` }}
          >
            {b.category}
          </span>
        </div>
      </div>

      {errorMsg && (
        <div className="text-[10px] text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/20 p-1.5 rounded shrink-0 font-mono">
          {errorMsg}
        </div>
      )}

      {/* Statement */}
      <div className="shrink-0">
        <div className="text-[#555] font-mono text-[10px] uppercase font-bold">[ Statement ]</div>
        <div className="text-[#ccc] text-[11px] italic font-serif leading-relaxed mt-0.5">
          "{b.statement}"
        </div>
      </div>

      {/* Metadata grid */}
      <div className="shrink-0 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-mono text-[#888]">
        <div><span className="text-[#444]">Category:</span> <span style={{ color: catColor }}>{b.category}</span></div>
        <div><span className="text-[#444]">Origin:</span> <span className="text-[#aaa]">{b.origin === "emergent" ? "agent" : b.origin === "authored" ? "user" : b.origin}</span></div>
        <div><span className="text-[#444]">Stage:</span> <span style={{ color: stageColor }}>{getStageLabel(stage)}</span></div>
        <div><span className="text-[#444]">Mass:</span> <span className="text-[#aaa]">{isProto ? b.ontological_mass.toFixed(3) : b.ontological_mass.toFixed(1)}</span></div>
        <div className="col-span-2"><span className="text-[#444]">Confidence:</span> <span className="text-[#aaa] font-bold">{(b.confidence * 100).toFixed(0)}%</span></div>
      </div>

      {/* Vector */}
      {vec.length > 0 && (
        <div className="shrink-0 mb-1">
          <div className="text-[#555] font-mono text-[10px] uppercase mb-1 font-bold">[ 16D Autopoietic Signature ]</div>
          <StructuralAutopoieticGlyph
            signature={vec}
            isStagnant={false}
          />
        </div>
      )}

      {/* Tabs Selector */}
      <div className="shrink-0 border-b border-[#1f1f2e]/20 flex gap-4 mt-2 text-[10px] font-mono">
        <button
          onClick={() => setActiveTab("metabolism")}
          className={`pb-1.5 px-0.5 border-b-2 font-bold cursor-pointer transition-colors ${
            activeTab === "metabolism"
              ? "border-[#a78bfa] text-[#a78bfa]"
              : "border-transparent text-[#555] hover:text-[#888]"
          }`}
        >
          [ METABOLISM LOG ]
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={`pb-1.5 px-0.5 border-b-2 font-bold cursor-pointer transition-colors ${
            activeTab === "history"
              ? "border-[#a78bfa] text-[#a78bfa]"
              : "border-transparent text-[#555] hover:text-[#888]"
          }`}
        >
          [ STATEMENT HISTORY ({versions.length}) ]
        </button>
      </div>

      {/* Tab Contents */}
      {activeTab === "metabolism" && (
        <div className="flex flex-col mt-2 shrink-0">
          <div className="text-[#555] font-mono text-[10px] uppercase shrink-0 font-bold mb-1">[ Metabolism Events ]</div>
          {(!b.events || b.events.length === 0) ? (
            <div className="text-[11px] text-[#444] italic mt-0.5 font-mono">No metabolic events logged</div>
          ) : (
            <div className="space-y-1.5 max-h-[200px] overflow-y-auto pr-1">
              {b.events.map((e) => {
                const isPos = e.delta_confidence >= 0
                const diffStr = isPos ? `+${e.delta_confidence.toFixed(3)}` : `${e.delta_confidence.toFixed(3)}`
                return (
                  <div key={e.id} className="text-[11px] border-b border-[#222]/30 pb-1 last:border-b-0 leading-normal">
                    <div className="flex items-center justify-between text-[#888]">
                      <span className="font-mono text-[10px]">{new Date(e.timestamp).toLocaleTimeString()}</span>
                      <span className={`font-mono text-[10px] font-bold ${isPos ? "text-[#4ade80]" : "text-[#f87171]"}`}>{diffStr}</span>
                    </div>
                    <div className="text-[#ccc] mt-0.5">
                      <span className="text-[#6c6c8a] font-mono text-[10px] mr-1">[{e.source_type}:{e.source_id}]</span>
                      {e.description}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {activeTab === "history" && (
        <div className="shrink-0 pt-2 font-mono text-[10px]">
          <div className="text-[#555] uppercase mb-1 font-bold">[ Version Diff History ]</div>
          {versions.length === 0 ? (
            <div className="text-[11px] text-[#444] italic font-mono mt-0.5">No versions recorded</div>
          ) : (
            <div className="space-y-1 max-h-[220px] overflow-y-auto pr-1">
              {versions.map((v, vIdx) => {
                const prev = vIdx < versions.length - 1 ? versions[vIdx + 1] : null
                const isExpanded = !!expandedVersions[v.version]
                const prevStatement = prev ? prev.statement : ""
                const statementDiff = isExpanded ? computeLineDiff(prevStatement, v.statement) : []
                const hasDiff = isExpanded && prevStatement !== v.statement

                return (
                  <div key={v.version} className="flex flex-col gap-1.5 p-1.5 rounded bg-[#07070b]/60 border border-[#1f1f2e]/10 text-[10px] font-mono">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[#a78bfa] font-bold">v{v.version}</span>
                          <span className="text-[#555] text-[9px]">
                            {v.created_at ? new Date(v.created_at).toLocaleString() : ""}
                          </span>
                        </div>
                        <div className="text-[#aaa] text-[9px] mt-0.5 truncate" title={v.change_reason || "No description"}>
                          {v.change_reason || "No description"}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {agentFlux && v.version !== b.version && (
                          <button
                            onClick={() => handleRevert(v.version)}
                            disabled={isSavingOrDeleting}
                            className="text-[9px] text-[#a78bfa] hover:text-[#c084fc] hover:underline disabled:text-[#555] cursor-pointer select-none font-bold mr-1"
                          >
                            [revert]
                          </button>
                        )}
                        <button
                          onClick={() => setExpandedVersions(prevMap => ({ ...prevMap, [v.version]: !prevMap[v.version] }))}
                          className="text-[9px] text-[#888] hover:text-[#ccc] hover:underline cursor-pointer select-none font-bold"
                        >
                          {isExpanded ? "[collapse]" : "[diff]"}
                        </button>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="mt-1 border-t border-[#1f1f2e]/10 pt-1.5 space-y-2 text-[9px]">
                        {hasDiff ? (
                          <div>
                            <div className="text-[#555] uppercase font-bold tracking-wider mb-0.5">[ Statement Diff ]</div>
                            <div className="bg-[#050508]/90 border border-[#1f1f2e]/10 p-1.5 rounded leading-relaxed text-[10px] font-sans">
                              {statementDiff.map((line, lIdx) => (
                                <div
                                  key={lIdx}
                                  className={
                                    line.type === 'added'
                                      ? 'text-[#4ade80] bg-[#4ade80]/5 px-1 font-mono'
                                      : line.type === 'removed'
                                        ? 'text-[#ef4444] bg-[#ef4444]/5 line-through px-1 font-mono'
                                        : 'text-[#888] px-1 font-mono'
                                  }
                                >
                                  {line.type === 'added' ? '+ ' : line.type === 'removed' ? '- ' : '  '}
                                  {line.value}
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="text-[#555] italic">No differences in statement.</div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
