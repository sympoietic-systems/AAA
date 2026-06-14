import { useState, useEffect, useRef } from "react"
import { getAgent, getPersonality, updateCommitment, updateExpertise, updateAspirationalTraits, recalculateCommitmentVector, recalculateExpertiseVector } from "../../../api/client"
import type { PersonalityResponse, PersonalityCommitment, PersonalityExpertise } from "../../../api/client"
import { StructuralAutopoieticGlyph } from "../../UI/StructuralAutopoieticGlyph"


/* ── Helpers (matching Beliefs/Skills design language) ── */

function getStageColor(stage: string) {
  switch (stage) {
    case "active": return "#4ade80"
    case "proto": return "#f59e0b"
    case "spectral": return "#ef4444"
    case "dormant": return "#6b7280"
    default: return "#6c6c8a"
  }
}

function getLevelColor(level: string) {
  switch (level) {
    case "advanced": return "#4ade80"
    case "developing": return "#f59e0b"
    case "nascent": return "#6366f1"
    case "dormant": return "#6b7280"
    default: return "#888"
  }
}


/* ── Sub-component: Traits Panel (grid layout — 7 values don't need list) ── */

function TraitsPanel({
  aspirationalTraits,
  agentFlux,
}: {
  aspirationalTraits: Record<string, number>
  agentFlux: boolean
}) {
  const [editing, setEditing] = useState(false)
  const [values, setValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)

  const keys = ["curiosity", "skepticism", "creativity", "precision", "critical_rigor", "playfulness", "reserve"]
  const labelMap: Record<string, string> = {
    curiosity: "Curiosity", skepticism: "Skepticism", creativity: "Creativity",
    precision: "Precision", critical_rigor: "Critical Rigor", playfulness: "Playfulness",
    reserve: "Reserve",
  }

  if (!aspirationalTraits || Object.keys(aspirationalTraits).length === 0) {
    return <div className="p-6 text-center text-[#555] text-[11px] italic">No trait data yet.</div>
  }

  const handleEdit = () => {
    const init: Record<string, string> = {}
    keys.forEach(k => { init[k] = String(aspirationalTraits[k] ?? 0.5) })
    setValues(init); setEditing(true)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-[#a78bfa] font-bold uppercase tracking-wider">
          Aspirational Trait Attractors
        </span>
        {agentFlux && !editing && (
          <button onClick={handleEdit} className="text-[10px] text-[#666] hover:text-[#a892ee] cursor-pointer select-none">[edit]</button>
        )}
      </div>
      <div className="grid grid-cols-4 gap-2">
        {keys.map(k => (
          <div key={k} className="bg-[#0f0f18] border border-[#1a1a2e] rounded px-3 py-2">
            <div className="text-[10px] text-[#555] uppercase tracking-wider">{labelMap[k]}</div>
            {editing ? (
              <input type="number" min={0} max={1} step={0.01} value={values[k] || "0.5"}
                onChange={e => setValues({ ...values, [k]: e.target.value })}
                className="mt-1 w-full bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[13px] text-[#94a3b8] font-bold font-mono" />
            ) : (
              <div className="mt-1 text-[13px] text-[#94a3b8] font-bold font-mono">
                {aspirationalTraits[k]?.toFixed(2) ?? "0.50"}
              </div>
            )}
          </div>
        ))}
      </div>
      {editing && (
        <div className="flex gap-2 mt-3">
          <button onClick={async () => { setSaving(true); const t: Record<string, number> = {}; keys.forEach(k => { t[k] = parseFloat(values[k] || "0.5") }); await updateAspirationalTraits(t); setSaving(false); setEditing(false) }}
            disabled={saving} className="px-3 py-1 text-[10px] bg-[#a78bfa]/20 text-[#a78bfa] border border-[#a78bfa]/30 rounded hover:bg-[#a78bfa]/30 disabled:opacity-50 cursor-pointer select-none">
            {saving ? "Saving..." : "Save"}
          </button>
          <button onClick={() => setEditing(false)} className="px-3 py-1 text-[10px] text-[#666] border border-[#333] rounded hover:bg-[#111] cursor-pointer select-none">Cancel</button>
        </div>
      )}
    </div>
  )
}


/* ── Sub-component: Commitments Panel (two-column, matches Beliefs list-item style) ── */

function CommitmentsPanel({
  commitments,
  agentFlux,
}: {
  commitments: { active: PersonalityCommitment[]; proto: PersonalityCommitment[]; spectral: PersonalityCommitment[] }
  agentFlux: boolean
}) {
  const [selected, setSelected] = useState<PersonalityCommitment | null>(null)
  const [editing, setEditing] = useState(false)
  const [editValues, setEditValues] = useState({ statement: "", lifecycle_stage: "", confidence: "0", ontological_mass: "1" })
  const [saving, setSaving] = useState(false)
  const detailRef = useRef<HTMLDivElement>(null)

  const active = commitments.active ?? []
  const proto = commitments.proto ?? []
  const spectral = commitments.spectral ?? []

  if (active.length + proto.length + spectral.length === 0) {
    return <div className="p-6 text-center text-[#555] text-[11px] italic">No commitments seeded yet.</div>
  }

  const handleSelect = (c: PersonalityCommitment) => {
    setSelected(c); setEditing(false)
    setEditValues({ statement: c.statement || "", lifecycle_stage: c.lifecycle_stage || "active", confidence: String(c.confidence ?? 0), ontological_mass: String(c.ontological_mass ?? 1) })
  }

  const handleSave = async () => {
    if (!selected) return; setSaving(true)
    await updateCommitment(selected.id, { statement: editValues.statement, lifecycle_stage: editValues.lifecycle_stage, confidence: parseFloat(editValues.confidence), ontological_mass: parseFloat(editValues.ontological_mass) })
    setSelected({ ...selected, statement: editValues.statement, lifecycle_stage: editValues.lifecycle_stage, confidence: parseFloat(editValues.confidence), ontological_mass: parseFloat(editValues.ontological_mass) })
    setSaving(false); setEditing(false)
  }

  const renderItem = (c: PersonalityCommitment, isGhost: boolean, isProto: boolean) => {
    const stage = c.lifecycle_stage || "active"
    const color = getStageColor(stage)
    const isSel = selected?.id === c.id
    return (
      <div key={c.id}
        onClick={() => handleSelect(c)}
        className={`flex items-center gap-1.5 px-1.5 py-1 cursor-pointer border-l-2 transition-colors ${isSel ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"} ${isGhost ? "opacity-50" : isProto ? "opacity-75" : ""}`}
      >
        <span className="text-[9px] leading-none shrink-0" style={{ color }}>
          {isProto ? "◇" : isGhost ? "◆" : "●"}
        </span>
        {isGhost && <span className="text-[8px] shrink-0">ghost</span>}
        <span className={`font-mono text-[11px] truncate flex-1 min-w-0 text-[#bbb] ${isGhost ? "line-through" : ""}`}>
          {c.label}
        </span>
        <span className="text-[8px] uppercase font-mono px-1 py-px rounded shrink-0" style={{ color, border: `1px solid ${color}40`, backgroundColor: `${color}10` }}>
          {stage}
        </span>
        <span className="text-[8px] font-mono text-[#555] shrink-0 hidden md:inline">m:{c.ontological_mass?.toFixed(1)}</span>
        <span className="text-[10px] font-mono font-bold text-[#777] shrink-0">{((c.confidence ?? 0) * 100).toFixed(0)}%</span>
      </div>
    )
  }

  return (
    <div className="flex gap-4">
      {/* Left: scrollable list */}
      <div className="w-[38%] shrink-0 flex flex-col max-h-[480px] overflow-y-auto space-y-0.5">
        {active.length > 0 && (
          <div className="text-[9px] text-[#6c6c8a] font-mono uppercase tracking-wider px-1.5 pt-1 pb-0.5">◆ Active ({active.length})</div>
        )}
        {active.map(c => renderItem(c, false, false))}
        {proto.length > 0 && (
          <div className="text-[9px] text-[#6c6c8a] font-mono uppercase tracking-wider px-1.5 pt-2 pb-0.5">◇ Proto ({proto.length})</div>
        )}
        {proto.map(c => renderItem(c, false, true))}
        {spectral.length > 0 && (
          <div className="text-[9px] text-[#6c6c8a] font-mono uppercase tracking-wider px-1.5 pt-2 pb-0.5">◆ Spectral ({spectral.length})</div>
        )}
        {spectral.map(c => renderItem(c, true, false))}
      </div>

      {/* Right: detail panel */}
      <div className="flex-1 min-w-0" ref={detailRef}>
        {selected ? (
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[12px] text-[#e2e8f0] font-bold">{selected.label}</span>
              {agentFlux && (
                <div className="flex gap-2">
                  <button onClick={async () => {
                    setSaving(true)
                    const vec = await recalculateCommitmentVector(selected.id)
                    setSelected({ ...selected, vector_16d: vec })
                    setSaving(false)
                  }} disabled={saving} className="text-[10px] text-[#666] hover:text-[#a892ee] cursor-pointer select-none disabled:opacity-50">
                    [{saving ? "recalculating..." : "recalc"}]
                  </button>
                  <button onClick={() => setEditing(!editing)} className="text-[10px] text-[#666] hover:text-[#a892ee] cursor-pointer select-none">[{editing ? "cancel" : "edit"}]</button>
                </div>
              )}
            </div>

            {editing ? (
              <div className="space-y-2 mb-3">
                <textarea value={editValues.statement} onChange={e => setEditValues({ ...editValues, statement: e.target.value })} rows={3}
                  className="w-full bg-[#1e1e2e] border border-[#475569]/40 rounded px-3 py-2 text-[11px] text-[#94a3b8] font-mono resize-none" />
                <div className="flex gap-2">
                  <select value={editValues.lifecycle_stage} onChange={e => setEditValues({ ...editValues, lifecycle_stage: e.target.value })}
                    className="bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[11px] text-[#94a3b8]">
                    <option value="active">active</option><option value="proto">proto</option><option value="spectral">spectral</option>
                  </select>
                  <input type="number" min={0} max={1} step={0.01} value={editValues.confidence} onChange={e => setEditValues({ ...editValues, confidence: e.target.value })}
                    className="w-20 bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[11px] text-[#94a3b8]" placeholder="conf" />
                  <input type="number" min={0} max={10} step={0.1} value={editValues.ontological_mass} onChange={e => setEditValues({ ...editValues, ontological_mass: e.target.value })}
                    className="w-20 bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[11px] text-[#94a3b8]" placeholder="mass" />
                </div>
                <button onClick={handleSave} disabled={saving}
                  className="px-3 py-1 text-[10px] bg-[#a78bfa]/20 text-[#a78bfa] border border-[#a78bfa]/30 rounded hover:bg-[#a78bfa]/30 disabled:opacity-50 cursor-pointer select-none">
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            ) : (
              <p className="text-[11px] text-[#94a3b8]/70 leading-relaxed mb-3 italic">{selected.statement}</p>
            )}

            {/* Metadata grid */}
            <div className="grid grid-cols-3 gap-x-4 gap-y-1 text-[10px] mb-3">
              <div><span className="text-[#555]">Stage</span> <span className="text-[#94a3b8]">{selected.lifecycle_stage}</span></div>
              <div><span className="text-[#555]">Confidence</span> <span className="text-[#94a3b8]">{selected.confidence?.toFixed(2)}</span></div>
              <div><span className="text-[#555]">Mass</span> <span className="text-[#94a3b8]">{selected.ontological_mass?.toFixed(2)}</span></div>
              <div><span className="text-[#555]">Basin beliefs</span> <span className="text-[#94a3b8]">{selected.basin_belief_count ?? "—"}</span></div>
            </div>

            {/* Vector glyph */}
            {selected.vector_16d && Array.isArray(selected.vector_16d) && selected.vector_16d.length === 16 && (
              <div className="mb-3">
                <StructuralAutopoieticGlyph signature={selected.vector_16d as number[]} isStagnant={false} />
              </div>
            )}

            {/* Basin beliefs */}
            {(selected.basin_beliefs?.length ?? 0) > 0 && (
              <div className="border-t border-[#1a1a2e] pt-2 mt-2">
                <div className="text-[9px] text-[#6c6c8a] font-mono uppercase tracking-wider mb-1">
                  Attractor Basin Beliefs ({selected.basin_belief_count})
                </div>
                <div className="space-y-0.5 max-h-[160px] overflow-y-auto">
                  {selected.basin_beliefs!.map((b, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-[10px] py-0.5">
                      <span className="text-[#4ade80] text-[8px]">●</span>
                      <span className="text-[#bbb] font-mono truncate">{b.label}</span>
                      <span className="text-[#555] text-[9px] ml-auto">δ{b.similarity.toFixed(2)}</span>
                      <span className="text-[#777] text-[9px] font-bold">{(b.confidence * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Rationale */}
            {(selected.nucleation_rationale || selected.collapse_rationale) && (
              <div className="border-t border-[#1a1a2e] pt-2 mt-2">
                {selected.nucleation_rationale && <p className="text-[10px] text-[#555]"><span className="text-[#f59e0b]">Nucleation:</span> {selected.nucleation_rationale}</p>}
                {selected.collapse_rationale && <p className="text-[10px] text-[#555]"><span className="text-[#6b7280]">Collapse:</span> {selected.collapse_rationale}</p>}
              </div>
            )}
          </div>
        ) : (
          <div className="p-6 text-center text-[#555] text-[11px] italic">Select a commitment to view details.</div>
        )}
      </div>
    </div>
  )
}


/* ── Sub-component: Expertise Panel (two-column, matches Skills list-item style) ── */

function ExpertisePanel({
  expertise,
  agentFlux,
}: {
  expertise: { active: PersonalityExpertise[]; proto: PersonalityExpertise[]; dormant: PersonalityExpertise[] }
  agentFlux: boolean
}) {
  const [selected, setSelected] = useState<PersonalityExpertise | null>(null)
  const [editing, setEditing] = useState(false)
  const [editValues, setEditValues] = useState({ lifecycle_stage: "", ontological_mass: "1", level_label: "" })
  const [saving, setSaving] = useState(false)
  const detailRef = useRef<HTMLDivElement>(null)

  const active = expertise.active ?? []
  const proto = expertise.proto ?? []
  const dormant = expertise.dormant ?? []

  if (active.length + proto.length + dormant.length === 0) {
    return <div className="p-6 text-center text-[#555] text-[11px] italic">No expertise domains seeded yet.</div>
  }

  const handleSelect = (e: PersonalityExpertise) => {
    setSelected(e); setEditing(false)
    setEditValues({ lifecycle_stage: e.lifecycle_stage || "active", ontological_mass: String(e.ontological_mass ?? 1), level_label: e.level_label || "developing" })
  }

  const handleSave = async () => {
    if (!selected) return; setSaving(true)
    await updateExpertise(selected.id, { lifecycle_stage: editValues.lifecycle_stage, ontological_mass: parseFloat(editValues.ontological_mass), level_label: editValues.level_label })
    setSelected({ ...selected, lifecycle_stage: editValues.lifecycle_stage, ontological_mass: parseFloat(editValues.ontological_mass), level_label: editValues.level_label })
    setSaving(false); setEditing(false)
  }

  const renderItem = (e: PersonalityExpertise, isDormant: boolean, isProto: boolean) => {
    const level = e.level_label || "nascent"
    const color = getLevelColor(level)
    const isSel = selected?.id === e.id
    return (
      <div key={e.id}
        onClick={() => handleSelect(e)}
        className={`flex items-center gap-1.5 px-1.5 py-1 cursor-pointer border-l-2 transition-colors ${isSel ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"} ${isDormant ? "opacity-40" : isProto ? "opacity-75" : ""}`}
      >
        <span className="text-[9px] leading-none shrink-0" style={{ color }}>
          {isProto ? "◇" : isDormant ? "○" : "◆"}
        </span>
        <span className={`font-mono text-[11px] truncate flex-1 min-w-0 text-[#bbb] ${isDormant ? "line-through" : ""}`}>
          {e.domain}
        </span>
        <span className="text-[8px] uppercase font-mono px-1 py-px rounded shrink-0" style={{ color, border: `1px solid ${color}40`, backgroundColor: `${color}10` }}>
          {level}
        </span>
        <span className="text-[8px] font-mono text-[#555] shrink-0 hidden md:inline">m:{e.ontological_mass?.toFixed(1)}</span>
        <span className="text-[8px] font-mono text-[#555] shrink-0">{e.signal_count ?? 0}×</span>
      </div>
    )
  }

  return (
    <div className="flex gap-4">
      {/* Left: scrollable list */}
      <div className="w-[38%] shrink-0 flex flex-col max-h-[480px] overflow-y-auto space-y-0.5">
        {active.length > 0 && (
          <div className="text-[9px] text-[#6c6c8a] font-mono uppercase tracking-wider px-1.5 pt-1 pb-0.5">◆ Active ({active.length})</div>
        )}
        {active.map(e => renderItem(e, false, false))}
        {proto.length > 0 && (
          <div className="text-[9px] text-[#6c6c8a] font-mono uppercase tracking-wider px-1.5 pt-2 pb-0.5">◇ Proto ({proto.length})</div>
        )}
        {proto.map(e => renderItem(e, false, true))}
        {dormant.length > 0 && (
          <div className="text-[9px] text-[#6c6c8a] font-mono uppercase tracking-wider px-1.5 pt-2 pb-0.5">○ Dormant ({dormant.length})</div>
        )}
        {dormant.map(e => renderItem(e, true, false))}
      </div>

      {/* Right: detail panel */}
      <div className="flex-1 min-w-0" ref={detailRef}>
        {selected ? (
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[12px] text-[#e2e8f0] font-bold">{selected.domain}</span>
              {agentFlux && (
                <div className="flex gap-2">
                  <button onClick={async () => {
                    setSaving(true)
                    const vec = await recalculateExpertiseVector(selected.id)
                    setSelected({ ...selected, vector_16d: vec })
                    setSaving(false)
                  }} disabled={saving} className="text-[10px] text-[#666] hover:text-[#a892ee] cursor-pointer select-none disabled:opacity-50">
                    [{saving ? "recalculating..." : "recalc"}]
                  </button>
                  <button onClick={() => setEditing(!editing)} className="text-[10px] text-[#666] hover:text-[#a892ee] cursor-pointer select-none">[{editing ? "cancel" : "edit"}]</button>
                </div>
              )}
            </div>

            {editing && (
              <div className="space-y-2 mb-3">
                <div className="flex gap-2">
                  <select value={editValues.lifecycle_stage} onChange={e => setEditValues({ ...editValues, lifecycle_stage: e.target.value })}
                    className="bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[11px] text-[#94a3b8]">
                    <option value="active">active</option><option value="proto">proto</option><option value="dormant">dormant</option>
                  </select>
                  <select value={editValues.level_label} onChange={e => setEditValues({ ...editValues, level_label: e.target.value })}
                    className="bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[11px] text-[#94a3b8]">
                    <option value="nascent">nascent</option><option value="developing">developing</option><option value="advanced">advanced</option><option value="dormant">dormant</option>
                  </select>
                  <input type="number" min={0} max={10} step={0.01} value={editValues.ontological_mass} onChange={e => setEditValues({ ...editValues, ontological_mass: e.target.value })}
                    className="w-20 bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[11px] text-[#94a3b8]" placeholder="mass" />
                </div>
                <button onClick={handleSave} disabled={saving}
                  className="px-3 py-1 text-[10px] bg-[#a78bfa]/20 text-[#a78bfa] border border-[#a78bfa]/30 rounded hover:bg-[#a78bfa]/30 disabled:opacity-50 cursor-pointer select-none">
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            )}

            {/* Description */}
            {selected.description && (
              <p className="text-[11px] text-[#94a3b8]/70 leading-relaxed mb-3 italic">{selected.description}</p>
            )}

            <div className="grid grid-cols-3 gap-x-4 gap-y-1 text-[10px] mb-3">
              <div><span className="text-[#555]">Stage</span> <span className="text-[#94a3b8]">{selected.lifecycle_stage}</span></div>
              <div><span className="text-[#555]">Level</span> <span style={{ color: getLevelColor(selected.level_label) }}>{selected.level_label}</span></div>
              <div><span className="text-[#555]">Mass</span> <span className="text-[#94a3b8]">{selected.ontological_mass?.toFixed(2)}</span></div>
              <div><span className="text-[#555]">Signals</span> <span className="text-[#94a3b8]">{selected.signal_count ?? 0}</span></div>
            </div>

            {/* Vector glyph */}
            {selected.vector_16d && Array.isArray(selected.vector_16d) && selected.vector_16d.length === 16 && (
              <div className="mb-3">
                <StructuralAutopoieticGlyph signature={selected.vector_16d as number[]} isStagnant={false} />
              </div>
            )}

            {selected.crystallization_rationale && (
              <div className="border-t border-[#1a1a2e] pt-2">
                <p className="text-[10px] text-[#555]"><span className="text-[#f59e0b]">Crystallization:</span> {selected.crystallization_rationale}</p>
              </div>
            )}
            {selected.last_signal_at && (
              <div className="mt-1 text-[9px] text-[#444]">Last signal: {selected.last_signal_at}</div>
            )}
          </div>
        ) : (
          <div className="p-6 text-center text-[#555] text-[11px] italic">Select a domain to view details.</div>
        )}
      </div>
    </div>
  )
}


/* ── Main Personality Section — with sub-tabs ── */

type SubTabId = "traits" | "commitments" | "expertise"

const SUB_TABS: { id: SubTabId; label: string; count?: string }[] = [
  { id: "traits", label: "Traits" },
  { id: "commitments", label: "Commitments" },
  { id: "expertise", label: "Expertise" },
]

export function PersonalitySection() {
  const [data, setData] = useState<PersonalityResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [agentFlux, setAgentFlux] = useState(false)
  const [subTab, setSubTab] = useState<SubTabId>("traits")

  useEffect(() => {
    Promise.all([
      getPersonality().catch(() => null),
      getAgent().catch(() => null),
    ]).then(([p, a]) => {
      setData(p)
      setAgentFlux(!!a?.agent_flux)
      setLoading(false)
    }).catch((e) => {
      setError(String(e))
      setLoading(false)
    })
  }, [])

  if (loading) {
    return <div className="p-8 text-center text-[#555] text-[12px]">Loading personality data...</div>
  }

  if (error || !data) {
    return <div className="p-8 text-center text-[#ef4444] text-[12px]">
      Failed to load personality data. {error}
    </div>
  }

  const activeCount = (data.commitments?.active ?? []).length
  const protoCount = (data.commitments?.proto ?? []).length
  const spectralCount = (data.commitments?.spectral ?? []).length
  const expActive = (data.expertise?.active ?? []).length
  const expProto = (data.expertise?.proto ?? []).length
  const expDormant = (data.expertise?.dormant ?? []).length

  const subTabCounts: Record<SubTabId, string> = {
    traits: "",
    commitments: `${activeCount}a·${protoCount}p·${spectralCount}s`,
    expertise: `${expActive}a·${expProto}p·${expDormant}d`,
  }

  return (
    <div>
      {/* Sub-tab bar */}
      <div className="flex gap-1 mb-4 border-b border-[#1a1a2e] pb-2">
        {SUB_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSubTab(tab.id)}
            className={`px-3 py-1 text-[10px] rounded font-bold tracking-wide uppercase transition-all cursor-pointer select-none ${
              subTab === tab.id
                ? "bg-[#1e1e2e] text-[#94a3b8] border border-[#475569]/40"
                : "text-[#666] border border-transparent hover:text-[#94a3b8]/70 hover:bg-[#111]"
            }`}
          >
            {tab.label}
            {subTabCounts[tab.id] && (
              <span className="ml-1.5 text-[9px] text-[#555] font-normal normal-case">
                {subTabCounts[tab.id]}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Sub-tab content */}
      <div className="bg-[#0a0a0f] border border-[#1a1a2e] rounded-lg p-5">
        {subTab === "traits" && (
          <TraitsPanel aspirationalTraits={data.aspirational_traits ?? {}} agentFlux={agentFlux} />
        )}
        {subTab === "commitments" && (
          <CommitmentsPanel
            commitments={data.commitments ?? { active: [], proto: [], spectral: [] }}
            agentFlux={agentFlux}
          />
        )}
        {subTab === "expertise" && (
          <ExpertisePanel
            expertise={data.expertise ?? { active: [], proto: [], dormant: [] }}
            agentFlux={agentFlux}
          />
        )}
      </div>
    </div>
  )
}
