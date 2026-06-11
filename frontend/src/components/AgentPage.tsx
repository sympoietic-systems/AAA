import { useState, useEffect, useCallback } from "react"
import {
  getBeliefs,
  getDaemonStatus,
  getSchedulerStatus,
  getDbSkills,
  getSkillContent,
} from "../api/client"
import type {
  BeliefsResponse,
  DaemonStatusResponse,
  SchedulerStatusResponse,
  DbSkillsResponse,
} from "../api/client"
import { BeliefsSection } from "./sidepanel/BeliefsSection"
import { DreamingSection } from "./sidepanel/DreamingSection"
import { StartupSection } from "./sidepanel/StartupSection"

interface Props {
  onGoHome: () => void
  onGoConversation?: () => void
}

function Section({
  label,
  open,
  onToggle,
  children,
}: {
  label: string
  open: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div className="border-b border-[#1a1a1a]">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-6 py-2.5 text-left hover:bg-[#111] transition-colors cursor-pointer select-none"
      >
        <span className="text-[10px] text-[#444] font-mono">{open ? "▼" : "▶"}</span>
        <span className="text-[11px] font-mono text-[#888]">{label}</span>
      </button>
      {open && <div className="px-6 pb-4 pt-1">{children}</div>}
    </div>
  )
}

export function AgentPage({ onGoHome, onGoConversation }: Props) {
  // Section open states
  const [beliefsOpen, setBeliefsOpen] = useState(true)
  const [dreamingOpen, setDreamingOpen] = useState(true)
  const [daemonsOpen, setDaemonsOpen] = useState(true)
  const [skillsOpen, setSkillsOpen] = useState(false)

  // Data
  const [beliefs, setBeliefs] = useState<BeliefsResponse | null>(null)
  const [beliefsError, setBeliefsError] = useState<string | null>(null)

  const [daemon, setDaemon] = useState<DaemonStatusResponse | null>(null)
  const [daemonError, setDaemonError] = useState<string | null>(null)

  const [scheduler, setScheduler] = useState<SchedulerStatusResponse | null>(null)
  const [schedulerError, setSchedulerError] = useState<string | null>(null)

  const [dbSkillsData, setDbSkillsData] = useState<DbSkillsResponse | null>(null)
  const [dbSkillsError, setDbSkillsError] = useState<string | null>(null)
  const [expandedSkill, setExpandedSkill] = useState<string | null>(null)
  const [skillContent, setSkillContent] = useState<Record<string, string>>({})
  const [loadingSkillContent, setLoadingSkillContent] = useState<string | null>(null)

  // Fetch beliefs (no conversation context needed for global view)
  const fetchBeliefs = useCallback(async () => {
    try {
      const res = await getBeliefs(null as any)
      setBeliefs(res)
      setBeliefsError(null)
    } catch (e: any) {
      setBeliefsError(e.message || "Failed to fetch beliefs")
    }
  }, [])

  const fetchDaemon = useCallback(async () => {
    try {
      const res = await getDaemonStatus()
      setDaemon(res)
      setDaemonError(null)
    } catch (e: any) {
      setDaemonError(e.message || "Failed")
    }
  }, [])

  const fetchScheduler = useCallback(async () => {
    try {
      const res = await getSchedulerStatus()
      setScheduler(res)
      setSchedulerError(null)
    } catch (e: any) {
      setSchedulerError(e.message || "Failed")
    }
  }, [])

  // Poll daemon + scheduler every 10s
  useEffect(() => {
    fetchDaemon()
    fetchScheduler()
    fetchBeliefs()
    const id = setInterval(() => {
      fetchDaemon()
      fetchScheduler()
    }, 10000)
    return () => clearInterval(id)
  }, [])

  // Load skills on open
  useEffect(() => {
    if (skillsOpen && !dbSkillsData && !dbSkillsError) {
      getDbSkills()
        .then(data => {
          setDbSkillsData({
            always_active: data?.always_active || [],
            on_demand: data?.on_demand || [],
            all: data?.all || [...(data?.always_active || []), ...(data?.on_demand || [])],
          })
        })
        .catch(e => setDbSkillsError(e.message || String(e)))
    }
  }, [skillsOpen])

  const handleLoadSkillContent = async (skillName: string) => {
    if (expandedSkill === skillName) { setExpandedSkill(null); return }
    if (skillContent[skillName]) { setExpandedSkill(skillName); return }
    setLoadingSkillContent(skillName)
    try {
      const result = await getSkillContent(skillName)
      const text = result.content || result.description || `(no content — lifecycle: ${result.lifecycle_stage || "?"})`
      setSkillContent(prev => ({ ...prev, [skillName]: text }))
      setExpandedSkill(skillName)
    } catch (e: any) {
      setSkillContent(prev => ({ ...prev, [skillName]: `Failed: ${e.message}` }))
      setExpandedSkill(skillName)
    } finally {
      setLoadingSkillContent(null)
    }
  }

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-[#1a1a1a] shrink-0">
        <span className="text-[11px] text-[#444] tracking-widest uppercase select-none">
          <span className="text-[#a892ee]">■</span>
          <span className="ml-2">symbia</span>
          <span className="text-[#333] mx-2">//</span>
          <span>agent</span>
        </span>
        <div className="flex items-center gap-4">
          <button
            onClick={onGoHome}
            className="text-[11px] text-[#444] hover:text-[#888] transition-colors cursor-pointer select-none"
          >
            [home]
          </button>
          {onGoConversation && (
            <button
              onClick={onGoConversation}
              className="text-[11px] text-[#444] hover:text-[#888] transition-colors cursor-pointer select-none"
            >
              [back to chat]
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <Section label="Beliefs" open={beliefsOpen} onToggle={() => setBeliefsOpen(p => !p)}>
          <BeliefsSection data={beliefs} error={beliefsError} />
        </Section>

        <Section label="Dreaming" open={dreamingOpen} onToggle={() => setDreamingOpen(p => !p)}>
          <DreamingSection status={daemon} error={daemonError} />
        </Section>

        <Section label="Daemons" open={daemonsOpen} onToggle={() => setDaemonsOpen(p => !p)}>
          <StartupSection status={scheduler} error={schedulerError} />
        </Section>

        <Section label={`Skills${dbSkillsData ? ` (${dbSkillsData.all.length})` : ""}`} open={skillsOpen} onToggle={() => setSkillsOpen(p => !p)}>
          {dbSkillsError ? (
            <p className="text-[10px] text-[#ef4444]">Error: {dbSkillsError}</p>
          ) : !dbSkillsData ? (
            <p className="text-[10px] text-[#555] animate-pulse">loading skills...</p>
          ) : (
            <>
              {dbSkillsData.always_active.length > 0 && (
                <div className="mb-3">
                  <p className="text-[9px] text-[#555] uppercase tracking-wider mb-2">Baseline Dispositions</p>
                  {dbSkillsData.always_active.map((s: any) => (
                    <div key={s.id} className="mb-1">
                      <div
                        className="flex items-center gap-2 cursor-pointer hover:bg-[#111] px-1 py-0.5 transition-colors"
                        onClick={() => handleLoadSkillContent(s.name)}
                      >
                        <span className="text-[9px] text-[#a78bfa]">◆</span>
                        <span className="text-[10px] text-[#bbb]">{s.name}</span>
                        <span className="text-[8px] text-[#444] ml-auto">
                          {loadingSkillContent === s.name ? "..." : expandedSkill === s.name ? "▲" : "▼"}
                        </span>
                      </div>
                      {expandedSkill === s.name && skillContent[s.name] && (
                        <div className="ml-4 mt-1 p-2 bg-[#0a0a0a] border border-[#1a1a1a] text-[10px] text-[#888] whitespace-pre-wrap max-h-48 overflow-y-auto">
                          {skillContent[s.name]}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {dbSkillsData.on_demand.length > 0 && (
                <div>
                  <p className="text-[9px] text-[#555] uppercase tracking-wider mb-2">On-Demand Capabilities</p>
                  {dbSkillsData.on_demand.map((s) => (
                    <div key={s.id} className="mb-1">
                      <div
                        className="flex items-center gap-2 cursor-pointer hover:bg-[#111] px-1 py-0.5 transition-colors"
                        onClick={() => handleLoadSkillContent(s.name)}
                      >
                        <span className="text-[9px] text-[#4ade80]">◇</span>
                        <span className="text-[10px] text-[#bbb] flex-1">{s.name}</span>
                        <span className="text-[9px] text-[#444]">c:{s.confidence.toFixed(1)} m:{s.ontological_mass.toFixed(1)}</span>
                        <span className="text-[8px] text-[#444]">
                          {loadingSkillContent === s.name ? "..." : expandedSkill === s.name ? "▲" : "▼"}
                        </span>
                      </div>
                      {expandedSkill === s.name && skillContent[s.name] && (
                        <div className="ml-4 mt-1 p-2 bg-[#0a0a0a] border border-[#1a1a1a] text-[10px] text-[#888] whitespace-pre-wrap max-h-48 overflow-y-auto">
                          {skillContent[s.name]}
                        </div>
                      )}
                      {expandedSkill === s.name && s.vector_16d?.length > 0 && (
                        <div className="ml-4 mt-1 flex items-end gap-0.5 h-4">
                          {(s.vector_16d as number[]).map((val: number, idx: number) => {
                            const h = Math.min(100, Math.max(10, Math.round(((val + 1) / 2) * 100)))
                            return (
                              <div
                                key={idx}
                                style={{ height: `${h}%` }}
                                title={`Dim ${idx + 1}: ${val.toFixed(4)}`}
                                className="w-1 bg-[#a78bfa]/50 hover:bg-[#a78bfa]"
                              />
                            )
                          })}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </Section>
      </div>
    </div>
  )
}
