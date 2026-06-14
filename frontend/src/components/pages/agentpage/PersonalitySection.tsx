import { useState, useEffect } from "react"
import { getAgent, getPersonality, updateCommitment, updateExpertise, updateAspirationalTraits } from "../../../api/client"
import type { PersonalityResponse, PersonalityCommitment, PersonalityExpertise } from "../../../api/client"


/* ── Sub-component: Traits Panel ── */

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

  if (!aspirationalTraits || Object.keys(aspirationalTraits).length === 0) {
    return (
      <div className="p-6 text-center text-[#666] text-[11px] italic">
        No aspirational trait data available yet.
      </div>
    )
  }

  const handleEdit = () => {
    const init: Record<string, string> = {}
    keys.forEach((k) => {
      init[k] = String(aspirationalTraits[k] ?? 0.5)
    })
    setValues(init)
    setEditing(true)
  }

  const handleSave = async () => {
    setSaving(true)
    const traits: Record<string, number> = {}
    keys.forEach((k) => {
      traits[k] = parseFloat(values[k] || "0.5")
    })
    await updateAspirationalTraits(traits)
    setSaving(false)
    setEditing(false)
  }

  const handleCancel = () => {
    setEditing(false)
  }

  const labelMap: Record<string, string> = {
    curiosity: "Curiosity",
    skepticism: "Skepticism",
    creativity: "Creativity",
    precision: "Precision",
    critical_rigor: "Critical Rigor",
    playfulness: "Playfulness",
    reserve: "Reserve",
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-[#a78bfa] font-bold uppercase tracking-wider">
          Aspirational Trait Attractors
        </span>
        {agentFlux && !editing && (
          <button
            onClick={handleEdit}
            className="text-[10px] text-[#666] hover:text-[#a892ee] cursor-pointer"
          >
            [edit]
          </button>
        )}
      </div>

      <div className="grid grid-cols-4 gap-2">
        {keys.map((k) => (
          <div key={k} className="bg-[#0a0a0f] border border-[#1a1a2e] rounded px-3 py-2">
            <div className="text-[10px] text-[#555] uppercase tracking-wider">{labelMap[k]}</div>
            {editing ? (
              <input
                type="number"
                min={0}
                max={1}
                step={0.01}
                value={values[k] || "0.5"}
                onChange={(e) => setValues({ ...values, [k]: e.target.value })}
                className="mt-1 w-full bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[13px] text-[#94a3b8] font-bold font-mono"
              />
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
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1 text-[10px] bg-[#a78bfa]/20 text-[#a78bfa] border border-[#a78bfa]/30 rounded hover:bg-[#a78bfa]/30 disabled:opacity-50 cursor-pointer"
          >
            {saving ? "Saving..." : "Save"}
          </button>
          <button
            onClick={handleCancel}
            className="px-3 py-1 text-[10px] text-[#666] border border-[#333] rounded hover:bg-[#111] cursor-pointer"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  )
}


/* ── Sub-component: Commitments Panel ── */

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

  const all = [...(commitments.active ?? []), ...(commitments.proto ?? []), ...(commitments.spectral ?? [])]

  if (all.length === 0) {
    return (
      <div className="p-6 text-center text-[#666] text-[11px] italic">
        No commitments seeded yet.
      </div>
    )
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

  const handleEditToggle = () => {
    if (!selected || !agentFlux) return
    setEditing(!editing)
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
    // Optimistically update local
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

  const stageBadge = (stage: string) => {
    switch (stage) {
      case "active": return { bg: "#22c55e20", text: "#22c55e", label: "active" }
      case "proto": return { bg: "#f59e0b20", text: "#f59e0b", label: "proto" }
      case "spectral": return { bg: "#6b728020", text: "#6b7280", label: "spectral" }
      default: return { bg: "#333", text: "#888", label: stage }
    }
  }

  return (
    <div className="flex gap-4">
      {/* List */}
      <div className="w-[38%] shrink-0 flex flex-col gap-1 max-h-[480px] overflow-y-auto">
        {all.map((c) => {
          const badge = stageBadge(c.lifecycle_stage)
          return (
            <button
              key={c.id}
              onClick={() => handleSelect(c)}
              className={`text-left px-3 py-2 rounded text-[11px] border cursor-pointer transition-colors ${
                selected?.id === c.id
                  ? "bg-[#1e1e2e] border-[#475569]/40 text-[#e2e8f0]"
                  : "border-transparent text-[#94a3b8]/60 hover:text-[#94a3b8] hover:bg-[#111]"
              }`}
            >
              <span className="font-bold">{c.label}</span>
              <span
                className="ml-2 px-1.5 py-0.5 rounded text-[9px] font-bold"
                style={{ backgroundColor: badge.bg, color: badge.text }}
              >
                {badge.label}
              </span>
              <div className="text-[9px] text-[#555] mt-0.5">
                mass: {c.ontological_mass?.toFixed(2) ?? "—"}
                {" · "}
                conf: {c.confidence?.toFixed(2) ?? "—"}
              </div>
            </button>
          )
        })}
      </div>

      {/* Detail */}
      <div className="flex-1 min-w-0">
        {selected ? (
          <div className="bg-[#0a0a0f] border border-[#1a1a2e] rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[12px] text-[#e2e8f0] font-bold">{selected.label}</span>
              {agentFlux && (
                <button
                  onClick={handleEditToggle}
                  className="text-[10px] text-[#666] hover:text-[#a892ee] cursor-pointer"
                >
                  [{editing ? "cancel edit" : "edit"}]
                </button>
              )}
            </div>

            {editing ? (
              <div className="space-y-2 mb-3">
                <textarea
                  value={editValues.statement}
                  onChange={(e) => setEditValues({ ...editValues, statement: e.target.value })}
                  rows={3}
                  className="w-full bg-[#1e1e2e] border border-[#475569]/40 rounded px-3 py-2 text-[11px] text-[#94a3b8] font-mono resize-none"
                />
                <div className="flex gap-2">
                  <select
                    value={editValues.lifecycle_stage}
                    onChange={(e) => setEditValues({ ...editValues, lifecycle_stage: e.target.value })}
                    className="bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[11px] text-[#94a3b8]"
                  >
                    <option value="active">active</option>
                    <option value="proto">proto</option>
                    <option value="spectral">spectral</option>
                  </select>
                  <input
                    type="number" min={0} max={1} step={0.01}
                    value={editValues.confidence}
                    onChange={(e) => setEditValues({ ...editValues, confidence: e.target.value })}
                    placeholder="confidence"
                    className="w-20 bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[11px] text-[#94a3b8]"
                  />
                  <input
                    type="number" min={0} max={10} step={0.1}
                    value={editValues.ontological_mass}
                    onChange={(e) => setEditValues({ ...editValues, ontological_mass: e.target.value })}
                    placeholder="mass"
                    className="w-20 bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[11px] text-[#94a3b8]"
                  />
                </div>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-3 py-1 text-[10px] bg-[#a78bfa]/20 text-[#a78bfa] border border-[#a78bfa]/30 rounded hover:bg-[#a78bfa]/30 disabled:opacity-50 cursor-pointer"
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            ) : (
              <p className="text-[11px] text-[#94a3b8]/70 leading-relaxed mb-3 italic">
                {selected.statement}
              </p>
            )}

            <div className="grid grid-cols-2 gap-2 text-[10px]">
              <div>
                <span className="text-[#555]">Stage:</span>{" "}
                <span className="text-[#94a3b8]">{selected.lifecycle_stage}</span>
              </div>
              <div>
                <span className="text-[#555]">Confidence:</span>{" "}
                <span className="text-[#94a3b8]">{selected.confidence?.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-[#555]">Mass:</span>{" "}
                <span className="text-[#94a3b8]">{selected.ontological_mass?.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-[#555]">ID:</span>{" "}
                <span className="text-[#555] text-[9px] font-mono">{selected.id?.slice(0, 12)}...</span>
              </div>
            </div>

            {(selected.nucleation_rationale || selected.collapse_rationale) && (
              <div className="mt-3 pt-3 border-t border-[#1a1a2e]">
                {selected.nucleation_rationale && (
                  <p className="text-[10px] text-[#555]">
                    <span className="text-[#f59e0b]">Nucleation:</span> {selected.nucleation_rationale}
                  </p>
                )}
                {selected.collapse_rationale && (
                  <p className="text-[10px] text-[#555]">
                    <span className="text-[#6b7280]">Collapse:</span> {selected.collapse_rationale}
                  </p>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="p-6 text-center text-[#666] text-[11px] italic">
            Select a commitment to view details.
          </div>
        )}
      </div>
    </div>
  )
}


/* ── Sub-component: Expertise Panel ── */

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

  const all = [...(expertise.active ?? []), ...(expertise.proto ?? []), ...(expertise.dormant ?? [])]

  if (all.length === 0) {
    return (
      <div className="p-6 text-center text-[#666] text-[11px] italic">
        No expertise domains seeded yet.
      </div>
    )
  }

  const handleSelect = (e: PersonalityExpertise) => {
    setSelected(e)
    setEditing(false)
    setEditValues({
      lifecycle_stage: e.lifecycle_stage || "active",
      ontological_mass: String(e.ontological_mass ?? 1),
      level_label: e.level_label || "developing",
    })
  }

  const handleEditToggle = () => {
    if (!selected || !agentFlux) return
    setEditing(!editing)
  }

  const handleSave = async () => {
    if (!selected) return
    setSaving(true)
    await updateExpertise(selected.id, {
      lifecycle_stage: editValues.lifecycle_stage,
      ontological_mass: parseFloat(editValues.ontological_mass),
      level_label: editValues.level_label,
    })
    setSelected({
      ...selected,
      lifecycle_stage: editValues.lifecycle_stage,
      ontological_mass: parseFloat(editValues.ontological_mass),
      level_label: editValues.level_label,
    })
    setSaving(false)
    setEditing(false)
  }

  const levelColor = (level: string) => {
    switch (level) {
      case "advanced": return "#22c55e"
      case "developing": return "#f59e0b"
      case "nascent": return "#6366f1"
      case "dormant": return "#6b7280"
      default: return "#888"
    }
  }

  return (
    <div className="flex gap-4">
      {/* List */}
      <div className="w-[38%] shrink-0 flex flex-col gap-1 max-h-[480px] overflow-y-auto">
        {all.map((e) => (
          <button
            key={e.id}
            onClick={() => handleSelect(e)}
            className={`text-left px-3 py-2 rounded text-[11px] border cursor-pointer transition-colors ${
              selected?.id === e.id
                ? "bg-[#1e1e2e] border-[#475569]/40 text-[#e2e8f0]"
                : "border-transparent text-[#94a3b8]/60 hover:text-[#94a3b8] hover:bg-[#111]"
            }`}
          >
            <span className="font-bold">{e.domain}</span>
            <span
              className="ml-2 text-[9px] font-bold"
              style={{ color: levelColor(e.level_label) }}
            >
              {e.level_label}
            </span>
            <div className="text-[9px] text-[#555] mt-0.5">
              mass: {e.ontological_mass?.toFixed(2) ?? "—"}
              {" · "}
              signals: {e.signal_count ?? 0}
            </div>
          </button>
        ))}
      </div>

      {/* Detail */}
      <div className="flex-1 min-w-0">
        {selected ? (
          <div className="bg-[#0a0a0f] border border-[#1a1a2e] rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[12px] text-[#e2e8f0] font-bold">{selected.domain}</span>
              {agentFlux && (
                <button
                  onClick={handleEditToggle}
                  className="text-[10px] text-[#666] hover:text-[#a892ee] cursor-pointer"
                >
                  [{editing ? "cancel edit" : "edit"}]
                </button>
              )}
            </div>

            {editing ? (
              <div className="space-y-2 mb-3">
                <div className="flex gap-2">
                  <select
                    value={editValues.lifecycle_stage}
                    onChange={(e) => setEditValues({ ...editValues, lifecycle_stage: e.target.value })}
                    className="bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[11px] text-[#94a3b8]"
                  >
                    <option value="active">active</option>
                    <option value="proto">proto</option>
                    <option value="dormant">dormant</option>
                  </select>
                  <select
                    value={editValues.level_label}
                    onChange={(e) => setEditValues({ ...editValues, level_label: e.target.value })}
                    className="bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[11px] text-[#94a3b8]"
                  >
                    <option value="nascent">nascent</option>
                    <option value="developing">developing</option>
                    <option value="advanced">advanced</option>
                    <option value="dormant">dormant</option>
                  </select>
                  <input
                    type="number" min={0} max={10} step={0.01}
                    value={editValues.ontological_mass}
                    onChange={(e) => setEditValues({ ...editValues, ontological_mass: e.target.value })}
                    placeholder="mass"
                    className="w-20 bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[11px] text-[#94a3b8]"
                  />
                </div>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-3 py-1 text-[10px] bg-[#a78bfa]/20 text-[#a78bfa] border border-[#a78bfa]/30 rounded hover:bg-[#a78bfa]/30 disabled:opacity-50 cursor-pointer"
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            ) : null}

            <div className="grid grid-cols-2 gap-2 text-[10px]">
              <div>
                <span className="text-[#555]">Stage:</span>{" "}
                <span className="text-[#94a3b8]">{selected.lifecycle_stage}</span>
              </div>
              <div>
                <span className="text-[#555]">Level:</span>{" "}
                <span className="text-[#94a3b8]" style={{ color: levelColor(selected.level_label) }}>
                  {selected.level_label}
                </span>
              </div>
              <div>
                <span className="text-[#555]">Mass:</span>{" "}
                <span className="text-[#94a3b8]">{selected.ontological_mass?.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-[#555]">Signals:</span>{" "}
                <span className="text-[#94a3b8]">{selected.signal_count ?? 0}</span>
              </div>
            </div>

            {selected.crystallization_rationale && (
              <div className="mt-3 pt-3 border-t border-[#1a1a2e]">
                <p className="text-[10px] text-[#555]">
                  <span className="text-[#f59e0b]">Crystallization:</span> {selected.crystallization_rationale}
                </p>
              </div>
            )}

            {selected.last_signal_at && (
              <div className="mt-1 text-[9px] text-[#444]">
                Last signal: {selected.last_signal_at}
              </div>
            )}
          </div>
        ) : (
          <div className="p-6 text-center text-[#666] text-[11px] italic">
            Select a domain to view details.
          </div>
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
