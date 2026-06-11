import { useState, useCallback } from "react"
import type {
  ConversationFile,
  ImageMetadata,
  NoteInfo,
  WebMetadata,
  DocumentMetadata,
} from "../api/client"
import { getFileSummary } from "../api/client"
import { SectionHeader } from "./sidepanel/SectionHeader"
import { VitalitySection } from "./sidepanel/VitalitySection"
import { DiffractionSection } from "./sidepanel/DiffractionSection"
import { TokensSection } from "./sidepanel/TokensSection"
import { NotesSection } from "./sidepanel/NotesSection"
import { SedimentSection } from "./sidepanel/SedimentSection"
import { SummarySection } from "./sidepanel/SummarySection"
import { MemoryNodesSection } from "./sidepanel/MemoryNodesSection"
import { AttractorsSection } from "./sidepanel/AttractorsSection"

export function SidePanel({
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

  // Section visibility states
  const [healthOpen, setHealthOpen] = useState(false)
  const [diffractiveOpen, setDiffractiveOpen] = useState(false)
  const [tokensOpen, setTokensOpen] = useState(false)
  const [notesOpen, setNotesOpen] = useState(false)
  const [sedimentOpen, setSedimentOpen] = useState(false)
  const [summaryOpen, setSummaryOpen] = useState(false)
  const [memoryNodesOpen, setMemoryNodesOpen] = useState(false)
  const [attractorsOpen, setAttractorsOpen] = useState(false)

  // Sediment detail state (file summary expansion)
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

  const handleNotesOpenToggle = useCallback(() => setNotesOpen(o => !o), [])
  const handleSummaryOpenToggle = useCallback(() => setSummaryOpen(o => !o), [])
  const handleMemoryNodesOpenToggle = useCallback(() => setMemoryNodesOpen(o => !o), [])
  const handleSedimentOpenToggle = useCallback(() => setSedimentOpen(o => !o), [])
  const handleTokensOpenToggle = useCallback(() => setTokensOpen(o => !o), [])
  const handleHealthOpenToggle = useCallback(() => setHealthOpen(o => !o), [])
  const handleDiffractiveOpenToggle = useCallback(() => setDiffractiveOpen(o => !o), [])
  const handleAttractorsOpenToggle = useCallback(() => setAttractorsOpen(o => !o), [])

  const panelOpen = !isCollapsed

  return (
    <div
      className={`
        border-[#222] bg-[#0c0c0c]
        md:border-l md:border-t-0 md:h-full
        border-t
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
          <div className="flex items-center shrink-0 px-3 py-2 border-b border-[#222]">
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
              <SectionHeader
                label="Summary"
                open={summaryOpen}
                onToggle={handleSummaryOpenToggle}
              />
              {summaryOpen && (
                <div className="pl-3">
                  <SummarySection summary={summary} humanSummary={humanSummary} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Memory Nodes"
                open={memoryNodesOpen}
                onToggle={handleMemoryNodesOpenToggle}
              />
              {memoryNodesOpen && (
                <div className="pl-3">
                  <MemoryNodesSection
                    conversationId={conversationId}
                    enabled={panelOpen && memoryNodesOpen}
                  />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Notes"
                count={notes.length}
                open={notesOpen}
                onToggle={handleNotesOpenToggle}
              />
              {notesOpen && (
                <div className="pl-3">
                  <NotesSection
                    notes={notes}
                    onDeleteNote={onDeleteNote}
                    onUpdateNote={onUpdateNote}
                    onNavigate={onNavigateNode}
                  />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Sediment"
                count={uploadedFiles.length}
                open={sedimentOpen}
                onToggle={handleSedimentOpenToggle}
              />
              {sedimentOpen && (
                <SedimentSection
                  conversationId={conversationId}
                  uploadedFiles={uploadedFiles}
                  onDeleteFile={onDeleteFile}
                  onReprocessFile={onReprocessFile}
                  expandedFile={expandedFile}
                  loadingSummary={loadingSummary}
                  loadedSummaries={loadedSummaries}
                  onToggleSummary={handleToggleSummary}
                />
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Tokens"
                open={tokensOpen}
                onToggle={handleTokensOpenToggle}
              />
              {tokensOpen && (
                <div className="pl-3">
                  <TokensSection
                    conversationId={conversationId}
                    enabled={panelOpen && tokensOpen}
                    messageCount={messageCount}
                  />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Vitality"
                open={healthOpen}
                onToggle={handleHealthOpenToggle}
              />
              {healthOpen && (
                <div className="pl-3">
                  <VitalitySection
                    enabled={panelOpen && healthOpen}
                    messageCount={messageCount}
                  />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Diffraction"
                open={diffractiveOpen}
                onToggle={handleDiffractiveOpenToggle}
              />
              {diffractiveOpen && (
                <div className="pl-3">
                  <DiffractionSection
                    enabled={panelOpen && diffractiveOpen}
                    messageCount={messageCount}
                  />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Attractors"
                open={attractorsOpen}
                onToggle={handleAttractorsOpenToggle}
              />
              {attractorsOpen && (
                <div className="pl-3">
                  <AttractorsSection
                    conversationId={conversationId}
                    enabled={panelOpen && attractorsOpen}
                    messageCount={messageCount}
                  />
                </div>
              )}
            </div>

          </div>
        </>
      )}
    </div>
  )
}
