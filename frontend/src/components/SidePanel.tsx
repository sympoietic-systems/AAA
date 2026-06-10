import { useState, useEffect } from "react"
import type {
  ConversationFile,
  DbSkillsResponse,
  ImageMetadata,
  NoteInfo,
  WebMetadata,
  DocumentMetadata,
  ChatMessage,
} from "../api/client"
import {
  getDbSkills,
  getSkillContent,
  getFileSummary,
} from "../api/client"
import { useTelemetry } from "../hooks/useTelemetry"
import { SectionHeader } from "./sidepanel/SectionHeader"
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
import ConnectionCloud from "./ConnectionCloud"
import { SpectralEchoes } from "./SpectralEchoes"

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
  fullTreeMessages = [],
  links = [],
  activeMessageId = null,
  activePathIds = new Set<number>(),
  setActiveMessageId = () => {},
  commitProposedBranch = async () => null,
  refreshTree = () => {},
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
  fullTreeMessages?: ChatMessage[]
  links?: any[]
  activeMessageId?: number | null
  activePathIds?: Set<number>
  setActiveMessageId?: (id: number | null) => void
  commitProposedBranch?: (parentMsgId: number, content: string) => Promise<any>
  refreshTree?: () => void
}) {
  const [collapsed, setCollapsed] = useState(true)
  const isCollapsed = panelCollapsed !== undefined ? panelCollapsed : collapsed
  const togglePanel = () => {
    if (onPanelToggle) onPanelToggle()
    else setCollapsed(p => !p)
  }
  const [dbSkillsData, setDbSkillsData] = useState<DbSkillsResponse | null>(null)
  const [dbSkillsError, setDbSkillsError] = useState<string | null>(null)
  const [dbSkillsOpen, setDbSkillsOpen] = useState(false)
  const [expandedSkill, setExpandedSkill] = useState<string | null>(null)
  const [skillContent, setSkillContent] = useState<Record<string, string>>({})
  const [loadingSkillContent, setLoadingSkillContent] = useState<string | null>(null)

  // Section visibility states
  const [healthOpen, setHealthOpen] = useState(false)
  const [beliefsOpen, setBeliefsOpen] = useState(false)
  const [diffractiveOpen, setDiffractiveOpen] = useState(false)
  const [dreamingOpen, setDreamingOpen] = useState(false)
  const [startupOpen, setStartupOpen] = useState(false)
  const [tokensOpen, setTokensOpen] = useState(false)
  const [notesOpen, setNotesOpen] = useState(false)
  const [sedimentOpen, setSedimentOpen] = useState(false)
  const [summaryOpen, setSummaryOpen] = useState(false)
  const [memoryNodesOpen, setMemoryNodesOpen] = useState(false)
  const [cloudOpen, setCloudOpen] = useState(true)
  const [spectralEchoesOpen, setSpectralEchoesOpen] = useState(true)

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

  // DB skills fetch (Symbia's procedural skills) — fetch on mount
  useEffect(() => {
    if (!dbSkillsData && !dbSkillsError) {
      console.log("[Skills] Fetching /api/skills/db...")
      getDbSkills()
        .then(data => {
          console.log("[Skills] Received:", data)
          if (!data || (!data.always_active && !data.on_demand)) {
            console.warn("[Skills] Empty or malformed response:", data)
          }
          setDbSkillsData({ always_active: data?.always_active || [], on_demand: data?.on_demand || [], all: data?.all || data?.always_active?.concat(data?.on_demand || []) || [] })
        })
        .catch(e => {
          console.error("[Skills] Error:", e)
          setDbSkillsError(e.message || String(e))
        })
    }
  }, [dbSkillsData, dbSkillsError])

  const handleLoadSkillContent = async (skillName: string) => {
    if (expandedSkill === skillName) {
      setExpandedSkill(null)
      return
    }
    if (skillContent[skillName]) {
      setExpandedSkill(skillName)
      return
    }
    setLoadingSkillContent(skillName)
    try {
      const result = await getSkillContent(skillName)
      const text = result.content
        || result.description
        || `(no content available — lifecycle: ${result.lifecycle_stage || "unknown"}, status: ${result.status || "unknown"})`
      setSkillContent(prev => ({ ...prev, [skillName]: text }))
      setExpandedSkill(skillName)
    } catch (e: any) {
      setSkillContent(prev => ({ ...prev, [skillName]: `Failed to load: ${e.message}` }))
      setExpandedSkill(skillName)
    } finally {
      setLoadingSkillContent(null)
    }
  }

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
                label="Connection Cloud"
                open={cloudOpen}
                onToggle={() => setCloudOpen(!cloudOpen)}
              />
              {cloudOpen && (
                <div className="w-full h-[550px] my-1">
                  <ConnectionCloud
                    messages={fullTreeMessages}
                    links={links}
                    notes={notes}
                    activeMessageId={activeMessageId}
                    activePathIds={activePathIds}
                    setActiveMessageId={setActiveMessageId}
                    commitProposedBranch={commitProposedBranch}
                    refreshTree={refreshTree}
                    conversationId={conversationId || ""}
                  />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Spectral Echoes"
                open={spectralEchoesOpen}
                onToggle={() => setSpectralEchoesOpen(!spectralEchoesOpen)}
              />
              {spectralEchoesOpen && (
                <div className="pl-3 pr-2 my-1">
                  <SpectralEchoes
                    conversationId={conversationId || ""}
                    activeMessageId={activeMessageId}
                    refreshTree={refreshTree}
                  />
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
              {/* DB Procedural Skills (Symbia's own skills) */}
              <SectionHeader
                label="Skills"
                count={dbSkillsData ? (dbSkillsData.all.length) : undefined}
                open={dbSkillsOpen}
                onToggle={() => setDbSkillsOpen(!dbSkillsOpen)}
              />
              {dbSkillsOpen && (
                <div className="pl-3">
                  {dbSkillsError ? (
                    <p className="text-[10px] text-[#ef4444] font-mono py-1">Error: {dbSkillsError}</p>
                  ) : !dbSkillsData ? (
                    <p className="text-[10px] text-[#555] animate-pulse py-1">loading skills...</p>
                  ) : (
                    <>
                      {dbSkillsData.always_active && dbSkillsData.always_active.length > 0 && (
                        <div className="mb-2">
                          <p className="text-[9px] text-[#888] uppercase tracking-wider mb-1">Baseline Dispositions</p>
                          {dbSkillsData.always_active.map((s: any) => (
                            <div key={s.id} className="mb-1">
                              <div
                                className="flex items-center gap-1 cursor-pointer hover:bg-[#1a1a2e] rounded px-1 py-0.5"
                                onClick={() => handleLoadSkillContent(s.name)}
                              >
                                <span className="text-[9px] text-[#a78bfa]">◆</span>
                                <span className="text-[11px] text-[#e2e8f0] font-mono">{s.name}</span>
                                <span className="text-[8px] text-[#555] ml-auto">
                                  {loadingSkillContent === s.name ? "..." : expandedSkill === s.name ? "▲" : "▼"}
                                </span>
                              </div>
                              {expandedSkill === s.name && skillContent[s.name] && (
                                <div className="ml-4 mt-1 p-2 bg-[#0d0d1a] border border-[#1a1a2e] rounded text-[10px] text-[#94a3b8] font-mono whitespace-pre-wrap max-h-60 overflow-y-auto">
                                  {skillContent[s.name]}
                                </div>
                              )}
                              {expandedSkill === s.name && s.vector_16d && s.vector_16d.length > 0 && (
                                <div className="ml-4 mt-1">
                                  <div className="text-[#555] font-mono text-[8px] uppercase mb-1">[ 16D Structural Vector ]</div>
                                  <div className="flex items-end gap-0.5 h-4 bg-[#08080c] border border-[#1a1a24] p-0.5 rounded w-fit">
                                    {(s.vector_16d as number[]).map((val: number, idx: number) => {
                                      const heightPercent = Math.min(100, Math.max(10, Math.round(((val + 1.0) / 2.0) * 100)))
                                      return (
                                        <div
                                          key={idx}
                                          style={{ height: `${heightPercent}%` }}
                                          title={`Dim ${idx + 1}: ${val.toFixed(4)}`}
                                          className="w-1 bg-[#a78bfa]/50 hover:bg-[#a78bfa]"
                                        />
                                      )
                                    })}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      {dbSkillsData.on_demand.length > 0 && (
                        <div>
                          <p className="text-[9px] text-[#888] uppercase tracking-wider mb-1">On-Demand Capabilities</p>
                          {dbSkillsData.on_demand.map((s) => (
                            <div key={s.id} className="mb-1">
                              <div
                                className="flex items-center gap-1 cursor-pointer hover:bg-[#1a1a2e] rounded px-1 py-0.5"
                                onClick={() => handleLoadSkillContent(s.name)}
                              >
                                <span className="text-[9px] text-[#4ade80]">◇</span>
                                <div className="flex-1 min-w-0">
                                  <span className="text-[11px] text-[#e2e8f0] font-mono">{s.name}</span>
                                  <span className="text-[9px] text-[#666] ml-1">
                                    c:{s.confidence.toFixed(1)} m:{s.ontological_mass.toFixed(1)}
                                  </span>
                                </div>
                                <span className="text-[8px] text-[#555] flex-shrink-0">
                                  {loadingSkillContent === s.name ? "..." : expandedSkill === s.name ? "▲" : "▼"}
                                </span>
                              </div>
                              {expandedSkill === s.name && skillContent[s.name] && (
                                <div className="ml-4 mt-1 p-2 bg-[#0d0d1a] border border-[#1a1a2e] rounded text-[10px] text-[#94a3b8] font-mono whitespace-pre-wrap max-h-60 overflow-y-auto">
                                  {skillContent[s.name]}
                                </div>
                              )}
                              {expandedSkill === s.name && s.vector_16d && s.vector_16d.length > 0 && (
                                <div className="ml-4 mt-1">
                                  <div className="text-[#555] font-mono text-[8px] uppercase mb-1">[ 16D Structural Vector ]</div>
                                  <div className="flex items-end gap-0.5 h-4 bg-[#08080c] border border-[#1a1a24] p-0.5 rounded w-fit">
                                    {(s.vector_16d as number[]).map((val: number, idx: number) => {
                                      const heightPercent = Math.min(100, Math.max(10, Math.round(((val + 1.0) / 2.0) * 100)))
                                      return (
                                        <div
                                          key={idx}
                                          style={{ height: `${heightPercent}%` }}
                                          title={`Dim ${idx + 1}: ${val.toFixed(4)}`}
                                          className="w-1 bg-[#a78bfa]/50 hover:bg-[#a78bfa]"
                                        />
                                      )
                                    })}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
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
