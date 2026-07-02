import { memo } from "react"
import type { StepPreview } from "../../../../../api/research"

export const DocumentDigestionPreview = memo(function DocumentDigestionPreview({ preview }: { preview: StepPreview }) {
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
          {preview.mode === "chunks" && preview.chunk_limit != null && (
            <span className="text-ui-dim">(top {preview.chunk_limit} chunks)</span>
          )}
          {preview.mode === "full" && (
            <span className="text-ui-dim">(entire document)</span>
          )}
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
      {preview.mode === "chunks" && preview.doc_chunks && preview.doc_chunks.length > 0 && (
        <div>
          <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">
            top chunks ({preview.doc_chunks.length})
          </div>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {preview.doc_chunks.map((chunk, i) => {
              const simDisplay = chunk.sim > 0 ? ` (sim=${chunk.sim.toFixed(2)})` : ""
              return (
                <div key={i} className="text-ui-secondary text-[9px] pl-2 border-l border-ui-border leading-relaxed">
                  <div className="text-ui-dim text-[8px] mb-0.5">chunk {i + 1}{simDisplay}</div>
                  <div className="whitespace-pre-wrap break-all text-[8px]">{chunk.content.slice(0, 500)}{chunk.content.length > 500 ? "…" : ""}</div>
                </div>
              )
            })}
          </div>
        </div>
      )}
      {preview.mode === "full" && preview.doc_chunks && preview.doc_chunks.length > 0 && (
        <div>
          <div className="text-ui-dim text-[9px] mb-1 uppercase font-mono">
            document text ({preview.doc_chunks.length} chunks)
          </div>
          <div className="max-h-64 overflow-y-auto pl-2 border-l border-ui-border">
            <div className="text-ui-secondary text-[8px] whitespace-pre-wrap break-all leading-relaxed">
              {preview.doc_chunks.map(c => c.content).join("\n\n").slice(0, 1500)}
              {preview.doc_chunks.reduce((acc, c) => acc + c.content.length, 0) > 1500 ? "…" : ""}
            </div>
          </div>
        </div>
      )}
      {(!preview.doc_chunks || preview.doc_chunks.length === 0) && (
        <div className="text-ui-dim italic text-[9px]">
          {preview.document_digested ? "document already digested" : "no document chunks available"}
        </div>
      )}
    </div>
  )
})
