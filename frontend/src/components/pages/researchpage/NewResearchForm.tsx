// NewResearchForm — create and dispatch a research task.
// Terminal aesthetic, uses shared UI components.

import React, { memo, useState, useEffect, useRef, useCallback } from "react"
import type { DispatchPayload, IndexedFile } from "../../../api/research"
import { listIndexedFiles } from "../../../api/research"
import type { ConversationInfo } from "../../../api/conversations"
import { listConversations, uploadFiles, getConversationFiles } from "../../../api/conversations"
import { TerminalInput, TerminalButton, TerminalHeader } from "../../UI"

interface Props {
  onDispatch: (payload: DispatchPayload) => Promise<string | null>
  onClose: () => void
  conversationId?: string
}

const POLL_INTERVAL = 2000

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

  const [conversations, setConversations] = useState<ConversationInfo[]>([])
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadConvId, setUploadConvId] = useState(conversationId || "")
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
    setUploadConvId(conversationId || "")
  }, [conversationId])

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
      if (targetConvId === "new" || !conversationId) {
        setUploadConvId(returnedConvId)
      }
      startPolling(returnedConvId, file.name)
    } catch (err: any) {
      setUploadStatus("error")
      setUploadError(err.message || "Upload failed")
    }
  }, [uploadConvId, conversationId, startPolling])

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

    let convId = conversationId || undefined
    if (!convId && uploadedConvId && uploadConvId === uploadedConvId) {
      convId = uploadedConvId
    }

    await onDispatch({
      objective: objective.trim(),
      conversation_id: convId,
      max_depth: depth,
      max_breadth: breadth,
      is_agonistic: agonistic,
      budget_limit_usd: budget,
      inject_file_id: injectFileId,
      inject_conversation_id: injectConvId,
      document_mode: injectFileId ? docMode : undefined,
      document_chunk_limit: injectFileId ? chunkLimit : undefined,
    })
    setSending(false)
    setObjective("")
    onClose()
  }

  const selectedFileInfo = files.find(f => f.file_name === selectedFile)
  const convList = conversations || []
  const uploadConvIsNew = uploadConvId === "new" || (uploadConvId && !convList.find(c => c.id === uploadConvId))

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

      {/* Document injection */}
      <div className="mb-2 text-[10px] text-[#555]">
        <div className="flex items-center gap-2 mb-1">
          <span>document:</span>
          <select
            value={selectedFile}
            onChange={e => { setSelectedFile(e.target.value); if (e.target.value) { setUploadedFileName(""); setUploadedConvId(""); setUploadFile(null); setUploadStatus("") } }}
            className="bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none flex-1"
          >
            <option value="">— none —</option>
            {files.map(f => (
              <option key={f.conversation_id + ":" + f.file_name} value={f.file_name}>
                {f.file_name} ({f.file_type}, {f.token_count} tokens)
              </option>
            ))}
          </select>
        </div>

        {selectedFile && !uploadedFileName && (
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

        {selectedFileInfo?.summary && !uploadedFileName && (
          <div className="text-[#444] mt-1 text-[9px] leading-relaxed max-h-14 overflow-y-auto">
            {selectedFileInfo.summary.slice(0, 200)}{(selectedFileInfo.summary.length > 200) ? "…" : ""}
          </div>
        )}

        {/* Upload section */}
        <div className="mt-1.5">
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
                      {c.title || c.id.slice(0, 8)} {c.id === conversationId ? "(current)" : ""}
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
                <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
                  <span className="text-[#5c9e7a] text-[9px]">Ready</span>
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
              {uploadStatus === "error" && (
                <div className="text-semantic-red text-[9px] font-mono">{uploadError || "Upload failed"}</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={!objective.trim() || sending || uploadStatus === "uploading"}
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
