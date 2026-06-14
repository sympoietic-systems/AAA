import { useState, useEffect, memo } from "react"
import { getAgent, getPersonality, getBeliefs, updateAspirationalTraits } from "../../../api/client"
import type { SomaticStateInfo, EcosystemSnapshot } from "../../../api/client"
import { HealthMetrics } from "./shared/HealthMetrics"

/* ── Module-level constants (Section 3: stable references) ── */
const TRAIT_KEYS = ["curiosity", "skepticism", "creativity", "precision", "critical_rigor", "playfulness", "reserve"] as const
const TRAIT_LABEL_MAP: Record<string, string> = {
  curiosity: "Curiosity", skepticism: "Skepticism", creativity: "Creativity",
  precision: "Precision", critical_rigor: "Critical Rigor", playfulness: "Playfulness",
  reserve: "Reserve",
}
const EMPTY_TRAITS: Record<string, number> = {}

export const TraitsPanel = memo(function TraitsPanel() {
  const [aspirationalTraits, setAspirationalTraits] = useState<Record<string, number>>(EMPTY_TRAITS)
  const [agentFlux, setAgentFlux] = useState(false)
  const [somatic, setSomatic] = useState<SomaticStateInfo | null>(null)
  const [ecosystem, setEcosystem] = useState<EcosystemSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [editing, setEditing] = useState(false)
  const [values, setValues] = useState<Record<string, string>>(EMPTY_TRAITS as any)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    Promise.all([
      getPersonality().catch(() => null),
      getAgent().catch(() => null),
      getBeliefs(null as any).catch(() => null),
    ]).then(([p, a, b]) => {
      setAspirationalTraits(p?.aspirational_traits ?? EMPTY_TRAITS)
      setAgentFlux(!!a?.agent_flux)
      if (b) {
        setSomatic(b.somatic ?? null)
        setEcosystem(b.ecosystem ?? null)
      }
      setLoading(false)
    }).catch((e) => {
      setError(String(e))
      setLoading(false)
    })
  }, [])

  if (loading) {
    return <div className="p-8 text-center text-[#555] text-[12px]">Loading traits & health data...</div>
  }

  if (error) {
    return <div className="p-8 text-center text-[#ef4444] text-[12px]">Failed to load traits data. {error}</div>
  }

  const handleEdit = () => {
    const init: Record<string, string> = {}
    TRAIT_KEYS.forEach(k => { init[k] = String(aspirationalTraits[k] ?? 0.5) })
    setValues(init)
    setEditing(true)
  }

  return (
    <div className="space-y-4">
      {/* Health Metrics — global agent state */}
      <HealthMetrics somatic={somatic} ecosystem={ecosystem} />

      {/* Aspirational Traits — simple inline style */}
      {Object.keys(aspirationalTraits).length > 0 ? (
        <div className="font-mono text-[10px]">
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">
            [ Aspirational Trait Attractors ]{" "}
            {agentFlux && !editing && (
              <button onClick={handleEdit} className="text-[#666] hover:text-[#a892ee] cursor-pointer select-none ml-1">
                [edit]
              </button>
            )}
          </div>
          {editing ? (
            <>
              <div className="grid grid-cols-4 gap-2 mt-1.5">
                {TRAIT_KEYS.map(k => (
                  <div key={k}>
                    <div className="text-[9px] text-[#555]">{TRAIT_LABEL_MAP[k]}</div>
                    <input
                      type="number" min={0} max={1} step={0.01}
                      value={values[k] || "0.5"}
                      onChange={e => setValues({ ...values, [k]: e.target.value })}
                      className="mt-0.5 w-full bg-[#1e1e2e] border border-[#475569]/40 rounded px-2 py-1 text-[12px] text-[#94a3b8] font-bold font-mono"
                    />
                  </div>
                ))}
              </div>
              <div className="flex gap-2 mt-3">
                <button
                  onClick={async () => {
                    setSaving(true)
                    const t: Record<string, number> = {}
                    TRAIT_KEYS.forEach(k => { t[k] = parseFloat(values[k] || "0.5") })
                    await updateAspirationalTraits(t)
                    setSaving(false); setEditing(false)
                  }}
                  disabled={saving}
                  className="px-3 py-1 text-[10px] bg-[#a78bfa]/20 text-[#a78bfa] border border-[#a78bfa]/30 rounded hover:bg-[#a78bfa]/30 disabled:opacity-50 cursor-pointer select-none"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
                <button onClick={() => setEditing(false)} className="px-3 py-1 text-[10px] text-[#666] border border-[#333] rounded hover:bg-[#111] cursor-pointer select-none">
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-0.5 md:gap-x-5 mt-0.5">
              {TRAIT_KEYS.map(k => (
                <span key={k}>
                  <span className="text-[#666]">{TRAIT_LABEL_MAP[k]}:</span>{" "}
                  <span className="text-[#ccc] font-bold">{aspirationalTraits[k]?.toFixed(2) ?? "0.50"}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="text-[#555] text-[11px] italic">No trait data yet.</div>
      )}
    </div>
  )
})
