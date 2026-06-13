import { useState, useEffect, useRef, memo } from "react"
import {
  getDbSkills,
  getSkillContent,
  getAgent
} from "../../../api/client"
import type { DbSkillsResponse, DbSkillInfo } from "../../../api/client"
import { SkillListItem } from "./skills/SkillListItem"
import { SkillDetail } from "./skills/SkillDetail"
import { NewSkillForm } from "./skills/NewSkillForm"

export const SkillsSection = memo(SkillsSectionComponent)

interface SkillsSectionProps {
  initialSelectedId?: string
}

function SkillsSectionComponent({ initialSelectedId }: SkillsSectionProps) {
  const [data, setData] = useState<DbSkillsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [agentFlux, setAgentFlux] = useState<boolean>(false)

  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [skillContent, setSkillContent] = useState<Record<string, string>>({})
  const [loadingContent, setLoadingContent] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const detailRef = useRef<HTMLDivElement>(null)

  // Fetch skills and agent info on mount
  useEffect(() => {
    getDbSkills()
      .then(d => setData({
        always_active: d?.always_active || [],
        on_demand: d?.on_demand || [],
        collapsed: d?.collapsed || [],
        proposed: d?.proposed || [],
        all: d?.all || [...(d?.always_active || []), ...(d?.on_demand || []), ...(d?.collapsed || []), ...(d?.proposed || [])],
      }))
      .catch(e => setError(e.message || String(e)))

    getAgent()
      .then(info => setAgentFlux(!!info.agent_flux))
      .catch(() => setAgentFlux(false))
  }, [])

  // Scroll to detail on mobile when a skill is selected
  useEffect(() => {
    if ((!selectedName && !isAdding) || !detailRef.current) return
    if (window.matchMedia("(max-width: 767px)").matches) {
      detailRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }, [selectedName, isAdding])

  // Load skill content on demand
  const handleLoadContent = async (name: string) => {
    if (skillContent[name]) return
    setLoadingContent(name)
    try {
      const result = await getSkillContent(name)
      const text = result.content || result.description || `(no content — lifecycle: ${result.lifecycle_stage || "?"})`
      setSkillContent(prev => ({ ...prev, [name]: text }))
    } catch (e: any) {
      setSkillContent(prev => ({ ...prev, [name]: `Failed: ${e.message}` }))
    } finally {
      setLoadingContent(null)
    }
  }

  // Auto-select skill when initialSelectedId changes or data is loaded
  useEffect(() => {
    if (initialSelectedId && data?.all) {
      const matched = data.all.find(s => s.id === initialSelectedId || s.name === initialSelectedId)
      if (matched) {
        setSelectedName(matched.name)
        handleLoadContent(matched.name)
      }
    }
  }, [initialSelectedId, data])

  const handleUpdate = (updatedSkill: DbSkillInfo, updatedContent: string) => {
    setData(prev => {
      if (!prev) return null
      const updateList = (list: DbSkillInfo[]) =>
        list.map(s => s.id === updatedSkill.id ? updatedSkill : s)
      return {
        always_active: updateList(prev.always_active),
        on_demand: updateList(prev.on_demand),
        collapsed: updateList(prev.collapsed || []),
        proposed: updateList(prev.proposed || []),
        all: updateList(prev.all),
      }
    })
    if (selectedName) {
      setSkillContent(prev => ({ ...prev, [selectedName]: updatedContent }))
    }
  }

  const handleCreateSuccess = (newSkill: DbSkillInfo) => {
    setData(prev => {
      if (!prev) return null
      const always_active = newSkill.always_active
        ? [...prev.always_active, newSkill]
        : prev.always_active
      const on_demand = !newSkill.always_active
        ? [...prev.on_demand, newSkill]
        : prev.on_demand
      const all = [...prev.all, newSkill]
      return { always_active, on_demand, all }
    })
    setIsAdding(false)
    setSelectedName(newSkill.name)
    handleLoadContent(newSkill.name)
  }

  const handleDeleteSuccess = (skillId: string) => {
    setData(prev => {
      if (!prev) return null
      return {
        always_active: prev.always_active.filter(s => s.id !== skillId),
        on_demand: prev.on_demand.filter(s => s.id !== skillId),
        collapsed: (prev.collapsed || []).filter(s => s.id !== skillId),
        proposed: (prev.proposed || []).filter(s => s.id !== skillId),
        all: prev.all.filter(s => s.id !== skillId),
      }
    })
    setSelectedName(null)
  }

  if (error && !data) return <p className="text-[11px] text-[#ef4444] font-mono">{error}</p>
  if (!data) return <p className="text-[11px] text-[#555] font-mono animate-pulse">loading skills...</p>

  const { always_active, on_demand, collapsed = [], proposed = [] } = data
  const allSkills = [...always_active, ...on_demand, ...collapsed, ...proposed]
  const selected = allSkills.find(s => s.name === selectedName) || null

  // Event delegation for list clicks
  const handleListClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-skill-name]") as HTMLElement | null
    if (!el) return
    const name = el.getAttribute("data-skill-name")
    if (name) {
      setIsAdding(false)
      setSelectedName(prev => prev === name ? null : name)
      handleLoadContent(name)
    }
  }

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2 flex flex-col md:flex-row gap-3 md:h-[calc(100vh-300px)]">
      {/* ── Left: Skill list ── */}
      <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0">
        {agentFlux && (
          <button
            onClick={() => {
              setSelectedName(null)
              setIsAdding(true)
            }}
            className="w-full mb-2.5 py-1 px-3 border border-[#a78bfa]/20 hover:border-[#a78bfa]/40 bg-[#a78bfa]/5 hover:bg-[#a78bfa]/10 text-[#a78bfa] text-[10px] font-mono transition-all text-center cursor-pointer select-none uppercase tracking-wider rounded"
          >
            + add new skill
          </button>
        )}
        <div
          onClick={handleListClick}
          className="flex-1 space-y-0.5 overflow-y-auto pr-1 select-none"
        >
          {always_active.length > 0 && (
            <div>
              <div className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider pb-0.5">
                Baseline Dispositions ({always_active.length})
              </div>
              {always_active.map(s => (
                <SkillListItem key={s.id} s={s} isSelected={!isAdding && selectedName === s.name} isBaseline />
              ))}
            </div>
          )}
          {on_demand.length > 0 && (
            <div className={always_active.length > 0 ? "mt-2.5" : ""}>
              <div className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider pb-0.5">
                On-Demand Capabilities ({on_demand.length})
              </div>
              {on_demand.map(s => (
                <SkillListItem key={s.id} s={s} isSelected={!isAdding && selectedName === s.name} isBaseline={false} />
              ))}
            </div>
          )}
          {proposed.length > 0 && (
            <div className="mt-2.5">
              <div className="text-[#a78bfa] font-mono text-[9px] uppercase tracking-wider pb-0.5">
                Proposed Nucleations ({proposed.length})
              </div>
              {proposed.map(s => (
                <SkillListItem key={s.id} s={s} isSelected={!isAdding && selectedName === s.name} isBaseline={false} />
              ))}
            </div>
          )}
          {collapsed.length > 0 && (
            <div className="mt-2.5">
              <div className="text-[#ef4444] font-mono text-[9px] uppercase tracking-wider pb-0.5">
                Refused / Integrated Proposals ({collapsed.length})
              </div>
              {collapsed.map(s => (
                <SkillListItem key={s.id} s={s} isSelected={!isAdding && selectedName === s.name} isBaseline={false} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Right: Detail panel ── */}
      <div ref={detailRef} className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0">
        {isAdding ? (
          <NewSkillForm
            onCancel={() => setIsAdding(false)}
            onCreate={handleCreateSuccess}
          />
        ) : (
          <SkillDetail
            skill={selected}
            content={selectedName ? skillContent[selectedName] : undefined}
            loading={loadingContent === selectedName}
            onUpdate={handleUpdate}
            onDelete={handleDeleteSuccess}
            agentFlux={agentFlux}
          />
        )}
      </div>
    </div>
  )
}
