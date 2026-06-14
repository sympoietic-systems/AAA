import { useState, useEffect, useRef, memo, useMemo } from "react"
import { getPipeline } from "../../../api/client"
import type { SkillInfo } from "../../../api/client"
import { CollapsibleSection } from "./shared/CollapsibleSection"

/* ── Category config ── */
const CATEGORIES = [
  { key: "perception", label: "Perception", color: "#38bdf8" },
  { key: "memory", label: "Memory", color: "#f59e0b" },
  { key: "reasoning", label: "Reasoning", color: "#a78bfa" },
  { key: "action", label: "Action", color: "#f43f5e" },
]

function getCatColor(cat: string) {
  return CATEGORIES.find(c => c.key === cat?.toLowerCase())?.color ?? "#94a3b8"
}

/* ── List item ── */
const ModuleListItem = memo(function ModuleListItem({ module, isSelected }: { module: SkillInfo; isSelected: boolean }) {
  const catColor = getCatColor(module.category)
  return (
    <div data-module-name={module.name} data-selected={isSelected ? "true" : undefined}
      className={`flex items-center gap-1.5 px-1.5 py-1 cursor-pointer border-l-2 transition-colors select-none ${isSelected ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"}`}>
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${module.status ? "bg-[#4ade80]" : "bg-[#ef4444]"}`} />
      <span className="font-mono text-[11px] truncate flex-1 min-w-0 text-[#bbb]">{module.name}</span>
      <span className="text-[9px] font-mono font-bold shrink-0" style={{ color: catColor }}>{module.category}</span>
    </div>
  )
})

/* ── Submodule ── */
const SubmoduleItem = memo(function SubmoduleItem({ sub }: { sub: SkillInfo }) {
  return (
    <div className="text-[10px]">
      <div className="flex items-center gap-1.5">
        <span className="text-[#a78bfa] font-bold">↳</span>
        <span className="text-[#ccc] font-bold font-mono">{sub.name}</span>
        <span className="text-[9px] text-[#555] font-mono">{sub.category}</span>
      </div>
      <p className="text-[#777] leading-relaxed font-serif mt-0.5 ml-4">{sub.description}</p>
    </div>
  )
})

/* ── Main ── */
export const PipelineSection = memo(function PipelineSection() {
  const [pipeline, setPipeline] = useState<SkillInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedName, setSelectedName] = useState<string | null>(null)
  const detailRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getPipeline().then(data => {
      setPipeline(data.pipeline || [])
      if (data.pipeline?.length > 0) setSelectedName(data.pipeline[0].name)
      setLoading(false)
    }).catch(err => { setError(err.message || String(err)); setLoading(false) })
  }, [])

  useEffect(() => {
    if (!selectedName || !detailRef.current) return
    if (window.matchMedia("(max-width: 767px)").matches) {
      detailRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }, [selectedName])

  const grouped = useMemo(() => {
    const map: Record<string, SkillInfo[]> = {}
    for (const cat of CATEGORIES) map[cat.key] = []
    for (const m of pipeline) {
      const key = m.category?.toLowerCase() ?? "other"
      if (!map[key]) map[key] = []
      map[key].push(m)
    }
    return map
  }, [pipeline])

  if (loading) return <div className="text-[#555] font-mono animate-pulse">loading pipeline...</div>
  if (error) return <div className="text-[#ef4444] font-mono">Error: {error}</div>

  const selectedModule = pipeline.find(m => m.name === selectedName) || null

  const handleListClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-module-name]") as HTMLElement | null
    if (!el) return; const name = el.getAttribute("data-module-name")
    if (name) setSelectedName(name)
  }

  return (
    <div className="flex flex-col md:flex-row gap-3 md:h-[calc(100vh-240px)] px-4 py-2">
      <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0">
        <div className="flex-1 space-y-0.5 overflow-y-auto pr-1 select-none" onClick={handleListClick}>
          {CATEGORIES.map(cat => {
            const items = grouped[cat.key] || []
            if (items.length === 0) return null
            return (
              <CollapsibleSection key={cat.key} label={cat.label} count={items.length} icon="●" iconColor={cat.color}>
                {items.map(m => <ModuleListItem key={m.name} module={m} isSelected={selectedName === m.name} />)}
              </CollapsibleSection>
            )
          })}
        </div>
      </div>

      <div ref={detailRef} className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0">
        {selectedModule ? (
          <div className="flex-1 min-h-0 flex flex-col overflow-y-auto pr-1.5 gap-3 text-[11px]">
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${selectedModule.status ? "bg-[#4ade80]" : "bg-[#ef4444]"}`} />
              <span className="font-mono font-bold text-[#ccc] truncate">{selectedModule.name}</span>
            </div>

            <div>
              <div className="text-[#555] font-mono text-[10px] uppercase">[ Description ]</div>
              <div className="text-[#ccc] leading-relaxed font-serif mt-0.5">{selectedModule.description}</div>
            </div>

            <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-[10px] font-mono text-[#888]">
              <span><span className="text-[#444]">Category:</span> <span style={{ color: getCatColor(selectedModule.category) }} className="uppercase">{selectedModule.category}</span></span>
              <span><span className="text-[#444]">Cost Pool:</span> <span className="text-[#aaa] uppercase">{selectedModule.cost}</span></span>
              <span><span className="text-[#444]">Status:</span> <span className={selectedModule.status ? "text-[#4ade80]" : "text-[#ef4444]"}>{selectedModule.status ? "online" : "offline"}</span></span>
            </div>

            {selectedModule.triggers?.length > 0 && (
              <div>
                <div className="text-[#555] font-mono text-[10px] uppercase">[ Activation Triggers ]</div>
                <div className="text-[10px] text-[#888] mt-0.5">{selectedModule.triggers.join(", ")}</div>
              </div>
            )}

            <div className="flex-1 min-h-0 flex flex-col">
              <div className="text-[#555] font-mono text-[10px] uppercase shrink-0">
                [ Submodules ({selectedModule.children?.length ?? 0}) ]
              </div>
              {selectedModule.children?.length > 0 ? (
                <div className="flex-1 min-h-0 overflow-y-auto mt-1 space-y-1.5">
                  {selectedModule.children.map(sub => <SubmoduleItem key={sub.name} sub={sub} />)}
                </div>
              ) : (
                <span className="text-[#444] italic mt-0.5">No submodules registered</span>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 min-h-0 flex items-center justify-center">
            <span className="text-[#444] italic font-mono">select a module to inspect</span>
          </div>
        )}
      </div>
    </div>
  )
})
