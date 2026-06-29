import { memo, useState, useEffect, useRef, useCallback } from "react"
import type { ResearchTask, IndexedFile } from "../../../api/research"
import { continueTask, listIndexedFiles } from "../../../api/research"
import type { ConversationInfo } from "../../../api/conversations"
import { listConversations, uploadFiles, getConversationFiles } from "../../../api/conversations"
import { TerminalInput, TerminalButton } from "../../UI"

const CYCLE_OPTIONS = [1, 2, 3, 4, 5]
const CHUNK_OPTIONS = [3, 5, 8, 10, 15]
const POLL_INTERVAL = 2000

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

  const [conversations, setConversations] = useState<ConversationInfo[]>([])
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadConvId, setUploadConvId] = useState(task.conversation_id || "")
  const [uploadStatus, setUploadStatus] = useState<"" | "uploading" | "indexing" | "ready" | "error">("")
  const [uploadError, setUploadError] = useState("")
  const [uploadedFileName, setUploadedFileName] = useState("")
  const [uploadedConvId, setUploadedConvId] = useState("")
  const [showUpload, setShowUpload] = useState(false)

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    listIndexedFiles().then(r => setFiles(r.files)).catch(() => {})
  }, [])

  useEffect(() => {
    listConversations().then(r => setConversations(r.conversations || [])).catch(() => {})
  }, [])

  useEffect(() => {
    setUploadConvId(task.conversation_id || "")
  }, [task.conversation_id])

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  useEffect(() => {
    return () => stopPolling()
  }, [stopPolling])

  const startPolling = useCallback((convId: string, targetFileName: string) => {
    stopPolling()
    pollTimerRef.current = setInterval(async () => {
      try {
        const res = await getConversationFiles(convId)
        const target = res.files.find(f => f.file_name === targetFileName)
        if (!target) {
          setUploadStatus("error")
          setUploadError("File not found after upload")
          stopPolling()
          return
        }
        if (target.status === "ready") {
          setUploadStatus("ready")
          setUploadedFileName(target.file_name)
          setUploadedConvId(convId)
          stopPolling()
        } else if (target.status === "error") {
          setUploadStatus("error")
          setUploadError("Indexing failed")
          stopPolling()
        } else {
          setUploadStatus("indexing")
        }
      } catch {
        // silent
      }
    }, POLL_INTERVAL)
  }, [stopPolling])

  const handleFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadFile(file)
    setUploadStatus("uploading")
    setUploadError("")

    let targetConvId = uploadConvId
    if (!targetConvId || targetConvId === "new") {
      targetConvId = "new"
    }

    try {
      const res = await uploadFiles(targetConvId, [file])
      const returnedConvId = res.conversation_id
      setUploadedConvId(returnedConvId)
      if (targetConvId === "new" || !task.conversation_id) {
        setUploadConvId(returnedConvId)
      }
      startPolling(returnedConvId, file.name)
    } catch (err: any) {
      setUploadStatus("error")
      setUploadError(err.message || "Upload failed")
    }
  }, [uploadConvId, task.conversation_id, startPolling])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!objective.trim() || sending) return
    setSending(true)

    const injectFileId = uploadedFileName || selectedFile || undefined
    let injectConvId = uploadedConvId || undefined
    if (!injectFileId) {
      injectConvId = undefined
    } else if (!uploadedConvId && selectedFile) {
      const found = files.find(f => f.file_name === selectedFile)
      injectConvId = found?.conversation_id
    }

    try {
      await continueTask(task.id, {
        adjusted_objective: objective.trim() !== task.objective ? objective.trim() : undefined,
        additional_cycles: cycles,
        budget_limit_usd: budget,
        inject_file_id: injectFileId,
        inject_conversation_id: injectConvId,
        document_mode: injectFileId ? docMode : undefined,
        document_chunk_limit: injectFileId ? chunkLimit : undefined,
      })
      onClose()
      window.location.reload()
    } catch (err: any) {
      console.error("Continue task failed:", err)
      alert(`Failed to continue task: ${err.message || err}`)
    } finally {
      setSending(false)
    }
  }

  const selectedFileInfo = files.find(f => f.file_name === selectedFile)
  const convList = conversations || []

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <form
        onSubmit={handleSubmit}
        className="bg-[#0e0e0e] border border-[#222] w-full max-w-lg mx-4 p-4 font-mono text-[10px] text-[#777]"
        onClick={e => e.stopPropagation()}
      >
        <div className="space-y-3">
          <div className="text-[#8a7d74] uppercase text-[9px] tracking-wider">
            [ continue research ]
          </div>

          <TerminalInput
            value={objective}
            onChange={setObjective}
            placeholder="Refine objective..."
            className="w-full"
          />

          <div className="flex flex-wrap gap-x-4 gap-y-1 items-center">
            <label className="flex items-center gap-1.5">
              +cycles:
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
                onChange={e => { setSelectedFile(e.target.value); if (e.target.value) { setUploadedFileName(""); setUploadedConvId(""); setUploadFile(null); setUploadStatus("") } }}
                className="w-full bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none text-[10px] py-0.5"
              >
                <option value="">— none —</option>
                {files.map(f => (
                  <option key={f.conversation_id + ":" + f.file_name} value={f.file_name}>
                    {f.file_name} ({f.file_type}, {f.token_count} tokens)
                  </option>
                ))}
              </select>

              {selectedFileInfo?.summary && !uploadedFileName && (
                <div className="text-[#555] text-[9px] leading-relaxed max-h-16 overflow-y-auto">
                  {selectedFileInfo.summary.slice(0, 300)}{(selectedFileInfo.summary.length > 300) ? "…" : ""}
                </div>
              )}

              {selectedFile && !uploadedFileName && (
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

              {/* Upload section */}
              <div>
                <button
                  type="button"
                  onClick={() => setShowUpload(!showUpload)}
                  className="text-[#555] hover:text-[#777] text-[9px] font-mono cursor-pointer select-none"
                >
                  [{showUpload ? "▼ upload file" : "▶ upload file"}]
                </button>

                {showUpload && (
                  <div className="mt-1 space-y-1.5">
                    <div className="flex items-center gap-2 text-[9px]">
                      <span>to:</span>
                      <select
                        value={uploadConvId}
                        onChange={e => setUploadConvId(e.target.value)}
                        disabled={uploadStatus === "uploading" || uploadStatus === "indexing"}
                        className="bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none"
                      >
                        <option value="">— select —</option>
                        {convList.map(c => (
                          <option key={c.id} value={c.id}>
                            {c.title || c.id.slice(0, 8)} {c.id === task.conversation_id ? "(current)" : ""}
                          </option>
                        ))}
                        <option value="new">—— create new ——</option>
                      </select>
                    </div>

                    <div className="flex items-center gap-2">
                      <input
                        ref={fileInputRef}
                        type="file"
                        onChange={handleFileChange}
                        className="hidden"
                        accept=".txt,.md,.pdf,.docx,.epub,.mobi,.jpg,.jpeg,.png,.gif,.webp,.bmp,.svg"
                      />
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploadStatus === "uploading" || uploadStatus === "indexing"}
                        className="text-[#b37e5d] hover:text-[#ff6b00] text-[9px] font-mono cursor-pointer select-none disabled:text-[#333] disabled:cursor-not-allowed"
                      >
                        [{uploadFile ? uploadFile.name.slice(0, 30) + (uploadFile.name.length > 30 ? "…" : "") : "choose file"}]
                      </button>
                    </div>

                    {uploadStatus === "uploading" && (
                      <div className="text-[#b89553] text-[9px] font-mono">Uploading...</div>
                    )}
                    {uploadStatus === "indexing" && (
                      <div className="text-[#b89553] text-[9px] font-mono animate-pulse">Indexing document...</div>
                    )}
                    {uploadStatus === "ready" && (
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-[#777]">
                        <span className="text-[#5c9e7a] text-[9px]">Ready</span>
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
                    {uploadStatus === "error" && (
                      <div className="text-semantic-red text-[9px] font-mono">{uploadError || "Upload failed"}</div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="text-[9px] text-[#444]">
            Depth: {task.max_depth} + {cycles} = {task.max_depth + cycles}
            {task.result_summary ? " · Prior synthesis included as planner context" : ""}
          </div>
        </div>

        <div className="flex items-center gap-3 px-4 py-2 border-t border-[#1a1a1a] shrink-0">
          <button
            type="submit"
            disabled={!objective.trim() || sending || uploadStatus === "uploading"}
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
