import { useState, useEffect, useRef, memo } from "react"
import { updateBelief, deleteBelief, revertBelief, vetBeliefProposal, refineBeliefProposal, synthesizeMergeStatement } from "../../../../api/client"
import type { BeliefNodeInfo } from "../../../../api/client"
import { computeLineDiff } from "../../../../utils/diff"
import { formatTime, formatDateTimeFull } from "../../../../utils/dateFormat"
import { StructuralAutopoieticGlyph } from "../../../UI/StructuralAutopoieticGlyph"
import { getCategoryColor, getBeliefStageColor, getBeliefStageLabel } from "../shared/helpers"
import { TerminalTabs } from "../../../UI"

/* ── Module-level constants ── */

type DetailTab = "details" | "log" | "version"

/* ── Shared version item (no bg/border) ── */

function VersionItem({
  version, label, timestamp, changelog,
  isCurrent, agentFlux, isExpanded, hasDiff,
  onToggleDiff, onRevert, isReverting, children,
}: {
  version: number; label: string; timestamp: string; changelog: string
  isCurrent: boolean; agentFlux: boolean; isExpanded: boolean; hasDiff: boolean
  onToggleDiff: () => void; onRevert?: () => void; isReverting?: boolean
  children?: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-1 text-[10px] font-mono">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[#a78bfa] font-bold">v{version}</span>
            <span className="text-[#555] text-[9px]">{label}</span>
            <span className="text-[#555] text-[9px]">{timestamp}</span>
          </div>
          <div className="text-[#aaa] text-[9px] mt-0.5 truncate" title={changelog}>
            {changelog}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {agentFlux && !isCurrent && onRevert && (
            <button onClick={onRevert} disabled={isReverting}
              className="text-[9px] text-[#a78bfa] hover:text-[#c084fc] hover:underline disabled:text-[#555] cursor-pointer select-none font-bold">
              {isReverting ? "[reverting...]" : "[revert]"}
            </button>
          )}
          {hasDiff && (
            <button onClick={onToggleDiff}
              className="text-[9px] text-[#888] hover:text-[#ccc] hover:underline cursor-pointer select-none font-bold">
              {isExpanded ? "[collapse]" : "[diff]"}
            </button>
          )}
        </div>
      </div>
      {isExpanded && children}
    </div>
  )
}

/* ── Main Component ── */

interface BeliefDetailProps {
  belief: BeliefNodeInfo | null
  activeBeliefs: BeliefNodeInfo[]
  onUpdate: (updatedBelief: BeliefNodeInfo) => void
  onDelete: (beliefId: string) => void
  onReload?: () => void
  agentFlux: boolean
}

export const BeliefDetail = memo(function BeliefDetail({ belief, activeBeliefs = [], onUpdate, onDelete, onReload, agentFlux }: BeliefDetailProps) {
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
  const [activeTab, setActiveTab] = useState<DetailTab>("details")

  const [vetMode, setVetMode] = useState<"none" | "adopt" | "reject" | "merge">("none")
  const [adoptLabel, setAdoptLabel] = useState("")
  const [adoptStatement, setAdoptStatement] = useState("")
  const [rejectionRationale, setRejectionRationale] = useState("")
  const [targetBeliefId, setTargetBeliefId] = useState("")
  const [mergedStatement, setMergedStatement] = useState("")
  const [isRefining, setIsRefining] = useState(false)
  const [isVetting, setIsVetting] = useState(false)
  const [isSynthesizing, setIsSynthesizing] = useState(false)
  const workshopRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (vetMode !== "none" && workshopRef.current) {
      workshopRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" })
    }
  }, [vetMode])

  useEffect(() => {
    if (vetMode === "merge" && targetBeliefId) {
      const tb = activeBeliefs.find(ab => ab.id === targetBeliefId)
      if (tb) setMergedStatement(tb.statement)
    } else { setMergedStatement("") }
  }, [vetMode, targetBeliefId, activeBeliefs])

  useEffect(() => {
    setIsEditing(false); setIsConfirmingDelete(false); setErrorMsg(null)
    setExpandedVersions({}); setVetMode("none")
    setAdoptLabel(""); setAdoptStatement(""); setRejectionRationale("")
    setTargetBeliefId(""); setMergedStatement("")
    setIsRefining(false); setIsVetting(false); setIsSynthesizing(false)
    if (!belief) { setVersions([]); return }
    setVersions([]); setActiveTab("details")
    if (belief.is_proposal) {
      setAdoptLabel(belief.suggested_label || belief.label || "")
      setAdoptStatement(belief.suggested_statement || belief.statement || "")
      if (belief.potential_merge_target) setTargetBeliefId(belief.potential_merge_target)
      else if (activeBeliefs && activeBeliefs.length > 0) setTargetBeliefId(activeBeliefs[0].id)
      return
    }
    fetch(`/api/beliefs/${belief.id}/versions`)
      .then(res => res.json()).then(data => { if (Array.isArray(data)) setVersions(data) })
      .catch(e => console.error("Failed to load belief versions:", e))
  }, [belief, activeBeliefs])

  if (!belief) {
    return (
      <div className="flex-1 min-h-0 flex items-center justify-center">
        <span className="text-[11px] text-[#444] italic font-mono">select a node to inspect</span>
      </div>
    )
  }

  const b = belief
  const catColor = getCategoryColor(b.category)
  const stage = b.lifecycle_stage || "crystallized"
  const stageColor = getBeliefStageColor(stage)

  /* ── Handlers (declared before JSX per Best Practices §3) ── */
  const handleStartEdit = () => {
    setEditLabel(b.label); setEditStatement(b.statement); setEditConfidence(b.confidence)
    setEditOntologicalMass(b.ontological_mass); setEditLifecycleStage(b.lifecycle_stage)
    setIsEditing(true); setIsConfirmingDelete(false); setErrorMsg(null)
  }

  const handleSave = async () => {
    if (!editLabel.trim()) { setErrorMsg("Label is required"); return }
    if (!editStatement.trim()) { setErrorMsg("Statement is required"); return }
    setIsSavingOrDeleting(true); setErrorMsg(null)
    try {
      const result = await updateBelief(b.id, { label: editLabel.trim(), statement: editStatement.trim(), confidence: editConfidence, ontological_mass: editOntologicalMass, lifecycle_stage: editLifecycleStage })
      if (result.status === "ok") {
        onUpdate({ ...b, label: editLabel.trim(), statement: editStatement.trim(), confidence: editConfidence, ontological_mass: editOntologicalMass, lifecycle_stage: editLifecycleStage })
        setIsEditing(false)
        if (result.speciation_alert) alert("Speciation Alert: Belief has drifted significantly from its original signature!")
      } else { setErrorMsg("Failed to update belief details") }
    } catch (e: any) { setErrorMsg(e.message || String(e)) }
    finally { setIsSavingOrDeleting(false) }
  }

  const handleDelete = async () => {
    setIsSavingOrDeleting(true); setErrorMsg(null)
    try { await deleteBelief(b.id); onDelete(b.id) }
    catch (e: any) { setErrorMsg(e.message || String(e)); setIsSavingOrDeleting(false); setIsConfirmingDelete(false) }
  }

  const handleRevert = async (targetVersion: number) => {
    setIsSavingOrDeleting(true); setErrorMsg(null)
    try {
      const result = await revertBelief(b.id, targetVersion)
      if (result.status === "ok") {
        const vRes = await fetch(`/api/beliefs/${b.id}/versions`); const vData = await vRes.json()
        if (Array.isArray(vData)) {
          setVersions(vData)
          const tv = vData.find((x: any) => x.version === targetVersion)
          if (tv) onUpdate({ ...b, statement: tv.statement, vector_16d: JSON.stringify(tv.vector_16d), version: result.version })
        }
        if (result.speciation_alert) alert(`Speciation Alert: Belief signature has drifted significantly after reverting to version ${targetVersion}!`)
      } else { setErrorMsg("Failed to revert belief statement version") }
    } catch (e: any) { setErrorMsg(e.message || String(e)) }
    finally { setIsSavingOrDeleting(false) }
  }

  const handleRefine = async () => {
    setIsRefining(true); setErrorMsg(null)
    try {
      const result = await refineBeliefProposal(b.id)
      if (result.status === "error") setErrorMsg(result.message || "Failed to refine proposal")
      else if (onReload) onReload()
    } catch (e: any) { setErrorMsg(e.message || String(e)) }
    finally { setIsRefining(false) }
  }

  const handleVet = async (action: "adopt" | "reject" | "merge") => {
    setIsVetting(true); setErrorMsg(null)
    try {
      const payload: any = { action }
      if (action === "adopt") { if (!adoptLabel.trim()) { setErrorMsg("Suggested label is required"); setIsVetting(false); return }; if (!adoptStatement.trim()) { setErrorMsg("Suggested statement is required"); setIsVetting(false); return }; payload.suggested_label = adoptLabel.trim(); payload.suggested_statement = adoptStatement.trim() }
      else if (action === "reject") { if (!rejectionRationale.trim()) { setErrorMsg("Rejection rationale is required"); setIsVetting(false); return }; payload.rejection_rationale = rejectionRationale.trim() }
      else if (action === "merge") { if (!targetBeliefId) { setErrorMsg("Please select a target belief"); setIsVetting(false); return }; payload.target_belief_id = targetBeliefId; payload.merged_statement = mergedStatement.trim() }
      const result = await vetBeliefProposal(b.id, payload)
      if (result.status === "ok" || result.status === "success") { if (onReload) onReload() }
      else { setErrorMsg(result.message || `Failed to ${action} proposal`) }
    } catch (e: any) { setErrorMsg(e.message || String(e)) }
    finally { setIsVetting(false) }
  }

  const handleSynthesize = async () => {
    if (!targetBeliefId) return; setIsSynthesizing(true); setErrorMsg(null)
    try { const r = await synthesizeMergeStatement(b.id, targetBeliefId); if (r.status === "ok") setMergedStatement(r.synthesized_statement); else setErrorMsg("Synthesis failed") }
    catch (e: any) { setErrorMsg(e.message || "Synthesis failed") }
    finally { setIsSynthesizing(false) }
  }
  const isGhost = stage === "collapsed" || stage === "faded"
  let vec: number[] = []
  try { if (b.vector_16d) vec = JSON.parse(b.vector_16d) } catch { }

  /* ── Edit mode ── */
  if (isEditing) {
    return (
      <div className="flex-1 min-h-0 flex flex-col gap-3 text-[11px] font-mono">
        <div className="flex items-center justify-between">
          <span className="text-[#ccc] font-bold">editing: {b.label}</span>
          <div className="flex gap-2">
            <button onClick={handleSave} disabled={isSavingOrDeleting}
              className="text-[10px] text-[#666] hover:text-[#4ade80] disabled:text-[#555] transition-colors cursor-pointer select-none font-bold">
              {isSavingOrDeleting ? "[saving...]" : "[save]"}
            </button>
            <button onClick={() => setIsEditing(false)} disabled={isSavingOrDeleting}
              className="text-[10px] text-[#666] hover:text-[#ef4444] disabled:text-[#555] transition-colors cursor-pointer select-none font-bold">
              [cancel]
            </button>
          </div>
        </div>
        {errorMsg && <div className="text-[#ef4444]">{errorMsg}</div>}
        <div className="flex-1 flex flex-col gap-3 min-h-0 overflow-y-auto pr-1">
          <div className="flex flex-col gap-1">
            <span className="text-[#555] text-[10px] uppercase font-bold">[ Belief Label ]</span>
            <input type="text" value={editLabel} onChange={e => setEditLabel(e.target.value)} disabled={isSavingOrDeleting}
              className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] px-2 py-1.5 rounded text-[11px] font-mono w-full focus:outline-none focus:border-[#a78bfa]/50" />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-[#555] text-[10px] uppercase font-bold">[ Statement ]</span>
            <textarea value={editStatement} onChange={e => setEditStatement(e.target.value)} disabled={isSavingOrDeleting}
              className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] p-2 rounded text-[11px] font-serif leading-relaxed w-full focus:outline-none focus:border-[#a78bfa]/50 min-h-[60px] resize-y" />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-[#555] text-[10px] uppercase font-bold">[ Confidence: {(editConfidence * 100).toFixed(0)}% ]</span>
            <input type="range" min="0" max="1" step="0.05" value={editConfidence}
              onChange={e => setEditConfidence(parseFloat(e.target.value))} disabled={isSavingOrDeleting}
              className="accent-[#a78bfa] w-full cursor-pointer bg-[#14141c] h-1 rounded" />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-[#555] text-[10px] uppercase font-bold">[ Ontological Mass: {editOntologicalMass.toFixed(2)} ]</span>
            <input type="range" min="0" max="3" step="0.05" value={editOntologicalMass}
              onChange={e => setEditOntologicalMass(parseFloat(e.target.value))} disabled={isSavingOrDeleting}
              className="accent-[#a78bfa] w-full cursor-pointer bg-[#14141c] h-1 rounded" />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-[#555] text-[10px] uppercase font-bold">[ Lifecycle Stage ]</span>
            <select value={editLifecycleStage} onChange={e => setEditLifecycleStage(e.target.value)} disabled={isSavingOrDeleting}
              className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] px-2 py-1.5 rounded text-[11px] font-mono w-full focus:outline-none focus:border-[#a78bfa]/50">
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

  /* ── Proposal view ── */
  if (b.is_proposal) {
    const status = b.proposal_status || "pending"
    return (
      <div className={`flex-1 min-h-0 flex flex-col overflow-y-auto pr-1.5 gap-3 text-[11px] ${isGhost ? "opacity-55" : ""}`}>
        <div className="flex items-center justify-between font-mono">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-[11px] shrink-0 text-[#f59e0b]">◇</span>
            <span className="font-bold text-[#ccc] truncate">PROPOSAL: {b.label}</span>
          </div>
          <span className="text-[9px] font-mono font-bold"
            style={{ color: status === "pending" ? "#f59e0b" : status === "refined" ? "#a78bfa" : status === "rejected" ? "#ef4444" : "#4ade80" }}>
            {status}
          </span>
        </div>
        {errorMsg && <div className="text-[#ef4444]">{errorMsg}</div>}
        <div>
          <div className="text-[#555] font-mono text-[10px] uppercase font-bold">[ Provisional Statement ]</div>
          <div className="text-[#ccc] text-[11px] italic font-serif leading-relaxed mt-0.5">"{b.statement}"</div>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] font-mono text-[#888]">
          <span><span className="text-[#444]">Origin:</span> <span className="text-[#aaa]">emergent</span></span>
          <span><span className="text-[#444]">Mass:</span> <span className="text-[#aaa]">{b.ontological_mass.toFixed(2)}</span></span>
          <span><span className="text-[#444]">Confidence:</span> <span className="text-[#aaa]">{(b.confidence * 100).toFixed(0)}%</span></span>
          <span><span className="text-[#444]">Created:</span> <span className="text-[#aaa]">{b.last_reinforced_at ? formatDateTimeFull(b.last_reinforced_at) : ""}</span></span>
        </div>
        {b.symbia_reflection && (
          <div>
            <div className="text-[#a78bfa] font-mono text-[9px] uppercase font-bold tracking-wider">[ Symbia's Reflection ]</div>
            <div className="text-[#ccc] leading-relaxed text-[10.5px] mt-0.5">{b.symbia_reflection}</div>
            {b.symbia_friction_rationale && (
              <div className="mt-1 text-[#fb7185] italic text-[10px]">
                <span className="font-mono uppercase font-bold">[ Friction Warning ]:</span> {b.symbia_friction_rationale}
              </div>
            )}
          </div>
        )}
        {status === "rejected" && b.rejection_rationale && (
          <div>
            <div className="text-[#ef4444]/60 font-mono text-[9px] uppercase font-bold tracking-wider">[ Refusal Rationale ]</div>
            <div className="text-[#ef4444]/90 leading-relaxed text-[10.5px] mt-0.5">{b.rejection_rationale}</div>
          </div>
        )}
        {vec.length > 0 && (
          <div>
            <div className="text-[#555] font-mono text-[10px] uppercase font-bold">[ Initial Signature ]</div>
            <StructuralAutopoieticGlyph signature={vec} isStagnant={false} />
          </div>
        )}
        {b.source_trace && b.source_trace.length > 0 && (
          <div>
            <div className="text-[#555] font-mono text-[10px] uppercase font-bold">[ Source Trace ]</div>
            <div className="space-y-1 max-h-[80px] overflow-y-auto pr-1">
              {b.source_trace.map((src: any, idx: number) => (
                <div key={idx} className="text-[#888] font-mono text-[9.5px]">
                  • <span className="text-[#6c6c8a]">{src.type}</span>: <span className="text-[#aaa]">{src.id}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        {agentFlux && (status === "pending" || status === "refined") && (
          <div ref={workshopRef} className="flex flex-col gap-2">
            <div className="text-[#a78bfa] font-mono text-[10px] uppercase font-bold tracking-wider">[ Workshop Actions ]</div>
            {vetMode === "none" ? (
              <div className="flex gap-2 font-mono text-[10px]">
                <button onClick={handleRefine} disabled={isRefining || isVetting}
                  className="flex-1 py-1 text-[#a78bfa] hover:text-[#c084fc] cursor-pointer select-none font-bold">[ refine ]</button>
                <button onClick={() => setVetMode("adopt")} disabled={isRefining || isVetting}
                  className="flex-1 py-1 text-[#4ade80] hover:text-[#86efac] cursor-pointer select-none font-bold">[ adopt ]</button>
                <button onClick={() => setVetMode("reject")} disabled={isRefining || isVetting}
                  className="flex-1 py-1 text-[#ef4444] hover:text-[#f87171] cursor-pointer select-none font-bold">[ reject ]</button>
                {activeBeliefs.length > 0 && (
                  <button onClick={() => setVetMode("merge")} disabled={isRefining || isVetting}
                    className="flex-1 py-1 text-[#facc15] hover:text-[#fde047] cursor-pointer select-none font-bold">[ merge ]</button>
                )}
              </div>
            ) : (
              <div className="flex flex-col gap-2 font-mono">
                <div className="flex justify-between items-center">
                  <span className="text-[#aaa] text-[9.5px] uppercase font-bold">Action: {vetMode}</span>
                  <button onClick={() => setVetMode("none")} className="text-[#666] hover:text-[#ef4444] text-[9px] font-bold cursor-pointer">[cancel]</button>
                </div>
                {vetMode === "adopt" && (
                  <>
                    <div className="flex flex-col gap-1">
                      <span className="text-[#555] text-[9px] uppercase font-bold">[ Belief Label ]</span>
                      <input type="text" value={adoptLabel} onChange={e => setAdoptLabel(e.target.value)}
                        className="bg-[#050508] border border-[#222] text-[#ccc] px-1.5 py-1 rounded text-[10px] w-full focus:outline-none focus:border-[#a78bfa]/50" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-[#555] text-[9px] uppercase font-bold">[ Statement ]</span>
                      <textarea value={adoptStatement} onChange={e => setAdoptStatement(e.target.value)}
                        className="bg-[#050508] border border-[#222] text-[#ccc] p-1.5 rounded text-[10px] w-full focus:outline-none focus:border-[#a78bfa]/50 min-h-[40px] resize-y font-serif" />
                    </div>
                  </>
                )}
                {vetMode === "reject" && (
                  <div className="flex flex-col gap-1">
                    <span className="text-[#555] text-[9px] uppercase font-bold">[ Rejection Rationale ]</span>
                    <textarea value={rejectionRationale} onChange={e => setRejectionRationale(e.target.value)}
                      placeholder="Why should Symbia not adopt this belief?"
                      className="bg-[#050508] border border-[#222] text-[#ccc] p-1.5 rounded text-[10px] w-full focus:outline-none focus:border-[#a78bfa]/50 min-h-[40px] resize-y" />
                  </div>
                )}
                {vetMode === "merge" && (
                  <>
                    <div className="flex flex-col gap-1">
                      <span className="text-[#555] text-[9px] uppercase font-bold">[ Target Active Belief ]</span>
                      <select value={targetBeliefId} onChange={e => setTargetBeliefId(e.target.value)}
                        className="bg-[#050508] border border-[#222] text-[#ccc] px-1 py-1 rounded text-[10px] w-full focus:outline-none focus:border-[#a78bfa]/50">
                        <option value="">-- select target --</option>
                        {activeBeliefs.map(ab => <option key={ab.id} value={ab.id}>{ab.label} (v{ab.version})</option>)}
                      </select>
                    </div>
                    {targetBeliefId && (
                      <div className="flex flex-col gap-1">
                        <div className="flex justify-between items-center">
                          <span className="text-[#555] text-[9px] uppercase font-bold">[ Synthesized Statement ]</span>
                          <button onClick={handleSynthesize} disabled={isSynthesizing}
                            className="text-[8.5px] text-[#a78bfa] hover:text-[#c084fc] font-bold cursor-pointer underline disabled:text-[#555]">[ ask symbia to synthesize ]</button>
                        </div>
                        <textarea value={mergedStatement} onChange={e => setMergedStatement(e.target.value)}
                          className="bg-[#050508] border border-[#222] text-[#ccc] p-1.5 rounded text-[10px] w-full focus:outline-none focus:border-[#a78bfa]/50 min-h-[50px] resize-y font-serif" />
                        {targetBeliefId === belief.potential_merge_target && belief.statement && (
                          <div>
                            <div className="text-[#a78bfa] font-mono text-[9px] uppercase font-bold tracking-wider">[ Symbia's Suggested Synthesis ]</div>
                            <p className="italic font-serif text-[#ccc]">"{belief.statement}"</p>
                            <button onClick={() => setMergedStatement(belief.statement)}
                              className="text-[9px] text-[#a78bfa] hover:text-[#c084fc] font-bold cursor-pointer underline">[ Apply suggestion ]</button>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
                <button onClick={() => handleVet(vetMode)} disabled={isVetting}
                  className={`w-full py-1 text-center font-bold uppercase tracking-wider rounded border text-[10px] cursor-pointer ${vetMode === "adopt" ? "border-[#4ade80]/30 text-[#4ade80]" : vetMode === "reject" ? "border-[#ef4444]/30 text-[#ef4444]" : "border-[#facc15]/30 text-[#facc15]"}`}>
                  {isVetting ? "[ processing... ]" : `[ confirm ${vetMode} ]`}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  const sortedVersions = [...versions].sort((a, b) => b.version - a.version)

  return (
    <div className={`flex-1 min-h-0 flex flex-col overflow-y-auto pr-1.5 gap-3 text-[11px] ${isGhost ? "opacity-55" : ""}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[11px] shrink-0" style={{ color: catColor }}>●</span>
          <span className="font-mono font-bold text-[#ccc] truncate">
            {b.label} <span className="text-[#888] font-normal text-[9px]">v{b.version}</span>
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          {agentFlux && (
            <>
              {isConfirmingDelete ? (
                <span className="flex items-center gap-1.5 font-mono text-[10px]">
                  <span className="text-[#ef4444] animate-pulse">confirm delete?</span>
                  <button onClick={handleDelete} disabled={isSavingOrDeleting} className="text-[#666] hover:text-[#ef4444] hover:underline cursor-pointer select-none font-bold">[yes]</button>
                  <button onClick={() => setIsConfirmingDelete(false)} disabled={isSavingOrDeleting} className="text-[#666] hover:text-[#888] hover:underline cursor-pointer select-none font-bold">[no]</button>
                </span>
              ) : (
                <button onClick={() => setIsConfirmingDelete(true)} disabled={isSavingOrDeleting} className="text-[10px] text-[#666] hover:text-[#f87171] font-mono transition-colors cursor-pointer select-none font-bold">
                  [delete]
                </button>
              )}
              <button onClick={handleStartEdit} disabled={isSavingOrDeleting} className="text-[10px] text-[#666] hover:text-[#c084fc] font-mono transition-colors cursor-pointer select-none font-bold">
                [edit]
              </button>
            </>
          )}
          <span style={{ color: catColor }} className="text-[9px] font-mono font-bold">{b.category}</span>
        </div>
      </div>

      {errorMsg && <div className="text-[#ef4444]">{errorMsg}</div>}

      {/* Tab bar: Details • Log • Version */}
      <TerminalTabs
        tabs={[
          { key: "details", label: "Details" },
          { key: "log", label: "Log", badge: b.events?.length ?? 0 },
          { key: "version", label: "Version History", badge: versions.length },
        ]}
        active={activeTab}
        onChange={(key) => setActiveTab(key as DetailTab)}
      />

      {/* Details tab */}
      {activeTab === "details" && (
        <>
          <div>
            <div className="text-[#555] font-mono text-[10px] uppercase font-bold">[ Statement ]</div>
            <div className="text-[#ccc] text-[11px] italic font-serif leading-relaxed mt-0.5">"{b.statement}"</div>
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] font-mono text-[#888]">
            <span><span className="text-[#444]">Category:</span> <span style={{ color: catColor }}>{b.category}</span></span>
            <span><span className="text-[#444]">Origin:</span> <span className="text-[#aaa]">{b.origin === "emergent" ? "agent" : b.origin === "authored" ? "user" : b.origin}</span></span>
            <span><span className="text-[#444]">Stage:</span> <span style={{ color: stageColor }}>{getBeliefStageLabel(stage)}</span></span>
            <span><span className="text-[#444]">Mass:</span> <span className="text-[#aaa]">{b.ontological_mass.toFixed(2)}</span></span>
            <span><span className="text-[#444]">Confidence:</span> <span className="text-[#aaa] font-bold">{(b.confidence * 100).toFixed(0)}%</span></span>
          </div>
          {vec.length > 0 && (
            <div>
              <div className="text-[#555] font-mono text-[10px] uppercase font-bold">[ 16D Autopoietic Signature ]</div>
              <StructuralAutopoieticGlyph signature={vec} isStagnant={false} />
            </div>
          )}
        </>
      )}

      {/* Log tab */}
      {activeTab === "log" && (
        <div>
          <div className="text-[#555] font-mono text-[10px] uppercase">[ Metabolism Events ]</div>
          {(!b.events || b.events.length === 0) ? (
            <div className="text-[#444] italic mt-0.5 font-mono">No metabolic events logged</div>
          ) : (
            <div className="space-y-2 max-h-[320px] overflow-y-auto mt-1">
              {b.events.map((e) => {
                // Use parsed values from backend if available, fall back to regex
                const massVal = e.mass ?? (() => { const m = e.description?.match(/mass=([\d.]+)/); return m ? parseFloat(m[1]) : null; })()
                const confVal = e.confidence ?? (() => { const c = e.description?.match(/conf=([\d.]+)/); return c ? parseFloat(c[1]) : null; })()
                const massDeltaMatch = e.description?.match(/\(delta=([+\-\d.]+)\)/)
                const massDelta = massDeltaMatch ? parseFloat(massDeltaMatch[1]) : e.delta_confidence || null

                const evType = e.event_type || "event"
                const evTypeColor =
                  evType === "atrophy" ? "text-[#f59e0b]" :
                  evType === "collapse" ? "text-[#ef4444]" :
                  evType === "emergence" ? "text-[#22c55e]" :
                  evType === "crystallization" ? "text-[#60a5fa]" :
                  evType === "support" ? "text-[#a78bfa]" :
                  evType === "revision" ? "text-[#f472b6]" :
                  evType === "accretion" ? "text-[#2dd4bf]" :
                  "text-[#888]"

                return (
                  <div key={e.id}>
                    <div className="flex items-center gap-x-2 font-mono text-[10px]">
                      <span className="text-[#555]">{formatTime(e.timestamp)}</span>
                      {massVal !== null && (
                        <span className="text-[#93c5fd]">
                          m:<span>{massVal.toFixed(3)}</span>
                          {massDelta !== null && massDelta !== 0 && (
                            <span className={massDelta > 0 ? "text-[#4ade80]" : "text-[#f87171]"}>
                              ({massDelta > 0 ? "+" : ""}{massDelta.toFixed(3)})
                            </span>
                          )}
                        </span>
                      )}
                      {confVal !== null && (
                        <span className="text-[#4ade80]">c:{(confVal * 100).toFixed(0)}%</span>
                      )}
                      <span className={`${evTypeColor} uppercase tracking-wider`}>[{evType}]</span>
                    </div>
                    <div className="text-[10px] text-[#777] font-mono mt-0.5 ml-2 break-words">
                      {e.description}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Version tab */}
      {activeTab === "version" && (
        <div className="font-mono text-[10px]">
          <div className="text-[#555] uppercase font-bold">[ Version Diff History ]</div>
          {versions.length === 0 ? (
            <div className="text-[#444] italic mt-0.5">No versions recorded</div>
          ) : (
            <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-1 mt-1">
              {sortedVersions.map((v, vIdx) => {
                const prev = vIdx < sortedVersions.length - 1 ? sortedVersions[vIdx + 1] : null
                const isExpanded = !!expandedVersions[v.version]
                const prevStatement = prev ? prev.statement : ""
                const hasDiff = prevStatement !== v.statement
                const statementDiff = isExpanded ? computeLineDiff(prevStatement, v.statement) : []
                return (
                  <VersionItem
                    key={v.version} version={v.version}
                    label={v.created_at ? formatDateTimeFull(v.created_at) : ""}
                    timestamp="" changelog={v.change_reason || "No description"}
                    isCurrent={v.version === b.version} agentFlux={agentFlux}
                    isExpanded={isExpanded} hasDiff={hasDiff}
                    onToggleDiff={() => setExpandedVersions(prevMap => ({ ...prevMap, [v.version]: !prevMap[v.version] }))}
                    onRevert={v.version !== b.version ? () => handleRevert(v.version) : undefined}
                    isReverting={isSavingOrDeleting}
                  >
                    {isExpanded && hasDiff && (
                      <div className="mt-1 pt-1.5 space-y-2 text-[9px]">
                        <div>
                          <div className="text-[#555] uppercase font-bold tracking-wider mb-0.5">[ Statement Diff ]</div>
                          <div>
                            {statementDiff.map((line: any, lIdx: number) => (
                              <div key={lIdx} className={line.type === 'added' ? 'text-[#4ade80] px-1 font-mono' : line.type === 'removed' ? 'text-[#ef4444] line-through px-1 font-mono' : 'text-[#888] px-1 font-mono'}>
                                {line.type === 'added' ? '+ ' : line.type === 'removed' ? '- ' : '  '}{line.value}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                    {isExpanded && !hasDiff && <div className="text-[#555] italic text-[9px]">No differences.</div>}
                  </VersionItem>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
});
