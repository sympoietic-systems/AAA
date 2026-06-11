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
import { BeliefsSection } from "./agentpage/BeliefsSection"
import { DreamingSection } from "./agentpage/DreamingSection"
import { StartupSection } from "./agentpage/StartupSection"

type TabId = "beliefs" | "dreaming" | "daemons" | "skills"

const TABS: { id: TabId; label: string; count?: number }[] = [
  { id: "beliefs", label: "Beliefs" },
  { id: "dreaming", label: "Dreaming" },
  { id: "daemons", label: "Daemons" },
  { id: "skills", label: "Skills" },
]

interface Props {
  onGoHome: () => void
  onGoConversation?: () => void
}

export function AgentPage({ onGoHome, onGoConversation }: Props) {
  const [activeTab, setActiveTab] = useState<TabId>("beliefs")

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

  const fetchSkills = useCallback(async () => {
    if (dbSkillsData || dbSkillsError) return
    try {
      const data = await getDbSkills()
      setDbSkillsData({
        always_active: data?.always_active || [],
        on_demand: data?.on_demand || [],
        all: data?.all || [...(data?.always_active || []), ...(data?.on_demand || [])],
      })
    } catch (e: any) {
      setDbSkillsError(e.message || String(e))
    }
  }, [dbSkillsData, dbSkillsError])

  // Fetch all data on mount, poll daemon + scheduler every 10s
  useEffect(() => {
    fetchDaemon()
    fetchScheduler()
    fetchBeliefs()
    fetchSkills()
    const id = setInterval(() => {
      fetchDaemon()
      fetchScheduler()
    }, 10000)
    return () => clearInterval(id)
  }, [])

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

  // Update skills count in tabs
  const tabs = TABS.map((t) =>
    t.id === "skills" && dbSkillsData ? { ...t, count: dbSkillsData.all.length } : t
  )

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

      {/* Tab bar */}
      <div className="flex border-b border-[#2d2d3d] gap-1 px-4 py-1.5 shrink-0 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-2.5 py-0.5 text-[11px] rounded font-bold tracking-wide uppercase transition-all duration-200 border whitespace-nowrap cursor-pointer select-none ${
              activeTab === tab.id
                ? "bg-[#1e1e2e] text-[#94a3b8] border-[#475569]/40"
                : "text-[#94a3b8]/40 border-transparent hover:text-[#94a3b8]/70 hover:bg-[#111]"
            }`}
          >
            {tab.label}
            {tab.count != null ? ` (${tab.count})` : ""}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {activeTab === "beliefs" && <BeliefsSection data={beliefs} error={beliefsError} />}

        {activeTab === "dreaming" && <DreamingSection status={daemon} error={daemonError} />}

        {activeTab === "daemons" && <StartupSection status={scheduler} error={schedulerError} />}

        {activeTab === "skills" && (
          <>
            {dbSkillsError ? (
              <p className="text-[11px] text-[#ef4444]">Error: {dbSkillsError}</p>
            ) : !dbSkillsData ? (
              <p className="text-[11px] text-[#555] animate-pulse">loading skills...</p>
            ) : (
              <>
                {dbSkillsData.always_active.length > 0 && (
                  <div className="mb-3">
                    <p className="text-[10px] text-[#555] uppercase tracking-wider mb-2">Baseline Dispositions</p>
                    {dbSkillsData.always_active.map((s: any) => (
                      <div key={s.id} className="mb-1">
                        <div
                          className="flex items-center gap-2 cursor-pointer hover:bg-[#111] px-1 py-0.5 transition-colors"
                          onClick={() => handleLoadSkillContent(s.name)}
                        >
                          <span className="text-[10px] text-[#a78bfa]">◆</span>
                          <span className="text-[11px] text-[#bbb]">{s.name}</span>
                          <span className="text-[9px] text-[#444] ml-auto">
                            {loadingSkillContent === s.name ? "..." : expandedSkill === s.name ? "▲" : "▼"}
                          </span>
                        </div>
                        {expandedSkill === s.name && skillContent[s.name] && (
                          <div className="ml-4 mt-1 p-2 bg-[#0a0a0a] border border-[#1a1a1a] text-[11px] text-[#888] whitespace-pre-wrap max-h-48 overflow-y-auto">
                            {skillContent[s.name]}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {dbSkillsData.on_demand.length > 0 && (
                  <div>
                    <p className="text-[10px] text-[#555] uppercase tracking-wider mb-2">On-Demand Capabilities</p>
                    {dbSkillsData.on_demand.map((s) => (
                      <div key={s.id} className="mb-1">
                        <div
                          className="flex items-center gap-2 cursor-pointer hover:bg-[#111] px-1 py-0.5 transition-colors"
                          onClick={() => handleLoadSkillContent(s.name)}
                        >
                          <span className="text-[10px] text-[#4ade80]">◇</span>
                          <span className="text-[11px] text-[#bbb] flex-1">{s.name}</span>
                          <span className="text-[10px] text-[#444]">c:{s.confidence.toFixed(1)} m:{s.ontological_mass.toFixed(1)}</span>
                          <span className="text-[9px] text-[#444]">
                            {loadingSkillContent === s.name ? "..." : expandedSkill === s.name ? "▲" : "▼"}
                          </span>
                        </div>
                        {expandedSkill === s.name && skillContent[s.name] && (
                          <div className="ml-4 mt-1 p-2 bg-[#0a0a0a] border border-[#1a1a1a] text-[11px] text-[#888] whitespace-pre-wrap max-h-48 overflow-y-auto">
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
          </>
        )}
      </div>
    </div>
  )
}
