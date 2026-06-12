import { useState, useEffect } from "react"
import { updateSkill, deleteSkill } from "../../../../api/client"
import type { DbSkillInfo } from "../../../../api/client"
import { computeLineDiff } from "../../../../utils/diff"

interface SkillDetailProps {
  skill: DbSkillInfo | null
  content?: string
  loading: boolean
  onUpdate: (updatedSkill: DbSkillInfo, updatedContent: string) => void
  onDelete: (skillId: string) => void
  agentFlux: boolean
}

export function SkillDetail({ skill, content, loading, onUpdate, onDelete, agentFlux }: SkillDetailProps) {
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

  // Reset editing/confirming states and fetch versions when selected skill changes
  useEffect(() => {
    setIsEditing(false)
    setIsConfirmingDelete(false)
    setErrorMsg(null)
    setExpandedVersions({})

    if (!skill) {
      setVersions([])
      return
    }

    setVersions([])
    fetch(`/api/skills/${skill.id}/versions`)
      .then(res => res.json())
      .then(data => {
        if (data && data.versions) {
          setVersions(data.versions)
        }
      })
      .catch(e => console.error("Failed to load versions:", e))
  }, [skill])

  if (!skill) {
    return (
      <div className="flex-1 min-h-0 flex items-center justify-center border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50">
        <span className="text-[11px] text-[#444] italic font-mono">select a skill to inspect</span>
      </div>
    )
  }

  const handleStartEdit = () => {
    setEditDescription(skill.description)
    setEditContent(content || "")
    setEditTriggers(skill.trigger_keywords.join(", "))
    setIsEditing(true)
    setIsConfirmingDelete(false)
    setErrorMsg(null)
  }

  const handleSave = async () => {
    setIsSavingOrDeleting(true)
    setErrorMsg(null)
    try {
      const triggers = editTriggers
        .split(",")
        .map(t => t.trim())
        .filter(t => t.length > 0)
      
      const updated = await updateSkill(skill.id, {
        description: editDescription,
        content: editContent,
        trigger_keywords: triggers,
      })
      
      onUpdate(updated, editContent)
      setIsEditing(false)
    } catch (e: any) {
      setErrorMsg(e.message || String(e))
    } finally {
      setIsSavingOrDeleting(false)
    }
  }

  const handleDelete = async () => {
    setIsSavingOrDeleting(true)
    setErrorMsg(null)
    try {
      await deleteSkill(skill.id)
      onDelete(skill.id)
    } catch (e: any) {
      setErrorMsg(e.message || String(e))
      setIsSavingOrDeleting(false)
      setIsConfirmingDelete(false)
    }
  }

  if (isEditing) {
    return (
      <div className="flex-1 min-h-0 flex flex-col border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50 p-2.5 gap-2.5 text-[11px] font-mono">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#1f1f2e]/30 pb-1.5 shrink-0">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-[10px] shrink-0 text-[#a78bfa]">◆</span>
            <span className="font-mono text-[11px] font-bold text-[#ccc] truncate">editing: {skill.name}</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={isSavingOrDeleting}
              className="text-[10px] text-[#4ade80] hover:text-[#4ade80]/80 disabled:text-[#555] transition-colors cursor-pointer select-none"
            >
              {isSavingOrDeleting ? "[saving...]" : "[save]"}
            </button>
            <button
              onClick={() => setIsEditing(false)}
              disabled={isSavingOrDeleting}
              className="text-[10px] text-[#ef4444] hover:text-[#ef4444]/80 disabled:text-[#555] transition-colors cursor-pointer select-none"
            >
              [cancel]
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="text-[10px] text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/20 p-1.5 rounded shrink-0">
            {errorMsg}
          </div>
        )}

        {/* Form fields */}
        <div className="flex-1 flex flex-col gap-2.5 min-h-0 overflow-y-auto pr-1">
          {/* Description */}
          <div className="shrink-0 flex flex-col gap-1">
            <label className="text-[#555] text-[10px] uppercase font-bold">[ Short Description ]</label>
            <textarea
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              disabled={isSavingOrDeleting}
              className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] p-2 rounded text-[11px] font-serif leading-relaxed w-full focus:outline-none focus:border-[#a78bfa]/50 min-h-[50px] resize-y"
            />
          </div>

          {/* Trigger keywords */}
          <div className="shrink-0 flex flex-col gap-1">
            <label className="text-[#555] text-[10px] uppercase font-bold">[ Triggers (comma-separated) ]</label>
            <input
              type="text"
              value={editTriggers}
              onChange={(e) => setEditTriggers(e.target.value)}
              disabled={isSavingOrDeleting}
              placeholder="e.g. skill workshop, create skill"
              className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] px-2 py-1.5 rounded text-[11px] font-mono w-full focus:outline-none focus:border-[#a78bfa]/50"
            />
          </div>

          {/* Full Content */}
          <div className="flex-1 flex flex-col gap-1 min-h-[150px]">
            <label className="text-[#555] text-[10px] uppercase font-bold">[ Full Content ]</label>
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              disabled={isSavingOrDeleting}
              className="flex-1 bg-[#08080c] border border-[#1a1a24] text-[#ccc] p-2 rounded text-[11px] font-mono leading-relaxed w-full focus:outline-none focus:border-[#a78bfa]/50 resize-none overflow-y-auto"
            />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50 p-2.5 gap-2.5 text-[11px] font-sans">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1f1f2e]/30 pb-1.5 shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[10px] shrink-0 text-[#a78bfa]">◆</span>
          <span className="font-mono text-[11px] font-bold text-[#ccc] truncate">
            {skill.name} <span className="text-[#888] font-normal text-[9px] ml-1 bg-[#1a1a24] px-1 py-0.5 rounded border border-[#2d2d3a]">v{skill.version}</span>
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          {agentFlux && (
            <>
              {isConfirmingDelete ? (
                <div className="flex items-center gap-1.5 font-mono text-[10px]">
                  <span className="text-[#ef4444] animate-pulse">confirm delete?</span>
                  <button
                    onClick={handleDelete}
                    disabled={isSavingOrDeleting}
                    className="text-[#ef4444] hover:underline cursor-pointer select-none"
                  >
                    [yes]
                  </button>
                  <button
                    onClick={() => setIsConfirmingDelete(false)}
                    disabled={isSavingOrDeleting}
                    className="text-[#888] hover:underline cursor-pointer select-none"
                  >
                    [no]
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setIsConfirmingDelete(true)}
                  disabled={isSavingOrDeleting}
                  className="text-[10px] text-[#ef4444] hover:text-[#f87171] font-mono transition-colors cursor-pointer select-none"
                >
                  [delete]
                </button>
              )}
              <button
                onClick={handleStartEdit}
                disabled={isSavingOrDeleting}
                className="text-[10px] text-[#a78bfa] hover:text-[#c084fc] font-mono transition-colors cursor-pointer select-none"
              >
                [edit]
              </button>
            </>
          )}
          <span className="text-[9px] uppercase font-mono px-1.5 py-px rounded border border-[#a78bfa]/40 text-[#a78bfa] bg-[#a78bfa]/10">
            {skill.always_active ? "baseline" : "on-demand"}
          </span>
        </div>
      </div>

      {errorMsg && (
        <div className="text-[10px] text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/20 p-1.5 rounded shrink-0 font-mono">
          {errorMsg}
        </div>
      )}

      {/* Description */}
      <div className="shrink-0">
        <div className="text-[#555] font-mono text-[10px] uppercase">[ Description ]</div>
        <div className="text-[#ccc] text-[11px] font-serif leading-relaxed mt-0.5">
          {skill.description}
        </div>
      </div>

      {/* Refusal Reason (if collapsed) */}
      {skill.lifecycle_stage === "collapsed" && skill.refusal_reason && (
        <div className={`shrink-0 border p-2 rounded text-[10.5px] leading-relaxed font-serif ${
          skill.changelog?.startsWith("Merged")
            ? "border-[#a78bfa]/20 bg-[#a78bfa]/5 text-[#a78bfa]/90"
            : "border-[#ef4444]/20 bg-[#ef4444]/5 text-[#ef4444]/90"
        }`}>
          <div className={`font-mono text-[9px] uppercase font-bold tracking-wider mb-0.5 ${
            skill.changelog?.startsWith("Merged") ? "text-[#a78bfa]/60" : "text-[#ef4444]/60"
          }`}>
            {skill.changelog?.startsWith("Merged") ? "[ Integration Rationale ]" : "[ Refusal Rationale ]"}
          </div>
          {skill.refusal_reason}
        </div>
      )}

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
      <div className="flex-1 min-h-0 flex flex-col mb-2">
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

      {/* Version History */}
      {versions.length > 0 && (
        <div className="shrink-0 border-t border-[#1f1f2e]/20 pt-2 mt-auto">
          <div className="text-[#555] font-mono text-[10px] uppercase mb-1">[ Version History ]</div>
          <div className="space-y-1 max-h-[180px] overflow-y-auto pr-1">
            {versions.map((v, vIdx) => {
              const prev = vIdx < versions.length - 1 ? versions[vIdx + 1] : null
              const isExpanded = !!expandedVersions[v.version]

              const prevDesc = prev ? prev.description : ""
              const prevContent = prev ? prev.content : ""
              const prevTriggers = prev ? prev.trigger_keywords : []

              const descDiff = isExpanded ? computeLineDiff(prevDesc, v.description) : []
              const contentDiff = isExpanded ? computeLineDiff(prevContent, v.content) : []
              const addedTriggers = isExpanded ? v.trigger_keywords.filter((t: string) => !prevTriggers.includes(t)) : []
              const removedTriggers = isExpanded ? prevTriggers.filter((t: string) => !v.trigger_keywords.includes(t)) : []

              const hasDescDiff = isExpanded && prevDesc !== v.description
              const hasContentDiff = isExpanded && prevContent !== v.content
              const hasTriggersDiff = isExpanded && (addedTriggers.length > 0 || removedTriggers.length > 0)
              const hasAnyDiff = hasDescDiff || hasContentDiff || hasTriggersDiff

              return (
                <div key={v.version} className="flex flex-col gap-1.5 p-1.5 rounded bg-[#07070b]/60 border border-[#1f1f2e]/10 text-[10px] font-mono">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[#a78bfa] font-bold">v{v.version}</span>
                        {v.source && (
                          <span className={`text-[8px] uppercase px-1.5 py-px rounded-sm font-mono border leading-none ${
                            v.source === "auto_metabolism"
                              ? "border-[#c084fc]/35 text-[#c084fc] bg-[#c084fc]/5"
                              : "border-[#444] text-[#888] bg-[#151518]"
                          }`}>
                            {v.source === "auto_metabolism" ? "auto" : "user"}
                          </span>
                        )}
                        <span className="text-[#555] text-[9px]">
                          {v.created_at ? new Date(v.created_at).toLocaleString() : ""}
                        </span>
                      </div>
                      <div className="text-[#aaa] text-[9px] mt-0.5 truncate" title={v.changelog || "No changelog"}>
                        {v.changelog || "No changelog"}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => setExpandedVersions(prevMap => ({ ...prevMap, [v.version]: !prevMap[v.version] }))}
                        className="text-[9px] text-[#888] hover:text-[#ccc] hover:underline cursor-pointer select-none"
                      >
                        {isExpanded ? "[collapse]" : "[diff]"}
                      </button>
                      {agentFlux && v.version !== skill.version && (
                        <button
                          onClick={async () => {
                            if (revertingVersion) return
                            setRevertingVersion(v.version)
                            try {
                              const res = await fetch(`/api/skills/${skill.id}/revert/${v.version}`, { method: "POST" })
                              if (!res.ok) {
                                const err = await res.json()
                                alert(err.detail || "Revert failed")
                              } else {
                                const updated = await res.json()
                                onUpdate(updated, updated.content)
                                // Reload versions
                                const vRes = await fetch(`/api/skills/${skill.id}/versions`)
                                const vData = await vRes.json()
                                if (vData && vData.versions) setVersions(vData.versions)
                              }
                            } catch (e) {
                              alert(String(e))
                            } finally {
                              setRevertingVersion(null)
                            }
                          }}
                          disabled={revertingVersion !== null}
                          className="text-[9px] text-[#a78bfa] hover:text-[#c084fc] hover:underline cursor-pointer disabled:text-[#555]"
                        >
                          {revertingVersion === v.version ? "[reverting...]" : "[revert]"}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Expanded Diff Section */}
                  {isExpanded && (
                    <div className="mt-1 border-t border-[#1f1f2e]/10 pt-1.5 space-y-2 text-[9px]">
                      {/* Description Diff */}
                      {hasDescDiff && (
                        <div>
                          <div className="text-[#555] uppercase font-bold tracking-wider mb-0.5">[ Description Diff ]</div>
                          <div className="bg-[#050508]/90 border border-[#1f1f2e]/10 p-1.5 rounded leading-relaxed text-[10px] font-sans">
                            {descDiff.map((line, lIdx) => (
                              <div
                                key={lIdx}
                                className={
                                  line.type === 'added'
                                    ? 'text-[#4ade80] bg-[#4ade80]/5 px-1'
                                    : line.type === 'removed'
                                      ? 'text-[#ef4444] bg-[#ef4444]/5 line-through px-1'
                                      : 'text-[#888] px-1'
                                }
                              >
                                {line.type === 'added' ? '+ ' : line.type === 'removed' ? '- ' : '  '}
                                {line.value}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Triggers Diff */}
                      {hasTriggersDiff && (
                        <div>
                          <div className="text-[#555] uppercase font-bold tracking-wider mb-0.5">[ Triggers Diff ]</div>
                          <div className="flex flex-wrap gap-1 mt-0.5">
                            {removedTriggers.map((t: string) => (
                              <span key={t} className="text-[9px] font-mono bg-[#ef4444]/10 text-[#ef4444] border border-[#ef4444]/20 px-1.5 py-0.5 rounded line-through">
                                -{t}
                              </span>
                            ))}
                            {addedTriggers.map((t: string) => (
                              <span key={t} className="text-[9px] font-mono bg-[#4ade80]/10 text-[#4ade80] border border-[#4ade80]/20 px-1.5 py-0.5 rounded">
                                +{t}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Content Diff */}
                      {hasContentDiff && (
                        <div>
                          <div className="text-[#555] uppercase font-bold tracking-wider mb-0.5">[ Content Diff ]</div>
                          <div className="bg-[#050508]/90 border border-[#1f1f2e]/10 p-1.5 rounded font-mono text-[9px] overflow-x-auto whitespace-pre max-h-[120px] overflow-y-auto leading-normal">
                            {contentDiff.map((line, lIdx) => (
                              <div
                                key={lIdx}
                                className={
                                  line.type === 'added'
                                    ? 'text-[#4ade80] bg-[#4ade80]/5 px-1'
                                    : line.type === 'removed'
                                      ? 'text-[#ef4444] bg-[#ef4444]/5 px-1'
                                      : 'text-[#666] px-1'
                                }
                              >
                                {line.type === 'added' ? '+ ' : line.type === 'removed' ? '- ' : '  '}
                                {line.value}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {!hasAnyDiff && (
                        <div className="text-[#555] italic">No differences in description, triggers, or content.</div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
