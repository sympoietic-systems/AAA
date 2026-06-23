import { memo } from "react"
import { confirmResonanceLink, deleteResonanceLink } from "../../../api/client"
import type { SimNode, SimLink } from "./ConnectionCloudSimulation"

interface OverlaysProps {
  contextMenu: { x: number; y: number; node: SimNode } | null
  handleDeleteNode: () => void
  hoveredNode: SimNode | null
  dimensions: { width: number; height: number }
  zoom: number
  pan: { x: number; y: number }
  committingNode: SimNode | null
  setCommittingNode: React.Dispatch<React.SetStateAction<SimNode | null>>
  commitContent: string
  setCommitContent: React.Dispatch<React.SetStateAction<string>>
  handleCommitSubmit: () => void
  isCommitLoading: boolean
  selectedLink: SimLink | null
  selectedLinkPos: { x: number; y: number } | null
  setSelectedLink: React.Dispatch<React.SetStateAction<SimLink | null>>
  setSelectedLinkPos: React.Dispatch<React.SetStateAction<{ x: number; y: number } | null>>
  conversationId: string
  refreshTree: () => void
  handleZoomIn: (e: React.MouseEvent) => void
  handleZoomOut: (e: React.MouseEvent) => void
  handleResetZoom: (e: React.MouseEvent) => void
}

export const ConnectionCloudOverlays = memo(function ConnectionCloudOverlays({
  contextMenu, handleDeleteNode,
  hoveredNode, dimensions, zoom, pan,
  committingNode, setCommittingNode, commitContent, setCommitContent, handleCommitSubmit, isCommitLoading,
  selectedLink, selectedLinkPos, setSelectedLink, setSelectedLinkPos,
  conversationId, refreshTree,
  handleZoomIn, handleZoomOut, handleResetZoom,
}: OverlaysProps) {
  return (
    <>
      {/* Right-click context menu — terminal style */}
      {contextMenu && (
        <div
          className="absolute z-20 bg-[#0d0d12]/95 py-1 px-0"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={handleDeleteNode}
            className="text-left px-3 py-1 text-[10px] font-mono text-[#ef4444] hover:text-[#f87171] transition-colors cursor-pointer select-none"
          >
            [delete node]
          </button>
        </div>
      )}

      {/* Zoom Controls — terminal style */}
      <div className="absolute bottom-3 right-3 flex flex-col gap-1 z-10 select-none">
        <button onClick={handleZoomIn} className="font-mono text-xs text-[#666] hover:text-action-hover cursor-pointer transition-colors"
          title="Zoom In">[ + ]</button>
        <button onClick={handleZoomOut} className="font-mono text-xs text-[#666] hover:text-action-hover cursor-pointer transition-colors"
          title="Zoom Out">[ − ]</button>
        <button onClick={handleResetZoom} className="font-mono text-[9px] text-[#666] hover:text-action-hover cursor-pointer transition-colors"
          title="Reset View">[ ⟲ ]</button>
      </div>

      {/* Hover Tooltip — minimal */}
      {hoveredNode && (
        <div
          className="absolute z-10 px-2 py-1.5 bg-[#0d0d12]/95 text-[10px] font-mono max-w-[200px] pointer-events-none select-none"
          style={{
            left: `${Math.min(dimensions.width - 210, Math.max(10, (hoveredNode.x * zoom + pan.x) - 100))}px`,
            top: `${Math.min(dimensions.height - 70, Math.max(10, (hoveredNode.y * zoom + pan.y) - 65))}px`,
          }}
        >
          <div className="flex justify-between pb-0.5 mb-1">
            <span className={`font-bold capitalize ${hoveredNode.speaker === "human" ? "text-[#6bc28c]" :
              hoveredNode.speaker === "proposed" ? "text-[#e09b67]" : "text-[#a892ee]"
              }`}>
              {hoveredNode.speaker === "proposed" ? `Agential Proposal: ${hoveredNode.title}` : hoveredNode.speaker}
            </span>
            <span className="text-[#555] ml-2">
              {hoveredNode.isProposed ? "Consent Required" : `ID: ${hoveredNode.dbId}`}
            </span>
          </div>
          <div className="text-[#94a3b8] line-clamp-2">
            {hoveredNode.content}
          </div>
        </div>
      )}

      {/* Branch Commit Modal — minimal */}
      {committingNode && (
        <div className="absolute inset-0 bg-[#09090b]/80 flex flex-col justify-end p-3 z-20">
          <div className="flex flex-col gap-2">
            <div className="flex justify-between items-center">
              <span className="text-[10px] font-mono font-bold text-semantic-purple uppercase tracking-wider">
                [ Commit Line of Flight ]
              </span>
              <button onClick={() => setCommittingNode(null)}
                className="text-[10px] font-mono text-action-dim hover:text-semantic-red cursor-pointer select-none">[cancel]</button>
            </div>
            <div className="text-[10px] font-mono text-[#94a3b8]">
              Topic: <span className="text-[#ccc]">{committingNode.title}</span>
            </div>
            <textarea
              value={commitContent}
              onChange={(e) => setCommitContent(e.target.value)}
              rows={4}
              className="w-full bg-[#08080c] border border-[#1b1b21] p-2 text-xs font-mono text-[#e4e4e7] focus:outline-none focus:border-action-hover/50 resize-none"
            />
            <button
              onClick={handleCommitSubmit}
              disabled={isCommitLoading || !commitContent.trim()}
              className="text-[10px] font-mono text-action-dim hover:text-action-hover disabled:text-[#555] disabled:cursor-not-allowed cursor-pointer select-none self-start"
            >
              {isCommitLoading ? "[committing...]" : "[commit branch to DAG]"}
            </button>
          </div>
        </div>
      )}

      {/* Resonance Link Details — minimal */}
      {selectedLink && selectedLinkPos && (
        <div
          className="absolute z-20 p-2.5 bg-[#0d0d12]/95 text-[10px] font-mono w-[220px]"
          style={{
            left: `${Math.min(dimensions.width - 230, Math.max(10, (selectedLinkPos.x * zoom + pan.x) - 110))}px`,
            top: `${Math.min(dimensions.height - 110, Math.max(10, (selectedLinkPos.y * zoom + pan.y) - 95))}px`,
          }}
        >
          <div className="flex justify-between pb-1 mb-1">
            <span className={`font-bold ${selectedLink.status === "proposed" ? "text-[#e09b67]" : "text-[#94a3b8]"}`}>
              {selectedLink.status === "proposed" ? "Proposed Resonance" : "Resonance Link"}
            </span>
            <button
              onClick={(e) => { e.stopPropagation(); setSelectedLink(null); setSelectedLinkPos(null) }}
              className="text-[#666] hover:text-[#888] cursor-pointer select-none">[close]</button>
          </div>

          {selectedLink.justification && (
            <div className="text-[#94a3b8] mb-2 italic">
              "{selectedLink.justification}"
            </div>
          )}

          <div className="flex gap-2">
            {selectedLink.status === "proposed" ? (
              <>
                <button
                  onClick={async (e) => {
                    e.stopPropagation()
                    if (selectedLink.id && conversationId) {
                      try { await confirmResonanceLink(conversationId, selectedLink.id); refreshTree() }
                      catch (err) { console.error("Failed to confirm link", err) }
                    }
                    setSelectedLink(null); setSelectedLinkPos(null)
                  }}
                  className="text-[9px] text-semantic-green hover:text-action-hover font-mono cursor-pointer select-none"
                >[confirm]</button>
                <button
                  onClick={async (e) => {
                    e.stopPropagation()
                    if (selectedLink.id && conversationId) {
                      try { await deleteResonanceLink(conversationId, selectedLink.id); refreshTree() }
                      catch (err) { console.error("Failed to delete link", err) }
                    }
                    setSelectedLink(null); setSelectedLinkPos(null)
                  }}
                  className="text-[9px] text-semantic-red hover:text-action-hover font-mono cursor-pointer select-none"
                >[dismiss]</button>
              </>
            ) : (
              <button
                onClick={async (e) => {
                  e.stopPropagation()
                  if (selectedLink.id && conversationId) {
                    try { await deleteResonanceLink(conversationId, selectedLink.id); refreshTree() }
                    catch (err) { console.error("Failed to delete link", err) }
                  }
                  setSelectedLink(null); setSelectedLinkPos(null)
                }}
                className="text-[9px] text-semantic-red hover:text-action-hover font-mono cursor-pointer select-none"
              >[remove link]</button>
            )}
          </div>
        </div>
      )}
    </>
  )
})
