// NewResearchForm — create and dispatch a research task.
// Terminal aesthetic, uses shared UI components.

import React, { memo, useState, useEffect } from "react"
import type { DispatchPayload, IndexedFile } from "../../../api/research"
import { listIndexedFiles } from "../../../api/research"
import { TerminalInput, TerminalButton, TerminalHeader } from "../../UI"

interface Props {
  onDispatch: (payload: DispatchPayload) => Promise<string | null>
  onClose: () => void
  conversationId?: string
}

export const NewResearchForm = memo(function NewResearchForm({ onDispatch, onClose, conversationId }: Props) {
  const [objective, setObjective] = useState(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search)
      return params.get("objective") || ""
    }
    return ""
  })
  const [advanced, setAdvanced] = useState(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search)
      return params.has("depth") || params.has("breadth") || params.has("budget")
    }
    return false
  })
  const [depth, setDepth] = useState(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search)
      const d = parseInt(params.get("depth") || "")
      return isNaN(d) ? 2 : d
    }
    return 2
  })
  const [breadth, setBreadth] = useState(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search)
      const b = parseInt(params.get("breadth") || "")
      return isNaN(b) ? 2 : b
    }
    return 2
  })
  const [agonistic, setAgonistic] = useState(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search)
      return params.get("agonistic") === "true"
    }
    return false
  })
  const [budget, setBudget] = useState(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search)
      const bg = parseFloat(params.get("budget") || "")
      return isNaN(bg) ? 0.50 : bg
    }
    return 0.50
  })
  const [sending, setSending] = useState(false)
  const [files, setFiles] = useState<IndexedFile[]>([])
  const [selectedFile, setSelectedFile] = useState("")
  const [docMode, setDocMode] = useState<"full" | "chunks">("chunks")
  const [chunkLimit, setChunkLimit] = useState(5)

  useEffect(() => {
    if (conversationId) {
      listIndexedFiles(conversationId).then(r => setFiles(r.files)).catch(() => {})
    }
  }, [conversationId])

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
      inject_file_id: selectedFile || undefined,
      document_mode: selectedFile ? docMode : undefined,
      document_chunk_limit: selectedFile ? chunkLimit : undefined,
    })
    setSending(false)
    setObjective("")
    onClose()
  }

  const selectedFileInfo = files.find(f => f.file_name === selectedFile)

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

      {/* Document injector */}
      {files.length > 0 && (
        <div className="mb-2 text-[10px] text-[#555]">
          <div className="flex items-center gap-2 mb-1">
            <span>document:</span>
            <select
              value={selectedFile}
              onChange={e => setSelectedFile(e.target.value)}
              className="bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none flex-1"
            >
              <option value="">— none —</option>
              {files.map(f => (
                <option key={f.file_name} value={f.file_name}>
                  {f.file_name} ({f.file_type})
                </option>
              ))}
            </select>
          </div>
          {selectedFile && (
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
              <label className="flex items-center gap-1 text-[#666]">
                <select
                  value={docMode}
                  onChange={e => setDocMode(e.target.value as "full" | "chunks")}
                  className="bg-transparent border-b border-[#222]/40 text-[#777] outline-none"
                >
                  <option value="chunks">top chunks</option>
                  <option value="full">full analysis</option>
                </select>
              </label>
              {docMode === "chunks" && (
                <label className="flex items-center gap-1 text-[#666]">
                  n=
                  <select
                    value={chunkLimit}
                    onChange={e => setChunkLimit(Number(e.target.value))}
                    className="bg-transparent border-b border-[#222]/40 text-[#777] outline-none w-10"
                  >
                    {[3,5,8,10,15].map(n => <option key={n} value={n}>{n}</option>)}
                  </select>
                </label>
              )}
            </div>
          )}
          {selectedFileInfo?.summary && (
            <div className="text-[#444] mt-1 text-[9px] leading-relaxed max-h-14 overflow-y-auto">
              {selectedFileInfo.summary.slice(0, 200)}{(selectedFileInfo.summary.length > 200) ? "…" : ""}
            </div>
          )}
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
