import { useState, useEffect, useMemo, memo } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import rehypeRaw from "rehype-raw"
import {
  listSedimentFiles,
  injectSediment,
  getConversationInjections,
  removeSedimentInjection,
  getFileSummary,
} from "../../../api/client"
import type {
  ConversationFile,
  SedimentFileInfo,
  SedimentInjectionInfo,
  ImageMetadata,
  WebMetadata,
  DocumentMetadata,
} from "../../../api/client"
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
  const [filter, setFilter] = useState<'all' | 'files' | 'research'>('all')
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
    if (type === "research-synthesis" || type === "synthesis-sediment") return "⊙"
    return "📄"
  }

  const filteredFiles = useMemo(() => {
    return files.filter((f) => {
      const isResearch = f.file_type === "research-synthesis" || f.file_type === "synthesis-sediment"
      if (filter === "files" && isResearch) return false
      if (filter === "research" && !isResearch) return false
      return true
    })
  }, [files, filter])

  const researchCount = useMemo(() => {
    return files.filter((f) => f.file_type === "research-synthesis" || f.file_type === "synthesis-sediment").length
  }, [files])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-[480px] max-h-[80vh] bg-[#0c0c0e]/95 border border-[#222]/40 rounded-sm shadow-2xl flex flex-col overflow-hidden backdrop-blur-md"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-[#1a1a1a] select-none shrink-0">
          <span className="text-[9px] font-mono uppercase tracking-widest text-[#6c6c8a]">
            [ Inject Sediment ]
          </span>
          <button
            onClick={onClose}
            className="text-[9px] text-[#555] hover:text-[#888] font-mono cursor-pointer transition-colors"
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
            className="w-full bg-transparent border-b border-[#222]/40 px-1 py-1.5 text-[10px] text-[#ccc] font-mono placeholder-[#444] focus:outline-none focus:border-[#a78bfa]/50 transition-colors"
            autoFocus
          />
        </div>

        {/* Filter bar */}
        <div className="flex gap-x-3 px-4 py-1.5 text-[9px] font-mono shrink-0 select-none border-b border-[#1a1a1a]">
          <button
            onClick={() => setFilter('all')}
            className={`cursor-pointer transition-colors ${filter === 'all' ? 'text-[#a78bfa]' : 'text-[#555] hover:text-[#888]'}`}
          >
            all
          </button>
          <span className="text-[#333]">•</span>
          <button
            onClick={() => setFilter('files')}
            className={`cursor-pointer transition-colors ${filter === 'files' ? 'text-[#a78bfa]' : 'text-[#555] hover:text-[#888]'}`}
          >
            files
          </button>
          <span className="text-[#333]">•</span>
          <button
            onClick={() => setFilter('research')}
            className={`cursor-pointer transition-colors ${filter === 'research' ? 'text-[#a78bfa]' : 'text-[#555] hover:text-[#888]'}`}
          >
            research ({researchCount})
          </button>
        </div>

        {/* File list */}
        <div className="flex-1 overflow-y-auto px-2 py-2 min-h-0">
          {loading ? (
            <div className="text-[9px] text-[#555] font-mono animate-pulse text-center py-8">
              [ scanning sediment layers... ]
            </div>
          ) : filteredFiles.length === 0 ? (
            <div className="text-[9px] text-[#444] font-mono text-center py-8 italic">
              {search ? "[ no matching files found ]" : "[ no files available for injection ]"}
            </div>
          ) : (
            <div className="space-y-0.5">
              {filteredFiles.map((f) => {
                const key = `${f.conversation_id}:${f.file_name}`
                const isSelected = selected.has(key)
                return (
                  <div
                    key={key}
                    onClick={() => toggleFile(key)}
                    className={`flex items-start gap-2.5 px-3 py-2 cursor-pointer transition-all duration-150 border-l-2 ${isSelected
                        ? "border-[#a78bfa] bg-[#1a1a2e]/50"
                        : "border-transparent hover:bg-[#111]"
                      }`}
                  >
                    <div className={`w-3 h-3 mt-0.5 border flex items-center justify-center shrink-0 transition-colors ${isSelected
                        ? "border-[#a78bfa] bg-[#a78bfa]/20"
                        : "border-[#333] bg-transparent"
                      }`}>
                      {isSelected && <span className="text-[8px] text-[#a78bfa] leading-none">✓</span>}
                    </div>

                    <div className="flex-1 min-w-0 font-mono">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm leading-none">{fileIcon(f.file_type)}</span>
                        <span className="text-[10px] text-[#ccc] truncate" title={f.display_name || f.file_name}>
                          {f.display_name || f.file_name}
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
        <div className="flex items-center justify-between px-4 py-2.5 border-t border-[#1a1a1a] bg-[#0c0c0e]/95 shrink-0">
          <span className="text-[8px] text-[#555] font-mono">
            {selected.size} file{selected.size !== 1 ? "s" : ""} selected
          </span>
          <button
            onClick={handleInject}
            disabled={selected.size === 0 || injecting}
            className={`text-[9px] font-mono px-3 py-1 transition-all duration-200 ${selected.size === 0 || injecting
                ? "text-[#444] cursor-not-allowed"
                : "text-[#a78bfa] hover:text-[#c0b0ff] cursor-pointer"
              }`}
          >
            {injecting ? "[injecting...]" : `[inject ${selected.size > 0 ? `(${selected.size})` : ""}]`}
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
}: SedimentSectionProps) {
  const [showInjectModal, setShowInjectModal] = useState(false)
  const [injections, setInjections] = useState<SedimentInjectionInfo[]>([])

  // File summary expansion — owned by SedimentSection itself
  const [expandedFile, setExpandedFile] = useState<string | null>(null)
  const [loadedSummaries, setLoadedSummaries] = useState<Record<string, {
    summary: string | null
    summary_model: string | null
    image_metadata?: ImageMetadata | null
    web_metadata?: WebMetadata | null
    document_metadata?: DocumentMetadata | null
  }>>({})
  const [loadingSummary, setLoadingSummary] = useState<string | null>(null)

  const handleToggleSummary = async (fileName: string) => {
    if (expandedFile === fileName) {
      setExpandedFile(null)
      return
    }
    setExpandedFile(fileName)
    if (!loadedSummaries[fileName] && conversationId) {
      setLoadingSummary(fileName)
      try {
        const res = await getFileSummary(conversationId, fileName)
        setLoadedSummaries((prev) => ({
          ...prev,
          [fileName]: {
            summary: res.summary,
            summary_model: res.summary_model,
            image_metadata: res.image_metadata,
            web_metadata: res.web_metadata,
            document_metadata: res.document_metadata,
          },
        }))
      } catch (err) {
        console.error("Failed to load file summary:", err)
      } finally {
        setLoadingSummary(null)
      }
    }
  }

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
    if (type === "research-synthesis" || type === "synthesis-sediment") return "⊙"
    return "📄"
  }

  const extractTaskIdFromFileName = (fileName: string) => {
    const match = fileName.match(/research-synthesis-([a-f0-9-]+)\.md/i)
    return match ? match[1] : ""
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
            className="text-[9px] font-mono text-[#666] hover:text-[#a78bfa] cursor-pointer select-none transition-colors"
          >
            [+ inject]
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
                  <span className={`text-[10px] font-mono truncate block ${
                    inj.file_type === "research-synthesis" || inj.file_type === "synthesis-sediment"
                      ? "text-[#a78bfa] font-medium"
                      : "text-[#aaa]"
                  }`}>
                    {inj.file_type === "research-synthesis" || inj.file_type === "synthesis-sediment"
                      ? `synthesis: ${inj.source_file_name.replace("research-synthesis-", "").replace(".md", "")}`
                      : inj.source_file_name}
                  </span>
                  <span className="text-[7px] text-[#555] font-mono truncate block">
                    from "{inj.source_conversation_title || "untitled"}"
                  </span>
                </div>

                <span className="text-[8px] text-[#666] font-mono shrink-0">
                  {inj.token_count >= 1000 ? `${(inj.token_count / 1000).toFixed(1)}k` : inj.token_count} tok
                </span>

                {(!inj.status || inj.status === "ready") ? (
                  <button
                    onClick={() => handleToggleSummary(inj.source_file_name)}
                    className="text-[8px] text-[#4ade80] hover:underline"
                  >
                    {expandedFile === inj.source_file_name ? "hide" : "sum"}
                  </button>
                ) : (
                  <span className={`text-[8px] px-1 border rounded animate-pulse font-mono ${
                    inj.status === "uploading"
                      ? "text-[#eab308] border-[#eab308]/30"
                      : inj.status === "error"
                      ? "text-[#ef4444] border-[#ef4444]/30 animate-none"
                      : "text-[#3b82f6] border-[#3b82f6]/30"
                  }`}>
                    {inj.status === "uploading" ? "uploading" : inj.status === "error" ? "error" : "indexing"}
                  </span>
                )}

                <button
                  onClick={() => handleRemoveInjection(inj.id)}
                  className="text-[9px] text-[#555] hover:text-[#ef4444] px-0.5 font-mono opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Remove injection"
                >
                  ×
                </button>
              </div>

              {expandedFile === inj.source_file_name && (
                <div className="mt-1 ml-4 border-l border-[#2a2a2a] pl-2">
                  {renderSummaryContent(inj.source_file_name)}
                  {(inj.file_type === "research-synthesis" || inj.file_type === "synthesis-sediment") && (
                    <div className="mt-2 pt-1.5 border-t border-[#1a1a1a] flex justify-end">
                      <a
                        href={`/research?id=${extractTaskIdFromFileName(inj.source_file_name)}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[9px] text-[#a78bfa] hover:text-[#c084fc] font-mono flex items-center gap-1 transition-colors"
                      >
                        <span>View Full Synthesis ↗</span>
                      </a>
                    </div>
                  )}
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
                <span className={`text-[10px] truncate flex-1 font-mono ${
                  f.file_type === "research-synthesis" || f.file_type === "synthesis-sediment"
                    ? "text-[#a78bfa] font-medium"
                    : "text-[#aaa]"
                }`}>
                  {f.file_type === "research-synthesis" || f.file_type === "synthesis-sediment"
                    ? `synthesis: ${f.file_name.replace("research-synthesis-", "").replace(".md", "")}`
                    : f.file_name}
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
                    onClick={() => handleToggleSummary(f.file_name)}
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
                <div className="mt-1 ml-4 border-l border-[#2a2a2a] pl-2">
                  {renderSummaryContent(f.file_name)}
                  {(f.file_type === "research-synthesis" || f.file_type === "synthesis-sediment") && (
                    <div className="mt-2 pt-1.5 border-t border-[#1a1a1a] flex justify-end">
                      <a
                        href={`/research?id=${extractTaskIdFromFileName(f.file_name)}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[9px] text-[#a78bfa] hover:text-[#c084fc] font-mono flex items-center gap-1 transition-colors"
                      >
                        <span>View Full Synthesis ↗</span>
                      </a>
                    </div>
                  )}
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
