// NewResearchForm — create and dispatch a research task.
// Terminal aesthetic, uses shared UI components.

import React, { memo, useState } from "react"
import type { DispatchPayload } from "../../../api/research"
import { TerminalInput, TerminalButton, TerminalHeader } from "../../UI"

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
      <TerminalHeader className="mb-2">[ new research ]</TerminalHeader>

      {/* Objective */}
      <TerminalInput
        value={objective}
        onChange={setObjective}
        placeholder="What should we investigate?"
        className="w-full mb-2"
      />

      {/* Advanced toggle */}
      <button
        type="button"
        onClick={() => setAdvanced(!advanced)}
        className="text-[#555] hover:text-[#777] text-[10px] font-mono mb-2 cursor-pointer select-none"
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
          className="text-[10px] text-[#4ade80] font-mono cursor-pointer select-none transition-colors disabled:text-[#333] disabled:cursor-not-allowed hover:text-[#6ee7b0]"
        >
          [{sending ? "dispatching..." : "▶ dispatch research"}]
        </button>
        <TerminalButton onClick={onClose} disabled={sending}>
          cancel
        </TerminalButton>
      </div>
    </form>
  )
})
