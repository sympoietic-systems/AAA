import { memo } from "react"
import type { StepPreview } from "../../../../../api/research"

interface DocPreviewItem {
  file_id: string
  mode: string
  chunk_limit?: number | null
  doc_summary?: string
  doc_chunks?: Array<{ content: string; sim: number }>
}

export const DocumentDigestionPreview = memo(function DocumentDigestionPreview({ preview }: { preview: StepPreview }) {
  const docs: DocPreviewItem[] = (preview.documents as DocPreviewItem[]) || []

  if (docs.length > 0) {
    return (
      <div className="space-y-4 font-mono">
        <div className="text-semantic-purple text-[9px] uppercase font-mono">
          digesting {docs.length} document(s)
        </div>
        {docs.map((doc, idx) => (
          <div key={doc.file_id || idx} className="p-2 border border-ui-border rounded bg-ui-bg-alt/50 space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-semantic-purple text-[8px] font-mono">▪ file</span>
              <span className="text-ui-secondary text-[9px] font-bold truncate">{doc.file_id}</span>
              <span className="text-ui-dim text-[8px]">({doc.mode})</span>
            </div>

            {doc.doc_summary && (
              <div>
                <div className="text-ui-dim text-[8px] uppercase">summary</div>
                <div className="text-ui-secondary text-[8px] pl-2 border-l border-ui-border leading-relaxed max-h-24 overflow-y-auto">
                  {doc.doc_summary}
                </div>
              </div>
            )}

            {doc.doc_chunks && doc.doc_chunks.length > 0 && (
              <div>
                <div className="text-ui-dim text-[8px] uppercase">chunks ({doc.doc_chunks.length})</div>
                <div className="space-y-1 max-h-36 overflow-y-auto">
                  {doc.doc_chunks.slice(0, 3).map((chunk, i) => (
                    <div key={i} className="text-ui-secondary text-[8px] pl-1.5 border-l border-ui-border/50">
                      {chunk.content.slice(0, 200)}{chunk.content.length > 200 ? "…" : ""}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    )
  }

  // Legacy single document view fallback
  return (
    <div className="space-y-3 font-mono">
      {preview.file_id && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-semantic-purple text-[8px] font-mono">▪ file</span>
          <span className="text-ui-secondary text-[9px] truncate">{preview.file_id}</span>
        </div>
      )}
      {preview.mode && (
        <div className="flex items-center gap-2 text-ui-dim text-[9px]">
          <span>mode:</span>
          <span className="text-ui-secondary">{preview.mode}</span>
        </div>
      )}
      {preview.doc_summary && (
        <div>
          <div className="text-ui-dim text-[9px] mb-0.5 uppercase font-mono">document summary</div>
          <div className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed max-h-32 overflow-y-auto">
            {preview.doc_summary}
          </div>
        </div>
      )}
    </div>
  )
})
