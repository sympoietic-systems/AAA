import { useState } from "react"
import type {
  ConversationFile,
  ImageMetadata,
  NoteInfo,
  WebMetadata,
  DocumentMetadata,
} from "../api/client"
import { getFileSummary } from "../api/client"
import { useTelemetry } from "../hooks/useTelemetry"
import { SectionHeader } from "./sidepanel/SectionHeader"
import { VitalitySection } from "./sidepanel/VitalitySection"
import { DiffractionSection } from "./sidepanel/DiffractionSection"
import { TokensSection } from "./sidepanel/TokensSection"
import { NotesSection } from "./sidepanel/NotesSection"
import { SedimentSection } from "./sidepanel/SedimentSection"
import { SummarySection } from "./sidepanel/SummarySection"
import { MemoryNodesSection } from "./sidepanel/MemoryNodesSection"

export function SidePanel({
  uploadedFiles = [],
  conversationId,
  onDeleteFile,
  onReprocessFile,
  messageCount: _messageCount = 0,
  notes = [],
  onDeleteNote,
  onUpdateNote,
  summary,
  humanSummary,
  width,
  panelCollapsed,
  onPanelToggle,
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
}) {
  const [collapsed, setCollapsed] = useState(true)
  const isCollapsed = panelCollapsed !== undefined ? panelCollapsed : collapsed
  const togglePanel = () => {
    if (onPanelToggle) onPanelToggle()
    else setCollapsed(p => !p)
  }

  // Section visibility states
  const [healthOpen, setHealthOpen] = useState(false)
  const [diffractiveOpen, setDiffractiveOpen] = useState(false)
  const [tokensOpen, setTokensOpen] = useState(false)
  const [notesOpen, setNotesOpen] = useState(false)
  const [sedimentOpen, setSedimentOpen] = useState(false)
  const [summaryOpen, setSummaryOpen] = useState(false)
  const [memoryNodesOpen, setMemoryNodesOpen] = useState(false)
  const [attractorsOpen, setAttractorsOpen] = useState(false)

  // Sediment detail state
  const [expandedFile, setExpandedFile] = useState<string | null>(null)
  const [loadedSummaries, setLoadedSummaries] = useState<Record<string, {
    summary: string | null
    summary_model: string | null
    image_metadata?: ImageMetadata | null
    web_metadata?: WebMetadata | null
    document_metadata?: DocumentMetadata | null
  }>>({})
  const [loadingSummary, setLoadingSummary] = useState<string | null>(null)

  // Telemetry — only conversation-scoped metrics
  const {
    metrics,
    metricsError,
    tokens,
    tokensError,
    beliefs,
    beliefsError,
  } = useTelemetry(
    isCollapsed,
    conversationId || null,
    {
      health: healthOpen,
      diffraction: diffractiveOpen,
      beliefs: attractorsOpen,
      dreaming: false,
      scheduler: false,
      tokens: tokensOpen,
    },
    _messageCount
  )

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
                onToggle={() => setSummaryOpen(!summaryOpen)}
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
                onToggle={() => setMemoryNodesOpen(!memoryNodesOpen)}
              />
              {memoryNodesOpen && (
                <div className="pl-3">
                  <MemoryNodesSection conversationId={conversationId} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Notes"
                count={notes.length}
                open={notesOpen}
                onToggle={() => setNotesOpen(!notesOpen)}
              />
              {notesOpen && (
                <div className="pl-3">
                  <NotesSection
                    notes={notes}
                    onDeleteNote={onDeleteNote}
                    onUpdateNote={onUpdateNote}
                  />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Sediment"
                count={uploadedFiles.length}
                open={sedimentOpen}
                onToggle={() => setSedimentOpen(!sedimentOpen)}
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
                onToggle={() => setTokensOpen(!tokensOpen)}
              />
              {tokensOpen && (
                <div className="pl-3">
                  <TokensSection tokens={tokens} error={tokensError} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Vitality"
                open={healthOpen}
                onToggle={() => setHealthOpen(!healthOpen)}
              />
              {healthOpen && (
                <div className="pl-3">
                  <VitalitySection metrics={metrics} error={metricsError} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Diffraction"
                open={diffractiveOpen}
                onToggle={() => setDiffractiveOpen(!diffractiveOpen)}
              />
              {diffractiveOpen && (
                <div className="pl-3">
                  <DiffractionSection metrics={metrics} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Attractors"
                open={attractorsOpen}
                onToggle={() => setAttractorsOpen(!attractorsOpen)}
              />
              {attractorsOpen && (
                <div className="pl-3 text-[10px] font-mono space-y-2">
                  {beliefsError ? (
                    <p className="text-[9px] text-[#ef4444]">{beliefsError}</p>
                  ) : !beliefs ? (
                    <p className="text-[9px] text-[#444] animate-pulse">loading...</p>
                  ) : (
                    <>
                      {beliefs.attractor_window.length === 0 ? (
                        <p className="text-[9px] text-[#444] italic">No active attractors</p>
                      ) : (
                        <div>
                          <span className="text-[#6c6c8a] text-[8px] uppercase tracking-wider block mb-1">
                            [ Attractor Window ]
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {beliefs.attractor_window.map((label) => {
                              const b = [...(beliefs.beliefs || []), ...(beliefs.proto_beliefs || []), ...(beliefs.ghosts || [])].find(x => x.label === label)
                              const catColor =
                                b?.category === "foundational" ? "#4ade80"
                                : b?.category === "ontological" ? "#a78bfa"
                                : b?.category === "methodological" ? "#facc15"
                                : "#555"
                              return (
                                <span
                                  key={label}
                                  title={b ? `${b.category} · mass ${b.ontological_mass.toFixed(1)} · ${(b.confidence * 100).toFixed(0)}%` : label}
                                  className="text-[9px] font-mono bg-[#141414] text-[#aaa] border border-[#222] px-1.5 py-0.5 rounded inline-flex items-center gap-1 cursor-help hover:border-[#444] transition-colors"
                                >
                                  <span className="text-[8px] leading-none" style={{ color: catColor }}>●</span>
                                  {label}
                                </span>
                              )
                            })}
                          </div>
                        </div>
                      )}
                      {beliefs.spectral_margin.length > 0 && (
                        <div>
                          <span className="text-[#6c6c8a] text-[8px] uppercase tracking-wider block mb-1">
                            [ Spectral Margin ]
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {beliefs.spectral_margin.map((label) => (
                              <span
                                key={label}
                                className="text-[9px] font-mono bg-[#141414] text-[#888]/60 border border-[#222]/60 px-1.5 py-0.5 rounded inline-flex items-center gap-1 opacity-70 line-through cursor-help hover:border-[#444]/60 transition-colors"
                              >
                                👻 {label}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>

          </div>
        </>
      )}
    </div>
  )
}
