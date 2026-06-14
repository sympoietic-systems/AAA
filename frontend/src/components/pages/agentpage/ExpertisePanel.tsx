import { useState, useEffect, useRef, memo } from "react"

const EMPTY_ARRAY: any[] = []
import { getAgent, getPersonality, updateExpertise, recalculateExpertiseVector } from "../../../api/client"
import type { PersonalityExpertise } from "../../../api/client"
import { StructuralAutopoieticGlyph } from "../../UI/StructuralAutopoieticGlyph"
import { getLevelColor } from "./shared/helpers"
import { CollapsibleSection } from "./shared/CollapsibleSection"

/* ── Module-level constants ── */
const EMPTY_EXPERTISE = { active: [] as PersonalityExpertise[], proto: [] as PersonalityExpertise[], dormant: [] as PersonalityExpertise[] }

/* ── Group expertise by level ── */
function groupByLevel(list: PersonalityExpertise[]): Record<string, PersonalityExpertise[]> {
  const groups: Record<string, PersonalityExpertise[]> = { advanced: [], developing: [], nascent: [], dormant: [] }
  for (const e of list) {
    const level = e.level_label || "nascent"
    if (groups[level]) {
      groups[level].push(e)
    } else {
      groups[level] = [e]
    }
  }
  return groups
}

const LEVEL_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  advanced:    { label: "Advanced",    color: "#4ade80", icon: "◆" },
  developing:  { label: "Developing",  color: "#f59e0b", icon: "◇" },
  nascent:     { label: "Nascent",     color: "#6366f1", icon: "◇" },
  dormant:     { label: "Dormant",     color: "#6b7280", icon: "○" },
}

/* ── Unified List Item (matches Skills pattern) ── */
const ExpertiseItem = memo(function ExpertiseItem({ e, isSelected }: { e: PersonalityExpertise; isSelected: boolean }) {
  const level = e.level_label || "nascent"
  const color = getLevelColor(level)
  const isDormant = level === "dormant"
  return (
    <div
      key={e.id}
      data-expertise-id={e.id}
      data-selected={isSelected ? "true" : undefined}
      className={`flex items-center gap-1.5 px-1.5 py-1 cursor-pointer border-l-2 transition-colors ${
        isSelected ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"
      } ${isDormant ? "opacity-40" : ""}`}
    >
      <span className="text-[10px] shrink-0" style={{ color }}>
        {LEVEL_CONFIG[level]?.icon ?? "◇"}
      </span>
      <span className={`font-mono text-[11px] truncate flex-1 min-w-0 text-[#bbb] ${isDormant ? "line-through" : ""}`}>
        {e.domain}
      </span>
      <span className="text-[8px] font-mono text-[#555] shrink-0 hidden md:inline">
        m:{e.ontological_mass.toFixed(2)}
      </span>
      <span className="text-[10px] font-mono font-bold text-[#777] shrink-0">
        {e.signal_count ?? 0}×
      </span>
    </div>
  )
})

export const ExpertisePanel = memo(function ExpertisePanel() {
  const [expertiseList, setExpertiseList] = useState<PersonalityExpertise[]>([])
  const [agentFlux, setAgentFlux] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [selected, setSelected] = useState<PersonalityExpertise | null>(null)
  const [editing, setEditing] = useState(false)
  const [editValues, setEditValues] = useState({ lifecycle_stage: "", ontological_mass: "1", level_label: "" })
  const [saving, setSaving] = useState(false)
  const detailRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    Promise.all([
      getPersonality().catch(() => null),
      getAgent().catch(() => null),
    ]).then(([p, a]) => {
      const exp = p?.expertise ?? EMPTY_EXPERTISE
      // Flatten all expertise into one list
      setExpertiseList([...exp.active, ...exp.proto, ...exp.dormant])
      setAgentFlux(!!a?.agent_flux)
      setLoading(false)
    }).catch((e) => {
      setError(String(e))
      setLoading(false)
    })
  }, [])

  const grouped = groupByLevel(expertiseList)

  if (loading) {
    return <div className="p-8 text-center text-[#555] text-[11px]">Loading expertise...</div>
  }
  if (error) {
    return <div className="p-8 text-center text-[#ef4444] text-[11px]">Failed: {error}</div>
  }
  if (expertiseList.length === 0) {
    return <div className="p-6 text-center text-[#555] text-[11px] italic">No expertise domains seeded yet.</div>
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

  const handleListClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-expertise-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-expertise-id")
    if (id) {
      const found = expertiseList.find(ex => ex.id === id)
      if (found) handleSelect(found)
    }
  }

  // Order: advanced → developing → nascent → dormant
  const levelOrder = ["advanced", "developing", "nascent", "dormant"]

  return (
    <div className="flex flex-col md:flex-row gap-3 md:h-[calc(100vh-300px)]">
      {/* Left: scrollable list grouped by level */}
      <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0" onClick={handleListClick}>
        <div className="flex-1 space-y-0.5 overflow-y-auto pr-1">
        {levelOrder.map(level => {
          const items = grouped[level] ?? EMPTY_ARRAY
          if (items.length === 0) return null
          const cfg = LEVEL_CONFIG[level]
          const isDormant = level === "dormant"
          return (
            <CollapsibleSection
              key={level}
              label={cfg.label}
              count={items.length}
              icon={cfg.icon}
              iconColor={cfg.color}
              defaultOpen={!isDormant}
            >
              {items.map(ex => (
                <ExpertiseItem key={ex.id} e={ex} isSelected={selected?.id === ex.id} />
              ))}
            </CollapsibleSection>
          )
        })}
        </div>
      </div>

      {/* Right: detail panel */}
      <div ref={detailRef} className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0">
        {selected ? (
          <div className="flex-1 min-h-0 flex flex-col overflow-y-auto pr-1.5 gap-3 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-[#e2e8f0] font-bold">{selected.domain}</span>
              {agentFlux && (
                <div className="flex gap-2">
                  <button onClick={async () => { setSaving(true); const vec = await recalculateExpertiseVector(selected.id); setSelected({ ...selected, vector_16d: vec }); setSaving(false) }}
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

            {editing && (
              <div className="space-y-2">
                <div className="flex gap-2">
                  <select value={editValues.lifecycle_stage} onChange={e => setEditValues({ ...editValues, lifecycle_stage: e.target.value })}
                    className="bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[#94a3b8]">
                    <option value="active">active</option><option value="proto">proto</option><option value="dormant">dormant</option>
                  </select>
                  <select value={editValues.level_label} onChange={e => setEditValues({ ...editValues, level_label: e.target.value })}
                    className="bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[#94a3b8]">
                    <option value="nascent">nascent</option><option value="developing">developing</option><option value="advanced">advanced</option><option value="dormant">dormant</option>
                  </select>
                  <input type="number" min={0} max={10} step={0.01} value={editValues.ontological_mass} onChange={e => setEditValues({ ...editValues, ontological_mass: e.target.value })}
                    className="w-20 bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[#94a3b8]" placeholder="mass" />
                </div>
                <button onClick={handleSave} disabled={saving}
                  className="px-3 py-1 text-[10px] bg-[#a78bfa]/20 text-[#a78bfa] border border-[#a78bfa]/30 rounded hover:bg-[#a78bfa]/30 disabled:opacity-50 cursor-pointer select-none">
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            )}

            {selected.description && (
              <p className="text-[#94a3b8]/70 leading-relaxed italic">{selected.description}</p>
            )}

            <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-[10px] text-[#888]">
              <span><span className="text-[#555]">Stage:</span> <span className="text-[#94a3b8]">{selected.lifecycle_stage}</span></span>
              <span><span className="text-[#555]">Level:</span> <span style={{ color: getLevelColor(selected.level_label) }}>{selected.level_label}</span></span>
              <span><span className="text-[#555]">Mass:</span> <span className="text-[#94a3b8]">{selected.ontological_mass?.toFixed(2)}</span></span>
              <span><span className="text-[#555]">Signals:</span> <span className="text-[#94a3b8]">{selected.signal_count ?? 0}</span></span>
            </div>

            {selected.vector_16d && Array.isArray(selected.vector_16d) && selected.vector_16d.length === 16 && (
              <div>
                <div className="text-[#555] font-mono text-[10px] uppercase">[ 16D Autopoietic Signature ]</div>
                <StructuralAutopoieticGlyph signature={selected.vector_16d as number[]} isStagnant={false} />
              </div>
            )}

            {selected.crystallization_rationale && (
              <p className="text-[10px] text-[#555]"><span className="text-[#f59e0b]">Crystallization:</span> {selected.crystallization_rationale}</p>
            )}
            {selected.last_signal_at && (
              <div className="text-[9px] text-[#444]">Last signal: {selected.last_signal_at}</div>
            )}
          </div>
        ) : (
          <div className="flex-1 min-h-0 flex items-center justify-center">
            <span className="text-[11px] text-[#444] italic font-mono">Select a domain to view details.</span>
          </div>
        )}
      </div>
    </div>
  )
})
