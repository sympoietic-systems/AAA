import { useState, useEffect, useRef, memo } from "react"
import { getAgent, getPersonality, updateCommitment, recalculateCommitmentVector } from "../../../api/client"
import type { PersonalityCommitment } from "../../../api/client"
import { StructuralAutopoieticGlyph } from "../../UI/StructuralAutopoieticGlyph"
import { getStageColor } from "./shared/helpers"
import { CollapsibleSection } from "./shared/CollapsibleSection"

/* ── Module-level constants ── */
const EMPTY_COMMITMENTS = { active: [] as PersonalityCommitment[], proto: [] as PersonalityCommitment[], spectral: [] as PersonalityCommitment[] }

/* ── Unified List Item (matches Skills pattern) ── */
const CommitmentItem = memo(function CommitmentItem({ c, isSelected, isGhost, isProto }: {
  c: PersonalityCommitment; isSelected: boolean; isGhost: boolean; isProto: boolean
}) {
  const stage = c.lifecycle_stage || "active"
  const color = getStageColor(stage)
  return (
    <div
      key={c.id}
      onClick={() => {}}
      data-commitment-id={c.id}
      data-selected={isSelected ? "true" : undefined}
      className={`flex items-center gap-1.5 px-1.5 py-1 cursor-pointer border-l-2 transition-colors ${
        isSelected ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"
      } ${isGhost ? "opacity-50" : isProto ? "opacity-75" : ""}`}
    >
      <span className="text-[10px] shrink-0" style={{ color }}>
        {isProto ? "◇" : isGhost ? "◆" : "●"}
      </span>
      <span className={`font-mono text-[11px] truncate flex-1 min-w-0 text-[#bbb] ${isGhost ? "line-through" : ""}`}>
        {c.label}
      </span>
      <span className="text-[8px] font-mono text-[#555] shrink-0 hidden md:inline">
        m:{c.ontological_mass.toFixed(2)}
      </span>
      <span className="text-[10px] font-mono font-bold text-[#777] shrink-0">
        {((c.confidence ?? 0) * 100).toFixed(0)}%
      </span>
    </div>
  )
})

export const CommitmentsPanel = memo(function CommitmentsPanel() {
  const [commitments, setCommitments] = useState(EMPTY_COMMITMENTS)
  const [agentFlux, setAgentFlux] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [selected, setSelected] = useState<PersonalityCommitment | null>(null)
  const [editing, setEditing] = useState(false)
  const [editValues, setEditValues] = useState({ statement: "", lifecycle_stage: "", confidence: "0", ontological_mass: "1" })
  const [saving, setSaving] = useState(false)
  const detailRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    Promise.all([
      getPersonality().catch(() => null),
      getAgent().catch(() => null),
    ]).then(([p, a]) => {
      setCommitments(p?.commitments ?? EMPTY_COMMITMENTS)
      setAgentFlux(!!a?.agent_flux)
      setLoading(false)
    }).catch((e) => {
      setError(String(e))
      setLoading(false)
    })
  }, [])

  const active = commitments.active
  const proto = commitments.proto
  const spectral = commitments.spectral

  if (loading) {
    return <div className="p-8 text-center text-[#555] text-[11px]">Loading commitments...</div>
  }
  if (error) {
    return <div className="p-8 text-center text-[#ef4444] text-[11px]">Failed: {error}</div>
  }
  if (active.length + proto.length + spectral.length === 0) {
    return <div className="p-6 text-center text-[#555] text-[11px] italic">No commitments seeded yet.</div>
  }

  const handleSelect = (c: PersonalityCommitment) => {
    setSelected(c)
    setEditing(false)
    setEditValues({
      statement: c.statement || "",
      lifecycle_stage: c.lifecycle_stage || "active",
      confidence: String(c.confidence ?? 0),
      ontological_mass: String(c.ontological_mass ?? 1),
    })
  }

  const handleSave = async () => {
    if (!selected) return
    setSaving(true)
    await updateCommitment(selected.id, {
      statement: editValues.statement,
      lifecycle_stage: editValues.lifecycle_stage,
      confidence: parseFloat(editValues.confidence),
      ontological_mass: parseFloat(editValues.ontological_mass),
    })
    setSelected({
      ...selected,
      statement: editValues.statement,
      lifecycle_stage: editValues.lifecycle_stage,
      confidence: parseFloat(editValues.confidence),
      ontological_mass: parseFloat(editValues.ontological_mass),
    })
    setSaving(false)
    setEditing(false)
  }

  const handleListClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-commitment-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-commitment-id")
    if (id) {
      const all = [...active, ...proto, ...spectral]
      const found = all.find(c => c.id === id)
      if (found) handleSelect(found)
    }
  }

  return (
    <div className="flex flex-col md:flex-row gap-3 md:h-[calc(100vh-300px)]">
      {/* Left: scrollable list with collapsible sections */}
      <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0" onClick={handleListClick}>
        <div className="flex-1 space-y-0.5 overflow-y-auto pr-1">
        {active.length > 0 && (
          <CollapsibleSection label="Active" count={active.length} icon="●" iconColor="#4ade80">
            {active.map(c => (
              <CommitmentItem key={c.id} c={c} isSelected={selected?.id === c.id} isGhost={false} isProto={false} />
            ))}
          </CollapsibleSection>
        )}
        {proto.length > 0 && (
          <CollapsibleSection label="Proto" count={proto.length} icon="◇" iconColor="#f59e0b">
            {proto.map(c => (
              <CommitmentItem key={c.id} c={c} isSelected={selected?.id === c.id} isGhost={false} isProto />
            ))}
          </CollapsibleSection>
        )}
        {spectral.length > 0 && (
          <CollapsibleSection label="Spectral" count={spectral.length} icon="◇" iconColor="#ef4444" defaultOpen={false}>
            {spectral.map(c => (
              <CommitmentItem key={c.id} c={c} isSelected={selected?.id === c.id} isGhost isProto={false} />
            ))}
          </CollapsibleSection>
        )}
        </div>
      </div>

      {/* Right: detail panel */}
      <div ref={detailRef} className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0">
        {selected ? (
          <div className="flex-1 min-h-0 flex flex-col overflow-y-auto pr-1.5 gap-3 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-[#e2e8f0] font-bold">{selected.label}</span>
              {agentFlux && (
                <div className="flex gap-2">
                  <button onClick={async () => { setSaving(true); const vec = await recalculateCommitmentVector(selected.id); setSelected({ ...selected, vector_16d: vec }); setSaving(false) }}
                    disabled={saving} className="text-[10px] text-[#666] hover:text-[#a892ee] cursor-pointer select-none disabled:opacity-50">
                    [{saving ? "recalculating..." : "recalc"}]
                  </button>
                  <button onClick={() => setEditing(!editing)}
                    className="text-[10px] text-[#666] hover:text-[#a892ee] cursor-pointer select-none">
                    [{editing ? "cancel" : "edit"}]
                  </button>
                </div>
              )}
            </div>

            {editing ? (
              <div className="space-y-2">
                <textarea value={editValues.statement} onChange={e => setEditValues({ ...editValues, statement: e.target.value })} rows={3}
                  className="w-full bg-[#1e1e2e] border border-[#475569]/40 rounded px-3 py-2 text-[#94a3b8] font-mono resize-none" />
                <div className="flex gap-2">
                  <select value={editValues.lifecycle_stage} onChange={e => setEditValues({ ...editValues, lifecycle_stage: e.target.value })}
                    className="bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[#94a3b8]">
                    <option value="active">active</option><option value="proto">proto</option><option value="spectral">spectral</option>
                  </select>
                  <input type="number" min={0} max={1} step={0.01} value={editValues.confidence} onChange={e => setEditValues({ ...editValues, confidence: e.target.value })}
                    className="w-20 bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[#94a3b8]" placeholder="conf" />
                  <input type="number" min={0} max={10} step={0.1} value={editValues.ontological_mass} onChange={e => setEditValues({ ...editValues, ontological_mass: e.target.value })}
                    className="w-20 bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[#94a3b8]" placeholder="mass" />
                </div>
                <button onClick={handleSave} disabled={saving}
                  className="px-3 py-1 text-[10px] bg-[#a78bfa]/20 text-[#a78bfa] border border-[#a78bfa]/30 rounded hover:bg-[#a78bfa]/30 disabled:opacity-50 cursor-pointer select-none">
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            ) : (
              <p className="text-[#94a3b8]/70 leading-relaxed italic">{selected.statement}</p>
            )}

            <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-[10px] text-[#888]">
              <span><span className="text-[#555]">Stage:</span> <span className="text-[#94a3b8]">{selected.lifecycle_stage}</span></span>
              <span><span className="text-[#555]">Confidence:</span> <span className="text-[#94a3b8]">{selected.confidence?.toFixed(2)}</span></span>
              <span><span className="text-[#555]">Mass:</span> <span className="text-[#94a3b8]">{selected.ontological_mass?.toFixed(2)}</span></span>
              <span><span className="text-[#555]">Basin beliefs:</span> <span className="text-[#94a3b8]">{selected.basin_belief_count ?? "—"}</span></span>
            </div>

            {selected.vector_16d && Array.isArray(selected.vector_16d) && selected.vector_16d.length === 16 && (
              <div>
                <div className="text-[#555] font-mono text-[10px] uppercase">[ 16D Autopoietic Signature ]</div>
                <StructuralAutopoieticGlyph signature={selected.vector_16d as number[]} isStagnant={false} />
              </div>
            )}

            {(selected.basin_beliefs?.length ?? 0) > 0 && (
              <div>
                <div className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider">Attractor Basin Beliefs ({selected.basin_belief_count})</div>
                <div className="space-y-0.5 max-h-[160px] overflow-y-auto mt-1">
                  {selected.basin_beliefs!.map((b, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-[10px]">
                      <span className="text-[#4ade80] text-[8px]">●</span>
                      <span className="text-[#bbb] font-mono truncate">{b.label}</span>
                      <span className="text-[#555] text-[9px] ml-auto">δ{b.similarity.toFixed(2)}</span>
                      <span className="text-[#777] text-[9px] font-bold">{(b.confidence * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(selected.nucleation_rationale || selected.collapse_rationale) && (
              <div className="text-[10px] text-[#555]">
                {selected.nucleation_rationale && <p><span className="text-[#f59e0b]">Nucleation:</span> {selected.nucleation_rationale}</p>}
                {selected.collapse_rationale && <p><span className="text-[#6b7280]">Collapse:</span> {selected.collapse_rationale}</p>}
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 min-h-0 flex items-center justify-center">
            <span className="text-[11px] text-[#444] italic font-mono">Select a commitment to view details.</span>
          </div>
        )}
      </div>
    </div>
  )
})
