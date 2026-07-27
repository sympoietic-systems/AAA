// NewResearchForm — create and dispatch a research task with multi-document support.
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

interface SelectedDocItem {
  id: string
  file_name: string
  conversation_id?: string
  document_mode: "full" | "chunks"
  document_chunk_limit: number
  is_uploading?: boolean
  upload_status?: string
  upload_error?: string
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
  const [injectedDocs, setInjectedDocs] = useState<SelectedDocItem[]>([])

  const [conversations, setConversations] = useState<ConversationInfo[]>([])
  const [uploadConvId, setUploadConvId] = useState(conversationId || "")
  const [showUpload, setShowUpload] = useState(false)
  const [selectedFileToAdd, setSelectedFileToAdd] = useState("")

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

  const addExistingDoc = useCallback((fileName: string) => {
    if (!fileName) return
    const found = files.find(f => f.file_name === fileName)
    setInjectedDocs(prev => [
      ...prev,
      {
        id: Math.random().toString(36).substring(2, 9),
        file_name: fileName,
        conversation_id: found?.conversation_id,
        document_mode: "chunks",
        document_chunk_limit: 5,
      },
    ])
    setSelectedFileToAdd("")
  }, [files])

  const removeDoc = useCallback((id: string) => {
    setInjectedDocs(prev => prev.filter(d => d.id !== id))
  }, [])

  const updateDocConfig = useCallback((id: string, mode: "full" | "chunks", limit: number) => {
    setInjectedDocs(prev =>
      prev.map(d => (d.id === id ? { ...d, document_mode: mode, document_chunk_limit: limit } : d))
    )
  }, [])

  const handleFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const tempId = Math.random().toString(36).substring(2, 9)
    const newDocItem: SelectedDocItem = {
      id: tempId,
      file_name: file.name,
      document_mode: "chunks",
      document_chunk_limit: 5,
      is_uploading: true,
      upload_status: "uploading",
    }
    setInjectedDocs(prev => [...prev, newDocItem])

    let targetConvId = uploadConvId || "new"

    try {
      const res = await uploadFiles(targetConvId, [file])
      const returnedConvId = res.conversation_id
      setInjectedDocs(prev =>
        prev.map(d => (d.id === tempId ? { ...d, conversation_id: returnedConvId, upload_status: "indexing" } : d))
      )

      const interval = setInterval(async () => {
        try {
          const filesRes = await getConversationFiles(returnedConvId)
          const target = filesRes.files.find(f => f.file_name === file.name)
          if (target?.status === "ready") {
            setInjectedDocs(prev =>
              prev.map(d => (d.id === tempId ? { ...d, is_uploading: false, upload_status: "ready" } : d))
            )
            clearInterval(interval)
          } else if (target?.status === "error") {
            setInjectedDocs(prev =>
              prev.map(d =>
                d.id === tempId ? { ...d, is_uploading: false, upload_status: "error", upload_error: "Indexing failed" } : d
              )
            )
            clearInterval(interval)
          }
        } catch {
          // keep polling
        }
      }, POLL_INTERVAL)
    } catch (err: any) {
      setInjectedDocs(prev =>
        prev.map(d =>
          d.id === tempId
            ? { ...d, is_uploading: false, upload_status: "error", upload_error: err.message || "Upload failed" }
            : d
        )
      )
    }
  }, [uploadConvId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!objective.trim() || sending) return
    setSending(true)

    const formattedDocs = injectedDocs.map(d => ({
      file_id: d.file_name,
      conversation_id: d.conversation_id,
      document_mode: d.document_mode,
      document_chunk_limit: d.document_chunk_limit,
    }))

    const firstDoc = formattedDocs[0]

    try {
      await onDispatch({
        objective: objective.trim(),
        conversation_id: conversationId,
        max_depth: depth,
        max_breadth: breadth,
        is_agonistic: agonistic,
        budget_limit_usd: budget,
        inject_file_id: firstDoc?.file_id,
        inject_conversation_id: firstDoc?.conversation_id,
        document_mode: firstDoc?.document_mode,
        document_chunk_limit: firstDoc?.document_chunk_limit,
        injected_documents: formattedDocs.length > 0 ? formattedDocs : undefined,
      })
      setObjective("")
      onClose()
    } catch (err: any) {
      console.error("Dispatch failed:", err)
      alert(`Dispatch failed: ${err?.message || err || "Unknown error"}`)
    } finally {
      setSending(false)
    }
  }

  const convList = conversations || []
  const hasUploading = injectedDocs.some(d => d.is_uploading)

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

      {/* Multi-Document Injection Section */}
      <div className="mb-3 text-[10px] text-[#777] font-mono">
        <div className="text-[#555] mb-1">documents ({injectedDocs.length}):</div>

        {/* List of selected documents */}
        {injectedDocs.map((doc) => (
          <div key={doc.id} className="p-1.5 mb-1.5 border border-[#222]/40 rounded bg-[#111]/30 flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span className="text-[#94a3b8] font-bold truncate max-w-[200px]" title={doc.file_name}>
                {doc.file_name}
              </span>
              <button
                type="button"
                onClick={() => removeDoc(doc.id)}
                className="text-semantic-red hover:text-red-400 text-[9px] cursor-pointer"
              >
                [✕ remove]
              </button>
            </div>

            {doc.is_uploading ? (
              <div className="text-[#b89553] text-[9px] animate-pulse">
                {doc.upload_status === "uploading" ? "Uploading..." : "Indexing document..."}
              </div>
            ) : doc.upload_status === "error" ? (
              <div className="text-semantic-red text-[9px]">{doc.upload_error || "Failed to process"}</div>
            ) : (
              <div className="flex items-center gap-3 text-[9px] text-[#666]">
                <label className="flex items-center gap-1">
                  mode:
                  <select
                    value={doc.document_mode}
                    onChange={e => updateDocConfig(doc.id, e.target.value as "full" | "chunks", doc.document_chunk_limit)}
                    className="bg-transparent border-b border-[#222]/40 text-[#777] outline-none"
                  >
                    <option value="chunks">top chunks</option>
                    <option value="full">full analysis</option>
                  </select>
                </label>
                {doc.document_mode === "chunks" && (
                  <label className="flex items-center gap-1">
                    chunks:
                    <select
                      value={doc.document_chunk_limit}
                      onChange={e => updateDocConfig(doc.id, doc.document_mode, Number(e.target.value))}
                      className="bg-transparent border-b border-[#222]/40 text-[#777] outline-none w-10"
                    >
                      {[3,5,8,10,15].map(n => <option key={n} value={n}>{n}</option>)}
                    </select>
                  </label>
                )}
              </div>
            )}
          </div>
        ))}

        {/* Add Document Controls */}
        <div className="flex flex-wrap items-center gap-2 mt-2">
          {/* Select existing */}
          <select
            value={selectedFileToAdd}
            onChange={e => {
              addExistingDoc(e.target.value)
            }}
            className="bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none text-[9px] flex-1 max-w-[200px]"
          >
            <option value="">+ add existing document</option>
            {files.map(f => (
              <option key={f.conversation_id + ":" + f.file_name} value={f.file_name}>
                {f.file_name} ({f.token_count} tokens)
              </option>
            ))}
          </select>

          {/* Toggle upload */}
          <button
            type="button"
            onClick={() => setShowUpload(!showUpload)}
            className="text-[#b37e5d] hover:text-[#ff6b00] text-[9px] cursor-pointer"
          >
            [{showUpload ? "▼ upload new" : "+ upload new"}]
          </button>
        </div>

        {/* Upload Drawer */}
        {showUpload && (
          <div className="mt-2 p-2 border border-[#222]/40 rounded bg-[#0a0a0a] space-y-1.5">
            <div className="flex items-center gap-2 text-[9px]">
              <span>target conversation:</span>
              <select
                value={uploadConvId}
                onChange={e => setUploadConvId(e.target.value)}
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
                className="text-[#4ade80] hover:text-[#6ee7b0] text-[9px] cursor-pointer"
              >
                [choose file & upload]
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={!objective.trim() || sending || hasUploading}
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
