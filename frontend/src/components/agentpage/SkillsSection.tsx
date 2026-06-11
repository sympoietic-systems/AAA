import { useState, useEffect, useRef, memo } from "react"
import { getDbSkills, getSkillContent } from "../../api/client"
import type { DbSkillsResponse, DbSkillInfo } from "../../api/client"

// ─── Skill List Item ─────────────────────────────────────

function SkillListItem({ s, isSelected, isBaseline }: { s: DbSkillInfo; isSelected: boolean; isBaseline: boolean }) {
  return (
    <div
      data-skill-name={s.name}
      data-selected={isSelected ? "true" : undefined}
      className={`
        flex items-center gap-1.5 px-1.5 py-1 cursor-pointer
        border-l-2 transition-colors
        ${isSelected ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"}
      `}
    >
      <span className={`text-[10px] shrink-0 ${isBaseline ? "text-[#a78bfa]" : "text-[#4ade80]"}`}>
        {isBaseline ? "◆" : "◇"}
      </span>
      <span className="font-mono text-[11px] truncate flex-1 min-w-0 text-[#bbb]">{s.name}</span>
      <span className="text-[8px] font-mono text-[#555] shrink-0 hidden md:inline">
        m:{s.ontological_mass.toFixed(1)}
      </span>
      <span className="text-[10px] font-mono font-bold text-[#777] shrink-0">
        {(s.confidence * 100).toFixed(0)}%
      </span>
    </div>
  )
}

// ─── Skill Detail Panel ──────────────────────────────────

function SkillDetail({
  skill, content, loading,
}: { skill: DbSkillInfo | null; content?: string; loading: boolean }) {
  if (!skill) {
    return (
      <div className="flex-1 min-h-0 flex items-center justify-center border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50">
        <span className="text-[11px] text-[#444] italic font-mono">select a skill to inspect</span>
      </div>
    )
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50 p-2.5 gap-2.5 text-[11px] font-sans">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1f1f2e]/30 pb-1.5 shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[10px] shrink-0 text-[#a78bfa]">◆</span>
          <span className="font-mono text-[11px] font-bold text-[#ccc] truncate">{skill.name}</span>
        </div>
        <span className="text-[9px] uppercase font-mono px-1.5 py-px rounded border border-[#a78bfa]/40 text-[#a78bfa] bg-[#a78bfa]/10 shrink-0 ml-2">
          {skill.always_active ? "baseline" : "on-demand"}
        </span>
      </div>

      {/* Description */}
      <div className="shrink-0">
        <div className="text-[#555] font-mono text-[10px] uppercase">[ Description ]</div>
        <div className="text-[#ccc] text-[11px] font-serif leading-relaxed mt-0.5">
          {skill.description}
        </div>
      </div>

      {/* Metadata */}
      <div className="shrink-0 grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] font-mono text-[#888]">
        <div><span className="text-[#444]">Source:</span> <span className="text-[#aaa]">{skill.source}</span></div>
        <div><span className="text-[#444]">Stage:</span> <span className="text-[#aaa]">{skill.lifecycle_stage}</span></div>
        <div><span className="text-[#444]">Mass:</span> <span className="text-[#aaa]">{skill.ontological_mass.toFixed(1)}</span></div>
        <div><span className="text-[#444]">Confidence:</span> <span className="text-[#aaa] font-bold">{(skill.confidence * 100).toFixed(0)}%</span></div>
      </div>

      {/* Keywords */}
      {skill.trigger_keywords.length > 0 && (
        <div className="shrink-0">
          <div className="text-[#555] font-mono text-[10px] uppercase mb-1">[ Triggers ]</div>
          <div className="flex flex-wrap gap-1">
            {skill.trigger_keywords.map((kw) => (
              <span key={kw} className="text-[9px] font-mono bg-[#141414] text-[#888] border border-[#222] px-1.5 py-0.5 rounded">
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Vector */}
      {skill.vector_16d?.length > 0 && (
        <div className="shrink-0">
          <div className="text-[#555] font-mono text-[10px] uppercase mb-1">[ 16D Autopoietic Vector ]</div>
          <div className="flex items-end gap-0.5 h-4 bg-[#08080c] border border-[#1a1a24] p-0.5 rounded w-fit max-w-full overflow-x-auto">
            {skill.vector_16d.map((val, idx) => {
              const hp = Math.min(100, Math.max(10, Math.round(((val + 1) / 2) * 100)))
              return (
                <div key={idx} style={{ height: `${hp}%`, minWidth: 4 }} title={`D${idx + 1}: ${val.toFixed(4)}`}
                  className="w-1 bg-[#a78bfa]/50 hover:bg-[#a78bfa] shrink-0"
                />
              )
            })}
          </div>
        </div>
      )}

      {/* Content — takes remaining height, scrolls internally */}
      <div className="flex-1 min-h-0 flex flex-col">
        <div className="text-[#555] font-mono text-[10px] uppercase shrink-0">[ Full Content ]</div>
        {loading ? (
          <div className="text-[10px] text-[#555] animate-pulse mt-0.5">loading...</div>
        ) : content ? (
          <div className="flex-1 min-h-0 overflow-y-auto mt-1 text-[10px] text-[#888] whitespace-pre-wrap leading-relaxed">
            {content}
          </div>
        ) : (
          <div className="text-[10px] text-[#444] italic mt-0.5">Click a skill to load its content</div>
        )}
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────

export const SkillsSection = memo(SkillsSectionComponent)

function SkillsSectionComponent() {
  const [data, setData] = useState<DbSkillsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [skillContent, setSkillContent] = useState<Record<string, string>>({})
  const [loadingContent, setLoadingContent] = useState<string | null>(null)
  const detailRef = useRef<HTMLDivElement>(null)

  // Fetch skills on mount
  useEffect(() => {
    getDbSkills()
      .then(d => setData({
        always_active: d?.always_active || [],
        on_demand: d?.on_demand || [],
        all: d?.all || [...(d?.always_active || []), ...(d?.on_demand || [])],
      }))
      .catch(e => setError(e.message || String(e)))
  }, [])

  // Scroll to detail on mobile when a skill is selected
  useEffect(() => {
    if (!selectedName || !detailRef.current) return
    if (window.matchMedia("(max-width: 767px)").matches) {
      detailRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }, [selectedName])

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

  if (error && !data) return <p className="text-[11px] text-[#ef4444] font-mono">{error}</p>
  if (!data) return <p className="text-[11px] text-[#555] font-mono animate-pulse">loading skills...</p>

  const { always_active, on_demand } = data
  const allSkills = [...always_active, ...on_demand]
  const selected = allSkills.find(s => s.name === selectedName) || null

  // Event delegation
  const handleListClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-skill-name]") as HTMLElement | null
    if (!el) return
    const name = el.getAttribute("data-skill-name")
    if (name) {
      setSelectedName(prev => prev === name ? null : name)
      handleLoadContent(name)
    }
  }

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2 flex flex-col md:flex-row gap-3 md:h-[calc(100vh-300px)]">
      {/* ── Left: Skill list ── */}
      <div
        onClick={handleListClick}
        className="md:w-[38%] shrink-0 w-full space-y-0.5 overflow-y-auto pr-1 select-none"
      >
        {always_active.length > 0 && (
          <div>
            <div className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider pb-0.5">
              Baseline Dispositions ({always_active.length})
            </div>
            {always_active.map(s => (
              <SkillListItem key={s.id} s={s} isSelected={selectedName === s.name} isBaseline />
            ))}
          </div>
        )}
        {on_demand.length > 0 && (
          <div className={always_active.length > 0 ? "mt-2" : ""}>
            <div className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider pb-0.5">
              On-Demand Capabilities ({on_demand.length})
            </div>
            {on_demand.map(s => (
              <SkillListItem key={s.id} s={s} isSelected={selectedName === s.name} isBaseline={false} />
            ))}
          </div>
        )}
      </div>

      {/* ── Right: Detail panel ── */}
      <div ref={detailRef} className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0">
        <SkillDetail
          skill={selected}
          content={selectedName ? skillContent[selectedName] : undefined}
          loading={loadingContent === selectedName}
        />
      </div>
    </div>
  )
}
