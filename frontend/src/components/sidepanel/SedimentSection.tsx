import { useState, useEffect, memo } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import rehypeRaw from "rehype-raw"
import {
  listSedimentFiles,
  injectSediment,
  getConversationInjections,
  removeSedimentInjection,
} from "../../api/client"
import type {
  ConversationFile,
  SedimentFileInfo,
  SedimentInjectionInfo,
  ImageMetadata,
  WebMetadata,
  DocumentMetadata,
} from "../../api/client"
import {
  ImageMetadataCard,
  WebMetadataCard,
  DocumentMetadataCard,
} from "./MetadataCards"

interface SedimentSectionProps {
  conversationId?: string
  uploadedFiles: ConversationFile[]
  onDeleteFile?: (fileName: string) => void
  onReprocessFile?: (fileName: string) => void
  expandedFile: string | null
  loadingSummary: string | null
  loadedSummaries: Record<string, {
    summary: string | null
    summary_model: string | null
    image_metadata?: ImageMetadata | null
    web_metadata?: WebMetadata | null
    document_metadata?: DocumentMetadata | null
  }>
  onToggleSummary: (fileName: string) => void
}

function SedimentInjectionModal({
  conversationId,
  onClose,
  onInjected,
}: {
  conversationId: string
  onClose: () => void
  onInjected: () => void
}) {
  const [files, setFiles] = useState<SedimentFileInfo[]>([])
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [injecting, setInjecting] = useState(false)

  useEffect(() => {
    setLoading(true)
    listSedimentFiles(conversationId, search || undefined)
      .then((res) => setFiles(res.files))
      .catch(() => setFiles([]))
      .finally(() => setLoading(false))
  }, [conversationId, search])

  const toggleFile = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const handleInject = async () => {
    if (selected.size === 0) return
    setInjecting(true)
    try {
      const filesToInject = Array.from(selected).map((key) => {
        const [convId, ...rest] = key.split(":")
        return { source_conversation_id: convId, source_file_name: rest.join(":") }
      })
      await injectSediment(conversationId, filesToInject)
      onInjected()
      onClose()
    } catch (e) {
      console.error("Injection failed:", e)
    } finally {
      setInjecting(false)
    }
  }

  const fileIcon = (type: string) => {
    if (type === "image") return "🖼"
    if (type === "pdf") return "📄"
    if (type === "md") return "📝"
    if (type === "epub" || type === "mobi") return "📖"
    if (type === "web_probe") return "🌐"
    return "📄"
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-[480px] max-h-[80vh] bg-[#0c0c0c] border border-[#2a2a2a] rounded-lg shadow-2xl flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a1a] shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-[#a78bfa]">◈</span>
            <span className="text-[11px] text-[#ccc] font-mono tracking-wide">Inject Sediment</span>
          </div>
          <button
            onClick={onClose}
            className="text-[10px] text-[#555] hover:text-[#aaa] font-mono transition-colors"
          >
            [close]
          </button>
        </div>

        {/* Search */}
        <div className="px-4 py-2 border-b border-[#1a1a1a] shrink-0">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search files across all conversations..."
            className="w-full bg-[#111] border border-[#222] rounded px-3 py-1.5 text-[10px] text-[#ccc] font-mono placeholder-[#444] focus:outline-none focus:border-[#a78bfa]/50 transition-colors"
            autoFocus
          />
        </div>

        {/* File list */}
        <div className="flex-1 overflow-y-auto px-2 py-2 min-h-0">
          {loading ? (
            <div className="text-[9px] text-[#555] font-mono animate-pulse text-center py-8">
              scanning sediment layers...
            </div>
          ) : files.length === 0 ? (
            <div className="text-[9px] text-[#444] font-mono text-center py-8 italic">
              {search ? "No files match your search." : "No files available for injection."}
            </div>
          ) : (
            <div className="space-y-0.5">
              {files.map((f) => {
                const key = `${f.conversation_id}:${f.file_name}`
                const isSelected = selected.has(key)
                return (
                  <div
                    key={key}
                    onClick={() => toggleFile(key)}
                    className={`flex items-start gap-2 px-2.5 py-2 rounded cursor-pointer transition-all duration-150 ${isSelected
                        ? "bg-[#a78bfa]/10 border border-[#a78bfa]/30"
                        : "hover:bg-[#151515] border border-transparent"
                      }`}
                  >
                    <div className={`w-3.5 h-3.5 mt-0.5 rounded-sm border flex items-center justify-center shrink-0 transition-colors ${isSelected
                        ? "border-[#a78bfa] bg-[#a78bfa]/20"
                        : "border-[#333] bg-[#0a0a0a]"
                      }`}>
                      {isSelected && <span className="text-[8px] text-[#a78bfa] leading-none">✓</span>}
                    </div>

                    <div className="flex-1 min-w-0 font-mono">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm">{fileIcon(f.file_type)}</span>
                        <span className="text-[10px] text-[#ccc] truncate">
                          {f.file_name}
                        </span>
                        <span className="text-[8px] text-[#555] shrink-0">
                          {f.token_count >= 1000 ? `${(f.token_count / 1000).toFixed(1)}k` : f.token_count}tok
                        </span>
                      </div>
                      <div className="text-[8px] text-[#555] truncate mt-0.5">
                        from "{f.conversation_title || "untitled"}"
                      </div>
                      {f.summary && (
                        <div className="text-[8px] text-[#666] mt-0.5 line-clamp-2 leading-relaxed">
                          {f.summary.slice(0, 120)}{f.summary.length > 120 ? "..." : ""}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-2.5 border-t border-[#1a1a1a] bg-[#080808] shrink-0">
          <span className="text-[8px] text-[#555] font-mono">
            {selected.size} file{selected.size !== 1 ? "s" : ""} selected
          </span>
          <button
            onClick={handleInject}
            disabled={selected.size === 0 || injecting}
            className={`text-[9px] font-mono px-3 py-1 rounded transition-all duration-200 ${selected.size === 0 || injecting
                ? "text-[#444] bg-[#111] border border-[#222] cursor-not-allowed"
                : "text-[#a78bfa] bg-[#a78bfa]/10 border border-[#a78bfa]/30 hover:bg-[#a78bfa]/20 hover:border-[#a78bfa]/50"
              }`}
          >
            {injecting ? "injecting..." : `inject ${selected.size > 0 ? `(${selected.size})` : ""}`}
          </button>
        </div>
      </div>
    </div>
  )
}

function SedimentSectionComponent({
  conversationId,
  uploadedFiles,
  onDeleteFile,
  onReprocessFile,
  expandedFile,
  loadingSummary,
  loadedSummaries,
  onToggleSummary,
}: SedimentSectionProps) {
  const [showInjectModal, setShowInjectModal] = useState(false)
  const [injections, setInjections] = useState<SedimentInjectionInfo[]>([])

  // Fetch + poll injections
  useEffect(() => {
    if (!conversationId) {
      setInjections([])
      return
    }

    let active = true
    let timeoutId: ReturnType<typeof setTimeout>

    const fetchInjections = async () => {
      if (!active) return
      try {
        const res = await getConversationInjections(conversationId)
        if (active) setInjections(res.injections)
      } catch {
        if (active) setInjections([])
      }

      if (active) {
        const delay = 60000 + (Math.random() - 0.5) * 5000 // 60s ± 2.5s
        timeoutId = setTimeout(fetchInjections, delay)
      }
    }

    fetchInjections()

    return () => {
      active = false
      clearTimeout(timeoutId)
    }
  }, [conversationId])

  const handleRemoveInjection = async (injectionId: string) => {
    try {
      await removeSedimentInjection(injectionId)
      setInjections((prev) => prev.filter((i) => i.id !== injectionId))
    } catch (e) {
      console.error("Failed to remove injection:", e)
    }
  }

  const fileIcon = (type: string) => {
    if (type === "image") return "🖼"
    if (type === "pdf") return "📄"
    if (type === "md") return "📝"
    if (type === "epub" || type === "mobi") return "📖"
    if (type === "web_probe") return "🌐"
    return "📄"
  }

  const renderSummaryContent = (fileName: string) => {
    if (loadingSummary === fileName) {
      return <div className="p-2 text-[9px] text-[#888] font-mono animate-pulse">Loading summary...</div>
    }

    const data = loadedSummaries[fileName]
    if (!data) {
      return <div className="p-2 text-[9px] text-[#888] font-mono">No summary available.</div>
    }

    if (data.image_metadata) {
      return <ImageMetadataCard metadata={data.image_metadata} />
    }
    if (data.web_metadata) {
      return <WebMetadataCard metadata={data.web_metadata} summary={data.summary} />
    }
    if (data.document_metadata) {
      return <DocumentMetadataCard metadata={data.document_metadata} summary={data.summary} />
    }
    return (
      <div className="p-2 text-[9px] text-[#888] font-mono leading-relaxed markdown-body">
        {data.summary ? (
          <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>
            {data.summary}
          </ReactMarkdown>
        ) : (
          "No summary available."
        )}
      </div>
    )
  }

  return (
    <div className="pl-3">
      {/* Inject button */}
      {conversationId && (
        <div className="mt-2 mb-1 flex items-center gap-2">
          <button
            onClick={() => setShowInjectModal(true)}
            className="text-[8px] font-mono text-[#a78bfa] border border-[#a78bfa]/30 bg-[#a78bfa]/5 hover:bg-[#a78bfa]/15 hover:border-[#a78bfa]/50 px-2 py-0.5 rounded transition-all duration-200"
          >
            ◈ inject
          </button>
          {injections.length > 0 && (
            <span className="text-[7px] text-[#666] font-mono">
              {injections.length} linked
            </span>
          )}
        </div>
      )}

      {/* Injected files */}
      {injections.length > 0 && (
        <div className="border-t border-[#1a1a1a] pt-1.5 mb-1.5">
          <div className="text-[7px] text-[#6c6c8a] font-mono uppercase tracking-wider mb-1">
            [ Injected Sediment ]
          </div>
          {injections.map((inj) => (
            <div key={inj.id} className="py-1.5 border-b border-[#1a1a1a] last:border-b-0">
              <div className="flex items-center gap-1.5 group">
                <span className="text-sm">{fileIcon(inj.file_type)}</span>
                <div className="flex-1 min-w-0">
                  <span className="text-[10px] text-[#aaa] font-mono truncate block">
                    {inj.source_file_name}
                  </span>
                  <span className="text-[7px] text-[#555] font-mono truncate block">
                    from "{inj.source_conversation_title || "untitled"}"
                  </span>
                </div>

                <span className="text-[8px] text-[#666] font-mono shrink-0">
                  {inj.token_count >= 1000 ? `${(inj.token_count / 1000).toFixed(1)}k` : inj.token_count} tok
                </span>

                <button
                  onClick={() => onToggleSummary(inj.source_file_name)}
                  className="text-[8px] text-[#4ade80] hover:underline"
                >
                  {expandedFile === inj.source_file_name ? "hide" : "sum"}
                </button>

                <button
                  onClick={() => handleRemoveInjection(inj.id)}
                  className="text-[9px] text-[#555] hover:text-[#ef4444] px-0.5 font-mono opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Remove injection"
                >
                  ×
                </button>
              </div>

              {expandedFile === inj.source_file_name && (
                <div className="mt-1 ml-4 bg-[#141414] border border-[#222] rounded overflow-hidden">
                  {renderSummaryContent(inj.source_file_name)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Native files */}
      {uploadedFiles.length > 0 && (
        <div className="border-t border-[#1a1a1a] pt-2">
          {uploadedFiles.map((f) => (
            <div key={f.file_name} className="py-1.5 border-b border-[#1a1a1a] last:border-b-0">
              <div className="flex items-center gap-1.5">
                <span className="text-sm">
                  {fileIcon(f.file_type)}
                </span>
                <span className="text-[10px] text-[#aaa] truncate flex-1 font-mono">
                  {f.file_name}
                </span>

                {f.status === "uploading" && (
                  <span className="text-[8px] text-[#eab308] animate-pulse px-1 border border-[#eab308]/30 rounded">
                    uploading
                  </span>
                )}
                {f.status === "processing" && (
                  <span className="text-[8px] text-[#3b82f6] animate-pulse px-1 border border-[#3b82f6]/30 rounded">
                    indexing
                  </span>
                )}
                {f.status === "error" && (
                  <div className="flex items-center gap-1.5 font-mono">
                    <span className="text-[8px] text-[#ef4444] px-1 border border-[#ef4444]/30 rounded" title={f.summary || "Unknown error"}>
                      error
                    </span>
                    {onReprocessFile && (
                      <button
                        onClick={() => onReprocessFile(f.file_name)}
                        className="text-[8px] text-[#60a5fa] hover:text-[#93c5fd] hover:underline"
                        title="Retry indexing/summarization"
                      >
                        retry
                      </button>
                    )}
                  </div>
                )}

                {f.token_count > 0 && f.status === "ready" && (
                  <span className="text-[8px] text-[#666] font-mono">
                    {f.token_count >= 1000 ? `${(f.token_count / 1000).toFixed(1)}k` : f.token_count} tok
                  </span>
                )}

                {f.status === "ready" && (
                  <button
                    onClick={() => onToggleSummary(f.file_name)}
                    className="text-[8px] text-[#4ade80] hover:underline"
                  >
                    {expandedFile === f.file_name ? "hide" : "sum"}
                  </button>
                )}

                {onDeleteFile && (
                  <button
                    onClick={() => onDeleteFile(f.file_name)}
                    className="text-[9px] text-[#555] hover:text-[#ef4444] px-1 font-mono"
                    title="Delete file trace"
                  >
                    ×
                  </button>
                )}
              </div>

              {expandedFile === f.file_name && (
                <div className="mt-1 ml-4 bg-[#141414] border border-[#222] rounded overflow-hidden">
                  {renderSummaryContent(f.file_name)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {uploadedFiles.length === 0 && injections.length === 0 && (
        <div className="text-[9px] text-[#444] font-mono italic py-2 mt-1">
          No files or injections in this conversation.
        </div>
      )}

      {/* Injection Modal */}
      {showInjectModal && conversationId && (
        <SedimentInjectionModal
          conversationId={conversationId}
          onClose={() => setShowInjectModal(false)}
          onInjected={() => {
            // Refetch after injection
            getConversationInjections(conversationId)
              .then((res) => setInjections(res.injections))
              .catch(() => setInjections([]))
          }}
        />
      )}
    </div>
  )
}

export const SedimentSection = memo(SedimentSectionComponent)
