import { useState, useEffect } from "react"
import type {
  ConversationFile,
  SkillsResponse,
  ImageMetadata,
  WebMetadata,
  DocumentMetadata,
  NoteInfo,
} from "../api/client"
import { getSkills, getFileSummary } from "../api/client"
import { useTelemetry } from "../hooks/useTelemetry"
import { SectionHeader } from "./sidepanel/SectionHeader"
import { SkillRow } from "./sidepanel/SkillRow"
import { VitalitySection } from "./sidepanel/VitalitySection"
import { BeliefsSection } from "./sidepanel/BeliefsSection"
import { DiffractionSection } from "./sidepanel/DiffractionSection"
import { DreamingSection } from "./sidepanel/DreamingSection"
import { StartupSection } from "./sidepanel/StartupSection"
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
  scrollToNoteRef,
}: {
  uploadedFiles?: ConversationFile[]
  conversationId?: string
  onDeleteFile?: (fileName: string) => void
  onReprocessFile?: (fileName: string) => void
  messageCount?: number
  notes?: NoteInfo[]
  onDeleteNote?: (noteId: string) => void
  onUpdateNote?: (noteId: string, comment?: string, visibility?: "personal" | "shared") => void
  summary?: string
  humanSummary?: string
  width?: number
  panelCollapsed?: boolean
  onPanelToggle?: () => void
  scrollToNoteRef?: React.MutableRefObject<((noteId: string) => void) | null>
}) {
  const [collapsed, setCollapsed] = useState(true)
  const isCollapsed = panelCollapsed !== undefined ? panelCollapsed : collapsed
  const togglePanel = () => {
    if (onPanelToggle) onPanelToggle()
    else setCollapsed(p => !p)
  }
  const [skillsData, setSkillsData] = useState<SkillsResponse | null>(null)
  const [skillsError, setSkillsError] = useState<string | null>(null)

  // Section visibility states
  const [healthOpen, setHealthOpen] = useState(false)
  const [beliefsOpen, setBeliefsOpen] = useState(false)
  const [diffractiveOpen, setDiffractiveOpen] = useState(false)
  const [dreamingOpen, setDreamingOpen] = useState(false)
  const [startupOpen, setStartupOpen] = useState(false)
  const [tokensOpen, setTokensOpen] = useState(false)
  const [notesOpen, setNotesOpen] = useState(false)
  const [sedimentOpen, setSedimentOpen] = useState(false)
  const [pipelineOpen, setPipelineOpen] = useState(false)
  const [skillsOpen, setSkillsOpen] = useState(false)
  const [summaryOpen, setSummaryOpen] = useState(false)
  const [memoryNodesOpen, setMemoryNodesOpen] = useState(false)

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

  // Orchestrated polling hook
  const {
    metrics,
    metricsError,
    beliefs,
    beliefsError,
    scheduler,
    schedulerError,
    daemon,
    daemonError,
    tokens,
    tokensError,
  } = useTelemetry(
    isCollapsed,
    conversationId || null,
    {
      health: healthOpen,
      diffraction: diffractiveOpen,
      beliefs: beliefsOpen,
      dreaming: dreamingOpen,
      scheduler: startupOpen,
      tokens: tokensOpen,
    }
  )

  // Local skills registry fetch (on-demand)
  useEffect(() => {
    if ((pipelineOpen || skillsOpen) && !skillsData) {
      getSkills()
        .then(setSkillsData)
        .catch((e) => setSkillsError(e.message))
    }
  }, [pipelineOpen, skillsOpen, skillsData])

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
            select-none
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
              className="flex items-center gap-1.5 text-[10px] text-[#555] hover:text-[#888] transition-colors"
            >
              <span>▶</span>
              <span>close</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-3 pb-3">
            {/* ── conversation ──────────────────────── */}

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
                    scrollToNoteRef={scrollToNoteRef}
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

            {/* ── agent ──────────────────────────── */}

            <div className="mt-3 mb-1.5 border-t border-[#1a1a1a] pt-2">
              <span className="text-[8px] text-[#444] uppercase font-mono tracking-[0.2em] select-none">agent</span>
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Beliefs"
                open={beliefsOpen}
                onToggle={() => setBeliefsOpen(!beliefsOpen)}
              />
              {beliefsOpen && (
                <div className="pl-3">
                  <BeliefsSection data={beliefs} error={beliefsError} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Dreaming"
                open={dreamingOpen}
                onToggle={() => setDreamingOpen(!dreamingOpen)}
              />
              {dreamingOpen && (
                <div className="pl-3">
                  <DreamingSection status={daemon} error={daemonError} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Daemons"
                open={startupOpen}
                onToggle={() => setStartupOpen(!startupOpen)}
              />
              {startupOpen && (
                <div className="pl-3">
                  <StartupSection status={scheduler} error={schedulerError} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Pipeline"
                count={skillsData ? skillsData.pipeline.length : undefined}
                open={pipelineOpen}
                onToggle={() => setPipelineOpen(!pipelineOpen)}
              />
              {pipelineOpen && (
                <div className="pl-3">
                  {skillsError && (
                    <p className="text-[10px] text-[#ef4444] font-mono py-1">
                      Error: {skillsError}
                    </p>
                  )}
                  {!skillsData && !skillsError && (
                    <p className="text-[10px] text-[#555] animate-pulse py-1">loading pipeline...</p>
                  )}
                  {skillsData && skillsData.pipeline.map((s) => (
                    <SkillRow key={s.name} skill={s} />
                  ))}
                </div>
              )}

              <SectionHeader
                label="Skills"
                count={skillsData ? skillsData.on_demand.length : undefined}
                open={skillsOpen}
                onToggle={() => setSkillsOpen(!skillsOpen)}
              />
              {skillsOpen && (
                <div className="pl-3">
                  {skillsError && (
                    <p className="text-[10px] text-[#ef4444] font-mono py-1">
                      Error: {skillsError}
                    </p>
                  )}
                  {!skillsData && !skillsError && (
                    <p className="text-[10px] text-[#555] animate-pulse py-1">loading skills...</p>
                  )}
                  {skillsData && skillsData.on_demand.length === 0 && (
                    <p className="text-[10px] text-[#444] py-1">no on-demand skills available</p>
                  )}
                  {skillsData && skillsData.on_demand.map((s) => (
                    <SkillRow key={s.name} skill={s} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
