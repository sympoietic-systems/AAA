import { useState, useEffect, useRef, memo } from "react"
import { getPipeline } from "../../../api/client"
import type { SkillInfo } from "../../../api/client"

// ─── Pipeline Module List Item ─────────────────────────────────────────

interface ModuleListItemProps {
  module: SkillInfo
  isSelected: boolean
}

function ModuleListItem({ module, isSelected }: ModuleListItemProps) {
  const getCategoryColor = (cat: string) => {
    switch (cat.toLowerCase()) {
      case "perception": return "text-[#38bdf8] border-[#38bdf8]/30"
      case "memory": return "text-[#f59e0b] border-[#f59e0b]/30"
      case "reasoning": return "text-[#a78bfa] border-[#a78bfa]/30"
      case "action": return "text-[#f43f5e] border-[#f43f5e]/30"
      default: return "text-[#94a3b8] border-[#94a3b8]/30"
    }
  }

  return (
    <div
      data-module-name={module.name}
      data-selected={isSelected ? "true" : undefined}
      className={`
        flex items-center gap-1.5 px-1.5 py-1.5 cursor-pointer
        border-l-2 transition-colors select-none
        ${isSelected ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"}
      `}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${module.status ? "bg-[#4ade80]" : "bg-[#ef4444]"}`} />
      <span className="font-mono text-[11px] truncate flex-1 min-w-0 text-[#bbb]">{module.name}</span>
      <span className={`text-[8px] uppercase font-mono px-1 py-px rounded shrink-0 bg-black/40 border ${getCategoryColor(module.category)}`}>
        {module.category}
      </span>
    </div>
  )
}

// ─── Submodule / Child Component ──────────────────────────────────────────

interface SubmoduleItemProps {
  sub: SkillInfo
}

function SubmoduleItem({ sub }: SubmoduleItemProps) {
  return (
    <div className="flex gap-2.5 p-2 rounded bg-black/30 border border-[#1a1a24]/60 text-[10px] font-mono">
      <span className="text-[#a78bfa] font-bold">↳</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[#eee] font-bold">{sub.name}</span>
          <span className="text-[7px] uppercase px-1 py-px rounded bg-[#111] text-[#555] border border-[#222]">
            {sub.category}
          </span>
        </div>
        <p className="text-[#777] text-[10px] leading-relaxed font-serif mt-0.5">
          {sub.description}
        </p>
      </div>
    </div>
  )
}

// ─── Main Component ────────────────────────────────────────────────────────

export const PipelineSection = memo(PipelineSectionComponent)

function PipelineSectionComponent() {
  const [pipeline, setPipeline] = useState<SkillInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedName, setSelectedName] = useState<string | null>(null)
  const detailRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getPipeline()
      .then(data => {
        setPipeline(data.pipeline || [])
        if (data.pipeline && data.pipeline.length > 0) {
          setSelectedName(data.pipeline[0].name)
        }
        setLoading(false)
      })
      .catch(err => {
        setError(err.message || String(err))
        setLoading(false)
      })
  }, [])

  // Scroll to detail on mobile when a module is selected
  useEffect(() => {
    if (!selectedName || !detailRef.current) return
    if (window.matchMedia("(max-width: 767px)").matches) {
      detailRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }, [selectedName])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="text-[11px] text-[#555] font-mono animate-pulse">interrogating pipeline registry...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-3 border border-[#ef4444]/20 bg-[#ef4444]/5 text-[#ef4444] font-mono text-[11px] rounded">
        Error: {error}
      </div>
    )
  }

  const selectedModule = pipeline.find(m => m.name === selectedName) || null

  const handleListClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-module-name]") as HTMLElement | null
    if (!el) return
    const name = el.getAttribute("data-module-name")
    if (name) {
      setSelectedName(name)
    }
  }

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2 flex flex-col md:flex-row gap-3 md:h-[calc(100vh-300px)]">
      {/* ── Left: Module list ── */}
      <div className="md:w-[38%] shrink-0 w-full flex flex-col min-h-0">
        <div className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider pb-1 shrink-0">
          Pipeline Sequence ({pipeline.length})
        </div>
        <div
          onClick={handleListClick}
          className="flex-1 space-y-0.5 overflow-y-auto pr-1 select-none"
        >
          {pipeline.map(m => (
            <ModuleListItem
              key={m.name}
              module={m}
              isSelected={selectedName === m.name}
            />
          ))}
        </div>
      </div>

      {/* ── Right: Detail panel ── */}
      <div ref={detailRef} className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0">
        {selectedModule ? (
          <div className="flex-1 min-h-0 flex flex-col border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50 p-2.5 gap-2.5 text-[11px] font-sans">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[#1f1f2e]/30 pb-1.5 shrink-0">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${selectedModule.status ? "bg-[#4ade80]" : "bg-[#ef4444]"}`} />
                <span className="font-mono text-[11px] font-bold text-[#ccc] truncate">{selectedModule.name}</span>
              </div>
              <span className="text-[9px] uppercase font-mono px-1.5 py-px rounded border border-[#a78bfa]/40 text-[#a78bfa] bg-[#a78bfa]/10">
                {selectedModule.always_run ? "always-run" : "conditional"}
              </span>
            </div>

            {/* Description */}
            <div className="shrink-0">
              <div className="text-[#555] font-mono text-[10px] uppercase">[ Description ]</div>
              <div className="text-[#ccc] text-[11px] font-serif leading-relaxed mt-0.5">
                {selectedModule.description}
              </div>
            </div>

            {/* Metadata Grid */}
            <div className="shrink-0 grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] font-mono text-[#888]">
              <div>
                <span className="text-[#444]">Category:</span> <span className="text-[#aaa] uppercase">{selectedModule.category}</span>
              </div>
              <div>
                <span className="text-[#444]">Execution Mode:</span> <span className="text-[#aaa]">Pipeline Sequential</span>
              </div>
              <div>
                <span className="text-[#444]">Cost Pool:</span> <span className="text-[#aaa] uppercase">{selectedModule.cost}</span>
              </div>
              <div>
                <span className="text-[#444]">Status:</span> <span className={selectedModule.status ? "text-[#4ade80]" : "text-[#ef4444]"}>{selectedModule.status ? "ONLINE" : "OFFLINE"}</span>
              </div>
            </div>

            {/* Triggers */}
            {selectedModule.triggers && selectedModule.triggers.length > 0 && (
              <div className="shrink-0">
                <div className="text-[#555] font-mono text-[10px] uppercase mb-1">[ Activation Triggers ]</div>
                <div className="flex flex-wrap gap-1">
                  {selectedModule.triggers.map(kw => (
                    <span key={kw} className="text-[9px] font-mono bg-[#141414] text-[#888] border border-[#222] px-1.5 py-0.5 rounded">
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Submodules / Children — takes remaining height, scrolls internally */}
            <div className="flex-1 min-h-0 flex flex-col">
              <div className="text-[#555] font-mono text-[10px] uppercase shrink-0">
                [ Submodules & Internal Abstractions ({selectedModule.children ? selectedModule.children.length : 0}) ]
              </div>
              {selectedModule.children && selectedModule.children.length > 0 ? (
                <div className="flex-1 min-h-0 overflow-y-auto mt-1 space-y-1.5">
                  {selectedModule.children.map(sub => (
                    <SubmoduleItem key={sub.name} sub={sub} />
                  ))}
                </div>
              ) : (
                <span className="text-[10px] text-[#444] italic mt-0.5">No submodules registered</span>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 min-h-0 flex items-center justify-center border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50">
            <span className="text-[11px] text-[#444] italic font-mono">select a module to inspect</span>
          </div>
        )}
      </div>
    </div>
  )
}
