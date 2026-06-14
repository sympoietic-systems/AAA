import { useState, useEffect, memo } from "react"
import { updateSkill, deleteSkill } from "../../../../api/client"
import type { DbSkillInfo } from "../../../../api/client"
import { computeLineDiff } from "../../../../utils/diff"
import { StructuralAutopoieticGlyph } from "../../../UI/StructuralAutopoieticGlyph"
import { TerminalTabs } from "../../../UI"

type DetailTab = "details" | "version"

/* ── Shared version item ── */

function VersionItem({
  version, source, timestamp, changelog,
  isCurrent, agentFlux, isExpanded, hasDiff,
  onToggleDiff, onRevert, isReverting, children,
}: {
  version: number; source?: string; timestamp: string; changelog: string
  isCurrent: boolean; agentFlux: boolean; isExpanded: boolean; hasDiff: boolean
  onToggleDiff: () => void; onRevert?: () => void; isReverting?: boolean
  children?: React.ReactNode
}) {
  const sourceLabel = source === "auto_metabolism" ? "auto" : (source === "agent" || source === "emergent") ? "agent" : "user"

  return (
    <div className="flex flex-col gap-1 text-[10px] font-mono">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[#a78bfa] font-bold">v{version}</span>
            {source && <span className={`text-[8px] uppercase font-bold`}>{sourceLabel}</span>}
            <span className="text-[#555] text-[9px]">{timestamp}</span>
          </div>
          <div className="text-[#aaa] text-[9px] mt-0.5 truncate" title={changelog}>
            {changelog}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {agentFlux && !isCurrent && onRevert && (
            <button onClick={onRevert} disabled={isReverting}
              className="text-[9px] text-[#a78bfa] hover:text-[#c084fc] hover:underline disabled:text-[#555] cursor-pointer select-none font-bold">
              {isReverting ? "[reverting...]" : "[revert]"}
            </button>
          )}
          {hasDiff && (
            <button onClick={onToggleDiff}
              className="text-[9px] text-[#888] hover:text-[#ccc] hover:underline cursor-pointer select-none font-bold">
              {isExpanded ? "[collapse]" : "[diff]"}
            </button>
          )}
        </div>
      </div>
      {isExpanded && children}
    </div>
  )
}

/* ── Main Component ── */

interface SkillDetailProps {
  skill: DbSkillInfo | null
  content?: string
  loading: boolean
  onUpdate: (updatedSkill: DbSkillInfo, updatedContent: string) => void
  onDelete: (skillId: string) => void
  agentFlux: boolean
}

export const SkillDetail = memo(function SkillDetail({ skill, content, loading, onUpdate, onDelete, agentFlux }: SkillDetailProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editDescription, setEditDescription] = useState("")
  const [editContent, setEditContent] = useState("")
  const [editTriggers, setEditTriggers] = useState("")
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false)
  const [isSavingOrDeleting, setIsSavingOrDeleting] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const [versions, setVersions] = useState<any[]>([])
  const [revertingVersion, setRevertingVersion] = useState<number | null>(null)
  const [expandedVersions, setExpandedVersions] = useState<Record<number, boolean>>({})
  const [activeTab, setActiveTab] = useState<DetailTab>("details")

  useEffect(() => {
    setIsEditing(false); setIsConfirmingDelete(false); setErrorMsg(null); setExpandedVersions({})
    if (!skill) { setVersions([]); return }
    setVersions([]); setActiveTab("details")
    fetch(`/api/skills/${skill.id}/versions`)
      .then(res => res.json()).then(data => { if (data?.versions) setVersions(data.versions) })
      .catch(e => console.error("Failed to load versions:", e))
  }, [skill])

  if (!skill) {
    return (
      <div className="flex-1 min-h-0 flex items-center justify-center">
        <span className="text-[11px] text-[#444] italic font-mono">select a skill to inspect</span>
      </div>
    )
  }

  /* ── Handlers (after null guard, before JSX) ── */
  const handleStartEdit = () => {
    setEditDescription(skill.description); setEditContent(content || "")
    setEditTriggers(skill.trigger_keywords.join(", ")); setIsEditing(true)
    setIsConfirmingDelete(false); setErrorMsg(null)
  }

  const handleSave = async () => {
    setIsSavingOrDeleting(true); setErrorMsg(null)
    try {
      const triggers = editTriggers.split(",").map(t => t.trim()).filter(t => t.length > 0)
      const updated = await updateSkill(skill.id, { description: editDescription, content: editContent, trigger_keywords: triggers })
      onUpdate(updated, editContent); setIsEditing(false)
    } catch (e: any) { setErrorMsg(e.message || String(e)) }
    finally { setIsSavingOrDeleting(false) }
  }

  const handleDelete = async () => {
    setIsSavingOrDeleting(true); setErrorMsg(null)
    try { await deleteSkill(skill.id); onDelete(skill.id) }
    catch (e: any) { setErrorMsg(e.message || String(e)); setIsSavingOrDeleting(false); setIsConfirmingDelete(false) }
  }

  /* ── Edit mode ── */
  if (isEditing) {
    return (
      <div className="flex-1 min-h-0 flex flex-col gap-3 text-[11px] font-mono">
        <div className="flex items-center justify-between">
          <span className="text-[#ccc] font-bold">editing: {skill.name}</span>
          <div className="flex gap-2">
            <button onClick={handleSave} disabled={isSavingOrDeleting}
              className="text-[10px] text-[#666] hover:text-[#4ade80] disabled:text-[#555] transition-colors cursor-pointer select-none">[save]</button>
            <button onClick={() => setIsEditing(false)} disabled={isSavingOrDeleting}
              className="text-[10px] text-[#666] hover:text-[#ef4444] disabled:text-[#555] transition-colors cursor-pointer select-none">[cancel]</button>
          </div>
        </div>
        {errorMsg && <div className="text-[#ef4444]">{errorMsg}</div>}
        <div className="flex-1 flex flex-col gap-3 min-h-0 overflow-y-auto pr-1">
          <div className="flex flex-col gap-1">
            <span className="text-[#555] text-[10px] uppercase font-bold">[ Short Description ]</span>
            <textarea value={editDescription} onChange={e => setEditDescription(e.target.value)} disabled={isSavingOrDeleting}
              className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] p-2 rounded text-[11px] font-serif leading-relaxed w-full focus:outline-none focus:border-[#a78bfa]/50 min-h-[50px] resize-y" />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-[#555] text-[10px] uppercase font-bold">[ Triggers (comma-separated) ]</span>
            <input type="text" value={editTriggers} onChange={e => setEditTriggers(e.target.value)} disabled={isSavingOrDeleting}
              placeholder="e.g. skill workshop, create skill"
              className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] px-2 py-1.5 rounded text-[11px] font-mono w-full focus:outline-none focus:border-[#a78bfa]/50" />
          </div>
          <div className="flex-1 flex flex-col gap-1 min-h-[150px]">
            <span className="text-[#555] text-[10px] uppercase font-bold">[ Full Content ]</span>
            <textarea value={editContent} onChange={e => setEditContent(e.target.value)} disabled={isSavingOrDeleting}
              className="flex-1 bg-[#08080c] border border-[#1a1a24] text-[#ccc] p-2 rounded text-[11px] font-mono leading-relaxed w-full focus:outline-none focus:border-[#a78bfa]/50 resize-none overflow-y-auto" />
          </div>
        </div>
      </div>
    )
  }

  const revertSkill = async (targetVersion: number) => {
    if (revertingVersion) return; setRevertingVersion(targetVersion)
    try {
      const res = await fetch(`/api/skills/${skill.id}/revert/${targetVersion}`, { method: "POST" })
      if (!res.ok) { const err = await res.json(); alert(err.detail || "Revert failed") }
      else {
        const updated = await res.json(); onUpdate(updated, updated.content)
        const vRes = await fetch(`/api/skills/${skill.id}/versions`); const vData = await vRes.json()
        if (vData?.versions) setVersions(vData.versions)
      }
    } catch (e) { alert(String(e)) }
    finally { setRevertingVersion(null) }
  }

  const sortedVersions = [...versions].sort((a, b) => b.version - a.version)

  return (
    <div className="flex-1 min-h-0 flex flex-col overflow-y-auto pr-1.5 gap-3 text-[11px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[10px] shrink-0 text-[#a78bfa]">◆</span>
          <span className="font-mono font-bold text-[#ccc] truncate">
            {skill.name} <span className="text-[#888] font-normal text-[9px]">v{skill.version}</span>
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          {agentFlux && (
            <>
              {isConfirmingDelete ? (
                <span className="flex items-center gap-1.5 font-mono text-[10px]">
                  <span className="text-[#ef4444] animate-pulse">confirm delete?</span>
                  <button onClick={handleDelete} disabled={isSavingOrDeleting} className="text-[#666] hover:text-[#ef4444] hover:underline cursor-pointer select-none">[yes]</button>
                  <button onClick={() => setIsConfirmingDelete(false)} disabled={isSavingOrDeleting} className="text-[#666] hover:text-[#888] hover:underline cursor-pointer select-none">[no]</button>
                </span>
              ) : (
                <button onClick={() => setIsConfirmingDelete(true)} disabled={isSavingOrDeleting} className="text-[10px] text-[#666] hover:text-[#f87171] font-mono transition-colors cursor-pointer select-none">[delete]</button>
              )}
              <button onClick={handleStartEdit} disabled={isSavingOrDeleting} className="text-[10px] text-[#666] hover:text-[#c084fc] font-mono transition-colors cursor-pointer select-none">[edit]</button>
            </>
          )}
          <span className="text-[9px] font-mono font-bold text-[#a78bfa]">{skill.always_active ? "baseline" : "on-demand"}</span>
        </div>
      </div>

      {errorMsg && <div className="text-[#ef4444]">{errorMsg}</div>}

      {/* Tab bar: Details • Version */}
      {versions.length > 0 && (
        <TerminalTabs
          tabs={[
            { key: "details", label: "Details" },
            { key: "version", label: "Version History", badge: versions.length },
          ]}
          active={activeTab}
          onChange={(key) => setActiveTab(key as DetailTab)}
        />
      )}

      {/* Details tab */}
      {activeTab === "details" && (
        <>
          <div>
            <div className="text-[#555] font-mono text-[10px] uppercase">[ Description ]</div>
            <div className="text-[#ccc] text-[11px] font-serif leading-relaxed mt-0.5">{skill.description}</div>
          </div>
          {skill.lifecycle_stage === "collapsed" && skill.refusal_reason && (
            <div>
              <div className={`font-mono text-[9px] uppercase font-bold tracking-wider ${skill.changelog?.startsWith("Merged") ? "text-[#a78bfa]/60" : "text-[#ef4444]/60"}`}>
                {skill.changelog?.startsWith("Merged") ? "[ Integration Rationale ]" : "[ Refusal Rationale ]"}
              </div>
              <div className={`leading-relaxed text-[10.5px] mt-0.5 ${skill.changelog?.startsWith("Merged") ? "text-[#a78bfa]/90" : "text-[#ef4444]/90"}`}>
                {skill.refusal_reason}
              </div>
            </div>
          )}
          <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-[10px] font-mono text-[#888]">
            <span><span className="text-[#444]">Source:</span> <span className="text-[#aaa]">{skill.source}</span></span>
            <span><span className="text-[#444]">Stage:</span> <span className="text-[#aaa]">{skill.lifecycle_stage}</span></span>
            <span><span className="text-[#444]">Mass:</span> <span className="text-[#aaa]">{skill.ontological_mass.toFixed(2)}</span></span>
            <span><span className="text-[#444]">Confidence:</span> <span className="text-[#aaa] font-bold">{(skill.confidence * 100).toFixed(0)}%</span></span>
          </div>
          {skill.trigger_keywords.length > 0 && (
            <div>
              <div className="text-[#555] font-mono text-[10px] uppercase">[ Triggers ]</div>
              <div className="text-[10px] text-[#888] mt-0.5">
                {skill.trigger_keywords.join(", ")}
              </div>
            </div>
          )}
          {skill.vector_16d?.length > 0 && (
            <div>
              <div className="text-[#555] font-mono text-[10px] uppercase">[ 16D Autopoietic Signature ]</div>
              <StructuralAutopoieticGlyph signature={skill.vector_16d} isStagnant={false} />
            </div>
          )}
          <div>
            <div className="text-[#555] font-mono text-[10px] uppercase">[ Full Content ]</div>
            {loading ? (
              <div className="text-[#555] animate-pulse mt-0.5">loading...</div>
            ) : content ? (
              <div className="mt-1 text-[10px] text-[#888] whitespace-pre-wrap leading-relaxed">{content}</div>
            ) : (
              <div className="text-[#444] italic mt-0.5">Click a skill to load its content</div>
            )}
          </div>
        </>
      )}

      {/* Version tab */}
      {activeTab === "version" && versions.length > 0 && (
        <div className="font-mono text-[10px]">
          <div className="text-[#555] uppercase font-bold">[ Version Diff History ]</div>
          <div className="space-y-1 max-h-[220px] overflow-y-auto pr-1 mt-1">
            {sortedVersions.map((v, vIdx) => {
              const prev = vIdx < sortedVersions.length - 1 ? sortedVersions[vIdx + 1] : null
              const isExpanded = !!expandedVersions[v.version]
              const prevDesc = prev ? prev.description : ""
              const prevContent = prev ? prev.content : ""
              const prevTriggers: string[] = prev ? prev.trigger_keywords : []
              const descDiff = isExpanded ? computeLineDiff(prevDesc, v.description) : []
              const contentDiff = isExpanded ? computeLineDiff(prevContent, v.content) : []
              const addedTriggers = isExpanded ? v.trigger_keywords.filter((t: string) => !prevTriggers.includes(t)) : []
              const removedTriggers = isExpanded ? prevTriggers.filter((t: string) => !v.trigger_keywords.includes(t)) : []
              const hasDescDiff = prevDesc !== v.description
              const hasContentDiff = prevContent !== v.content
              const hasTriggersDiff = addedTriggers.length > 0 || removedTriggers.length > 0
              const hasAnyDiff = hasDescDiff || hasContentDiff || hasTriggersDiff

              return (
                <VersionItem
                  key={v.version} version={v.version} source={v.source}
                  timestamp={v.created_at ? new Date(v.created_at).toLocaleString() : ""}
                  changelog={v.changelog || "No changelog"}
                  isCurrent={v.version === skill.version} agentFlux={agentFlux}
                  isExpanded={isExpanded} hasDiff={hasAnyDiff}
                  onToggleDiff={() => setExpandedVersions(prevMap => ({ ...prevMap, [v.version]: !prevMap[v.version] }))}
                  onRevert={v.version !== skill.version ? () => revertSkill(v.version) : undefined}
                  isReverting={revertingVersion !== null}
                >
                  {isExpanded && hasAnyDiff && (
                    <div className="mt-1 pt-1.5 space-y-2 text-[9px]">
                      {hasDescDiff && (
                        <div>
                          <div className="text-[#555] uppercase font-bold tracking-wider mb-0.5">[ Description Diff ]</div>
                          <div className="leading-relaxed text-[10px] font-sans">
                            {descDiff.map((line: any, lIdx: number) => (
                              <div key={lIdx} className={line.type === 'added' ? 'text-[#4ade80] px-1' : line.type === 'removed' ? 'text-[#ef4444] line-through px-1' : 'text-[#888] px-1'}>
                                {line.type === 'added' ? '+ ' : line.type === 'removed' ? '- ' : '  '}{line.value}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {hasTriggersDiff && (
                        <div>
                          <div className="text-[#555] uppercase font-bold tracking-wider mb-0.5">[ Triggers Diff ]</div>
                          <div className="flex flex-wrap gap-1">
                            {removedTriggers.map((t: string) => (
                              <span key={t} className="text-[9px] font-mono text-[#ef4444] line-through px-1.5 py-0.5">-{t}</span>
                            ))}
                            {addedTriggers.map((t: string) => (
                              <span key={t} className="text-[9px] font-mono text-[#4ade80] px-1.5 py-0.5">+{t}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      {hasContentDiff && (
                        <div>
                          <div className="text-[#555] uppercase font-bold tracking-wider mb-0.5">[ Content Diff ]</div>
                          <div className="font-mono text-[9px] overflow-x-auto whitespace-pre max-h-[120px] overflow-y-auto leading-normal">
                            {contentDiff.map((line: any, lIdx: number) => (
                              <div key={lIdx} className={line.type === 'added' ? 'text-[#4ade80] px-1' : line.type === 'removed' ? 'text-[#ef4444] px-1' : 'text-[#666] px-1'}>
                                {line.type === 'added' ? '+ ' : line.type === 'removed' ? '- ' : '  '}{line.value}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  {isExpanded && !hasAnyDiff && <div className="text-[#555] italic text-[9px]">No differences.</div>}
                </VersionItem>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
});
