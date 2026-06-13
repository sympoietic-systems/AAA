import { useState } from "react"
import { createBelief } from "../../../../api/client"
import type { BeliefNodeInfo } from "../../../../api/client"

interface NewBeliefFormProps {
  onCancel: () => void
  onCreate: (newBelief: BeliefNodeInfo) => void
}

export function NewBeliefForm({ onCancel, onCreate }: NewBeliefFormProps) {
  const [label, setLabel] = useState("")
  const [statement, setStatement] = useState("")
  const [confidence, setConfidence] = useState(0.5)
  const [ontologicalMass, setOntologicalMass] = useState(0.5)
  const [lifecycleStage, setLifecycleStage] = useState("crystallized")
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const handleSave = async () => {
    if (!label.trim()) {
      setSaveError("Label is required")
      return
    }
    if (!/^[a-z0-9-_]+$/.test(label.trim())) {
      setSaveError("Label must contain only lowercase letters, numbers, hyphens, and underscores")
      return
    }
    if (!statement.trim()) {
      setSaveError("Statement is required")
      return
    }

    setIsSaving(true)
    setSaveError(null)
    try {
      const result = await createBelief({
        label: label.trim(),
        statement: statement.trim(),
        confidence,
        ontological_mass: ontologicalMass,
        lifecycle_stage: lifecycleStage,
        agent_id: "symbia",
      })

      if (result.status === "ok") {
        const newB: BeliefNodeInfo = {
          id: result.belief_id,
          label: result.label,
          statement: statement.trim(),
          category: "general",
          confidence,
          ontological_mass: ontologicalMass,
          version: 1,
          vector_16d: "[]",
          origin: "authored",
          lifecycle_stage: lifecycleStage,
          last_reinforced_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          events: []
        }
        onCreate(newB)
      } else {
        setSaveError("Failed to save belief")
      }
    } catch (e: any) {
      setSaveError(e.message || String(e))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50 p-2.5 gap-2.5 text-[11px] font-mono">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1f1f2e]/30 pb-1.5 shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[10px] shrink-0 text-[#a78bfa]">◇</span>
          <span className="font-mono text-[11px] font-bold text-[#ccc] truncate">CREATE NEW BELIEF</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="text-[10px] text-[#4ade80] hover:text-[#4ade80]/80 disabled:text-[#555] transition-colors cursor-pointer select-none font-bold"
          >
            {isSaving ? "[saving...]" : "[save]"}
          </button>
          <button
            onClick={onCancel}
            disabled={isSaving}
            className="text-[10px] text-[#ef4444] hover:text-[#ef4444]/80 disabled:text-[#555] transition-colors cursor-pointer select-none font-bold"
          >
            [cancel]
          </button>
        </div>
      </div>

      {saveError && (
        <div className="text-[10px] text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/20 p-1.5 rounded shrink-0">
          {saveError}
        </div>
      )}

      {/* Form fields */}
      <div className="flex-1 flex flex-col gap-2.5 min-h-0 overflow-y-auto pr-1">
        {/* Label */}
        <div className="shrink-0 flex flex-col gap-1">
          <label className="text-[#555] text-[10px] uppercase font-bold">[ Belief Label ]</label>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            disabled={isSaving}
            placeholder="e.g. autopoietic-closure"
            className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] px-2 py-1.5 rounded text-[11px] font-mono w-full focus:outline-none focus:border-[#a78bfa]/50"
          />
        </div>

        {/* Statement */}
        <div className="shrink-0 flex flex-col gap-1">
          <label className="text-[#555] text-[10px] uppercase font-bold">[ Statement / core thesis ]</label>
          <textarea
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            disabled={isSaving}
            placeholder="Core thesis statement representing this belief node."
            className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] p-2 rounded text-[11px] font-serif leading-relaxed w-full focus:outline-none focus:border-[#a78bfa]/50 min-h-[60px] resize-y"
          />
        </div>

        {/* Confidence slider */}
        <div className="shrink-0 flex flex-col gap-1">
          <label className="text-[#555] text-[10px] uppercase font-bold">
            [ Confidence: {(confidence * 100).toFixed(0)}% ]
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={confidence}
            onChange={(e) => setConfidence(parseFloat(e.target.value))}
            disabled={isSaving}
            className="accent-[#a78bfa] w-full cursor-pointer bg-[#14141c] h-1 rounded"
          />
        </div>

        {/* Ontological Mass slider */}
        <div className="shrink-0 flex flex-col gap-1">
          <label className="text-[#555] text-[10px] uppercase font-bold">
            [ Ontological Mass: {ontologicalMass.toFixed(2)} ]
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={ontologicalMass}
            onChange={(e) => setOntologicalMass(parseFloat(e.target.value))}
            disabled={isSaving}
            className="accent-[#a78bfa] w-full cursor-pointer bg-[#14141c] h-1 rounded"
          />
        </div>

        {/* Lifecycle Stage select */}
        <div className="shrink-0 flex flex-col gap-1">
          <label className="text-[#555] text-[10px] uppercase font-bold">[ Lifecycle Stage ]</label>
          <select
            value={lifecycleStage}
            onChange={(e) => setLifecycleStage(e.target.value)}
            disabled={isSaving}
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
