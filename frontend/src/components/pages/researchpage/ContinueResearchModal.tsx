import { memo, useState, useEffect } from "react"
import type { ResearchTask, IndexedFile } from "../../../api/research"
import { continueResearch, listIndexedFiles } from "../../../api/research"
import { TerminalInput, TerminalButton } from "../../UI"

const CYCLE_OPTIONS = [1, 2, 3, 4, 5]
const CHUNK_OPTIONS = [3, 5, 8, 10, 15]

interface Props {
  task: ResearchTask
  onClose: () => void
}

export const ContinueResearchModal = memo(function ContinueResearchModal({ task, onClose }: Props) {
  const [objective, setObjective] = useState(task.objective)
  const [cycles, setCycles] = useState(1)
  const [budget, setBudget] = useState(task.budget_limit_usd || 0.50)
  const [files, setFiles] = useState<IndexedFile[]>([])
  const [selectedFile, setSelectedFile] = useState("")
  const [docMode, setDocMode] = useState<"full" | "chunks">("chunks")
  const [chunkLimit, setChunkLimit] = useState(5)
  const [sending, setSending] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  useEffect(() => {
    const convId = task.conversation_id
    if (convId) {
      listIndexedFiles(convId).then(r => setFiles(r.files)).catch(() => {})
    }
  }, [task.conversation_id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!objective.trim() || sending) return
    setSending(true)
    try {
      const result = await continueResearch({
        source_task_id: task.id,
        adjusted_objective: objective.trim(),
        additional_cycles: cycles,
        budget_limit_usd: budget,
        inject_file_id: selectedFile || undefined,
        document_mode: selectedFile ? docMode : undefined,
        document_chunk_limit: selectedFile ? chunkLimit : undefined,
      })
      window.location.href = `/research?id=${result.task_id}`
    } catch (err: any) {
      console.error("Continue research failed:", err)
      alert(`Failed to continue research: ${err.message || err}`)
    } finally {
      setSending(false)
    }
  }

  const selectedFileInfo = files.find(f => f.file_name === selectedFile)

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <form
        onSubmit={handleSubmit}
        className="w-[520px] max-h-[75vh] bg-[#0c0c0e]/95 border border-[#222]/40 rounded-sm shadow-2xl flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-2 border-b border-[#1a1a1a] select-none shrink-0">
          <span className="text-[9px] font-mono uppercase tracking-widest text-semantic-header">
            [ continue deeper ]
          </span>
          <button
            type="button"
            onClick={onClose}
            className="text-[9px] text-[#555] hover:text-[#888] font-mono cursor-pointer transition-colors"
          >
            [close]
          </button>
        </div>

        <div className="px-4 py-3 overflow-y-auto flex-1 space-y-3 font-mono">
          <div>
            <div className="text-[#6c6c8a] text-[9px] uppercase tracking-wider mb-1">Objective</div>
            <TerminalInput
              value={objective}
              onChange={setObjective}
              placeholder="Adjust the research objective..."
              className="w-full"
            />
          </div>

          <div className="flex flex-wrap gap-x-5 gap-y-1 text-[10px] text-[#777]">
            <label className="flex items-center gap-1.5">
              + cycles:
              <select
                value={cycles}
                onChange={e => setCycles(Number(e.target.value))}
                className="bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none text-[10px]"
              >
                {CYCLE_OPTIONS.map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
            <label className="flex items-center gap-1.5">
              budget: $
              <input
                type="number"
                value={budget}
                step={0.25}
                min={0.10}
                max={5.00}
                onChange={e => setBudget(Number(e.target.value))}
                className="w-16 bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none text-[10px]"
              />
            </label>
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-[#555] hover:text-[#777] cursor-pointer"
            >
              [{showAdvanced ? "▼" : "▶"} advanced]
            </button>
          </div>

          {showAdvanced && (
            <div className="space-y-2 pt-1 border-t border-[#1a1a1a]">
              <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ document injection ]</div>

              <select
                value={selectedFile}
                onChange={e => setSelectedFile(e.target.value)}
                className="w-full bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none text-[10px] py-0.5"
              >
                <option value="">— none —</option>
                {files.map(f => (
                  <option key={f.file_name} value={f.file_name}>
                    {f.file_name} ({f.file_type}, {f.token_count} tokens)
                  </option>
                ))}
              </select>

              {selectedFileInfo?.summary && (
                <div className="text-[#555] text-[9px] leading-relaxed max-h-16 overflow-y-auto">
                  {selectedFileInfo.summary.slice(0, 300)}{(selectedFileInfo.summary.length > 300) ? "…" : ""}
                </div>
              )}

              {selectedFile && (
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-[#777]">
                  <label className="flex items-center gap-1">
                    mode:
                    <select
                      value={docMode}
                      onChange={e => setDocMode(e.target.value as "full" | "chunks")}
                      className="bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none text-[10px]"
                    >
                      <option value="chunks">top chunks</option>
                      <option value="full">full analysis</option>
                    </select>
                  </label>
                  {docMode === "chunks" && (
                    <label className="flex items-center gap-1">
                      chunks:
                      <select
                        value={chunkLimit}
                        onChange={e => setChunkLimit(Number(e.target.value))}
                        className="bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none text-[10px]"
                      >
                        {CHUNK_OPTIONS.map(n => <option key={n} value={n}>{n}</option>)}
                      </select>
                    </label>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="text-[9px] text-[#444]">
            Previous depth: {task.max_depth} → New depth: {task.max_depth + cycles}
            {task.result_summary ? " · Prior synthesis included as context" : ""}
          </div>
        </div>

        <div className="flex items-center gap-3 px-4 py-2 border-t border-[#1a1a1a] shrink-0">
          <button
            type="submit"
            disabled={!objective.trim() || sending}
            className="text-[10px] text-[#4ade80] font-mono cursor-pointer select-none transition-colors disabled:text-[#333] disabled:cursor-not-allowed hover:text-[#6ee7b0]"
          >
            [{sending ? "dispatching..." : "▶ continue research"}]
          </button>
          <TerminalButton onClick={onClose} disabled={sending}>
            cancel
          </TerminalButton>
        </div>
      </form>
    </div>
  )
})
