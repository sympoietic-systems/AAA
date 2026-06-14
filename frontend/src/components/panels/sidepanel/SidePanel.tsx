import { useState, useCallback, memo } from "react"
import type {
  ConversationFile,
  NoteInfo,
} from "../../../api/client"
import { SectionHeader } from "./SectionHeader"
import { VitalitySection } from "./VitalitySection"
import { DiffractionSection } from "./DiffractionSection"
import { TokensSection } from "./TokensSection"
import { NotesSection } from "./NotesSection"
import { SedimentSection } from "./SedimentSection"
import { SummarySection } from "./SummarySection"
import { MemoryNodesSection } from "./MemoryNodesSection"
import { AttractorsSection } from "./AttractorsSection"

export const SidePanel = memo(function SidePanel({
  uploadedFiles = [],
  conversationId,
  onDeleteFile,
  onReprocessFile,
  messageCount = 0,
  notes = [],
  onDeleteNote,
  onUpdateNote,
  summary,
  humanSummary,
  width,
  panelCollapsed,
  onPanelToggle,
  onNavigateNode,
}: {
  uploadedFiles?: ConversationFile[]
  conversationId?: string
  onDeleteFile?: (fileName: string) => void
  onReprocessFile?: (fileName: string) => void
  messageCount?: number
  notes?: NoteInfo[]
  onDeleteNote?: (noteId: string) => void
  onUpdateNote?: (noteId: string, comment?: string, visibility?: "personal" | "shared" | "agent") => void
  summary?: string
  humanSummary?: string
  width?: number
  panelCollapsed?: boolean
  onPanelToggle?: () => void
  onNavigateNode?: (messageId: number) => void
}) {
  const [collapsed, setCollapsed] = useState(true)
  const isCollapsed = panelCollapsed !== undefined ? panelCollapsed : collapsed
  const togglePanel = useCallback(() => {
    if (onPanelToggle) onPanelToggle()
    else setCollapsed(p => !p)
  }, [onPanelToggle])

  // Section visibility states — single Record instead of 8 separate useState
  const [sections, setSections] = useState<Record<string, boolean>>({
    summary: false, memoryNodes: false, notes: false, sediment: false,
    tokens: false, health: false, diffractive: false, attractors: false,
  })

  const toggleSection = useCallback((key: string) => {
    setSections(prev => ({ ...prev, [key]: !prev[key] }))
  }, [])

  const panelOpen = !isCollapsed

  return (
    <div
      className={`
        md:border-l md:border-t-0 md:h-full
        border-t border-[#222]/40
        flex flex-col shrink-0
        overflow-hidden
        transition-all duration-200
        ${isCollapsed ? "md:w-9 w-full" : "w-full"}
      `}
      style={!isCollapsed && width ? { width: `${width}px` } : undefined}
    >
      {isCollapsed && (
        <button
          onClick={togglePanel}
          className="
            flex items-center gap-1.5 shrink-0
            text-xs text-[#555] hover:text-[#888]
            transition-colors
            md:flex-col md:justify-start md:gap-2 md:py-3 md:px-0
            md:h-full
            flex-row justify-start py-2 px-3
            select-none cursor-pointer
          "
        >
          <span className="text-[10px]">◀</span>
          <span className="md:[writing-mode:vertical-rl] md:text-[10px] md:tracking-wider text-[11px]">
            pipeline
          </span>
        </button>
      )}

      {!isCollapsed && (
        <>
          <div className="flex items-center shrink-0 px-3 py-2 border-b border-[#222]/40">
            <button
              onClick={togglePanel}
              className="flex items-center gap-1.5 text-[10px] text-[#555] hover:text-[#888] transition-colors cursor-pointer"
            >
              <span>▶</span>
              <span>close</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-3 pb-3">

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader label="Summary" open={sections.summary} onToggle={() => toggleSection("summary")} />
              {sections.summary && (
                <div className="pl-3"><SummarySection summary={summary} humanSummary={humanSummary} /></div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader label="Memory Nodes" open={sections.memoryNodes} onToggle={() => toggleSection("memoryNodes")} />
              {sections.memoryNodes && (
                <div className="pl-3">
                  <MemoryNodesSection conversationId={conversationId} enabled={panelOpen && sections.memoryNodes} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader label="Notes" count={notes.length} open={sections.notes} onToggle={() => toggleSection("notes")} />
              {sections.notes && (
                <div className="pl-3">
                  <NotesSection notes={notes} onDeleteNote={onDeleteNote} onUpdateNote={onUpdateNote} onNavigate={onNavigateNode} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader label="Sediment" count={uploadedFiles.length} open={sections.sediment} onToggle={() => toggleSection("sediment")} />
              {sections.sediment && (
                <SedimentSection conversationId={conversationId} uploadedFiles={uploadedFiles} onDeleteFile={onDeleteFile} onReprocessFile={onReprocessFile} />
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader label="Tokens" open={sections.tokens} onToggle={() => toggleSection("tokens")} />
              {sections.tokens && (
                <div className="pl-3">
                  <TokensSection conversationId={conversationId} enabled={panelOpen && sections.tokens} messageCount={messageCount} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader label="Vitality" open={sections.health} onToggle={() => toggleSection("health")} />
              {sections.health && (
                <div className="pl-3">
                  <VitalitySection enabled={panelOpen && sections.health} messageCount={messageCount} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader label="Diffraction" open={sections.diffractive} onToggle={() => toggleSection("diffractive")} />
              {sections.diffractive && (
                <div className="pl-3">
                  <DiffractionSection enabled={panelOpen && sections.diffractive} messageCount={messageCount} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader label="Attractors" open={sections.attractors} onToggle={() => toggleSection("attractors")} />
              {sections.attractors && (
                <div className="pl-3">
                  <AttractorsSection conversationId={conversationId} enabled={panelOpen && sections.attractors} messageCount={messageCount} />
                </div>
              )}
            </div>

          </div>
        </>
      )}
    </div>
  )
})
