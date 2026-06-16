// NewResearchForm — create and dispatch a research task.
// Terminal aesthetic: no bg/border/rounded containers.

import React, { memo, useState } from "react"
import type { DispatchPayload } from "../../../api/research"

interface Props {
  onDispatch: (payload: DispatchPayload) => Promise<string | null>
  onClose: () => void
}

export const NewResearchForm = memo(function NewResearchForm({ onDispatch, onClose }: Props) {
  const [objective, setObjective] = useState("")
  const [advanced, setAdvanced] = useState(false)
  const [depth, setDepth] = useState(2)
  const [breadth, setBreadth] = useState(2)
  const [agonistic, setAgonistic] = useState(false)
  const [budget, setBudget] = useState(0.50)
  const [sending, setSending] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!objective.trim() || sending) return
    setSending(true)
    await onDispatch({
      objective: objective.trim(),
      max_depth: depth,
      max_breadth: breadth,
      is_agonistic: agonistic,
      budget_limit_usd: budget,
    })
    setSending(false)
    setObjective("")
    onClose()
  }

  return (
    <form onSubmit={handleSubmit} className="mb-4">
      <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-2">
        [new research]
      </div>

      {/* Objective */}
      <input
        type="text"
        value={objective}
        onChange={e => setObjective(e.target.value)}
        placeholder="Objective: What should we investigate?"
        className="w-full bg-transparent border-b border-[#222]/40 focus:border-[#444] outline-none text-[#ccc] text-xs font-mono py-1 mb-2"
        autoFocus
        disabled={sending}
      />

      {/* Advanced toggle */}
      <button
        type="button"
        onClick={() => setAdvanced(!advanced)}
        className="text-[#555] hover:text-[#777] text-[10px] font-mono mb-2"
      >
        [{advanced ? "▼ advanced" : "▶ advanced"}]
      </button>

      {advanced && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2 text-[10px] font-mono text-[#777]">
          <label className="flex items-center gap-1">
            depth:
            <select
              value={depth}
              onChange={e => setDepth(Number(e.target.value))}
              className="bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none"
            >
              {[1,2,3,4].map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-1">
            breadth:
            <select
              value={breadth}
              onChange={e => setBreadth(Number(e.target.value))}
              className="bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none"
            >
              {[1,2,3,4,6].map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={agonistic}
              onChange={e => setAgonistic(e.target.checked)}
              className="mr-1"
            />
            agonistic
          </label>
          <label className="flex items-center gap-1">
            budget: $
            <input
              type="number"
              value={budget}
              step={0.25}
              min={0.10}
              max={5.00}
              onChange={e => setBudget(Number(e.target.value))}
              className="w-16 bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none"
            />
          </label>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={!objective.trim() || sending}
          className="text-[#4ade80] hover:text-[#6ee7b0] disabled:text-[#333] text-xs font-mono transition-colors"
        >
          [{sending ? "dispatching..." : "▶ dispatch research"}]
        </button>
        <button
          type="button"
          onClick={onClose}
          disabled={sending}
          className="text-[#666] hover:text-[#888] text-xs font-mono transition-colors"
        >
          [cancel]
        </button>
      </div>
    </form>
  )
})
