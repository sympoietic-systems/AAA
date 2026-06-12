import { useState, useEffect, useRef, memo } from "react"
import {
  getDbSkills,
  getSkillContent,
  updateSkill,
  getAgent,
  createSkill,
  deleteSkill
} from "../../../api/client"
import type { DbSkillsResponse, DbSkillInfo } from "../../../api/client"

// ─── Skill List Item ─────────────────────────────────────

interface SkillListItemProps {
  s: DbSkillInfo
  isSelected: boolean
  isBaseline: boolean
}

function SkillListItem({ s, isSelected, isBaseline }: SkillListItemProps) {
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

interface SkillDetailProps {
  skill: DbSkillInfo | null
  content?: string
  loading: boolean
  onUpdate: (updatedSkill: DbSkillInfo, updatedContent: string) => void
  onDelete: (skillId: string) => void
  agentFlux: boolean
}

function SkillDetail({ skill, content, loading, onUpdate, onDelete, agentFlux }: SkillDetailProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editDescription, setEditDescription] = useState("")
  const [editContent, setEditContent] = useState("")
  const [editTriggers, setEditTriggers] = useState("")
  
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false)
  const [isSavingOrDeleting, setIsSavingOrDeleting] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Reset editing/confirming states when selected skill changes
  useEffect(() => {
    setIsEditing(false)
    setIsConfirmingDelete(false)
    setErrorMsg(null)
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
          <span className="font-mono text-[11px] font-bold text-[#ccc] truncate">{skill.name}</span>
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

// ─── New Skill Form ──────────────────────────────────────

interface NewSkillFormProps {
  onCancel: () => void
  onCreate: (newSkill: DbSkillInfo) => void
}

function NewSkillForm({ onCancel, onCreate }: NewSkillFormProps) {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [content, setContent] = useState("")
  const [alwaysActive, setAlwaysActive] = useState(false)
  const [triggers, setTriggers] = useState("")
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const handleSave = async () => {
    if (!name.trim()) {
      setSaveError("Name is required")
      return
    }
    // Simple validation: lowercase alphanumeric and hyphens/underscores
    if (!/^[a-z0-9-_]+$/.test(name.trim())) {
      setSaveError("Name must contain only lowercase letters, numbers, hyphens, and underscores")
      return
    }
    if (!description.trim()) {
      setSaveError("Description is required")
      return
    }
    setIsSaving(true)
    setSaveError(null)
    try {
      const triggerList = alwaysActive
        ? []
        : triggers
            .split(",")
            .map(t => t.trim())
            .filter(t => t.length > 0)

      const result = await createSkill({
        name: name.trim(),
        description: description.trim(),
        content: content.trim() || undefined,
        always_active: alwaysActive,
        trigger_keywords: triggerList,
      })

      onCreate(result)
    } catch (e: any) {
      setSaveError(e.message || String(e))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50 p-2.5 gap-2.5 text-[11px] font-mono">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1f1f2e]/30 pb-1.5 shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[10px] shrink-0 text-[#a78bfa]">◆</span>
          <span className="font-mono text-[11px] font-bold text-[#ccc] truncate">CREATE NEW SKILL</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="text-[10px] text-[#4ade80] hover:text-[#4ade80]/80 disabled:text-[#555] transition-colors cursor-pointer select-none"
          >
            {isSaving ? "[saving...]" : "[save]"}
          </button>
          <button
            onClick={onCancel}
            disabled={isSaving}
            className="text-[10px] text-[#ef4444] hover:text-[#ef4444]/80 disabled:text-[#555] transition-colors cursor-pointer select-none"
          >
            [cancel]
          </button>
        </div>
      </div>

      {saveError && (
        <div className="text-[10px] text-[#ef4444] bg-[#ef4444]/10 border border-[#ef4444]/20 p-1.5 rounded shrink-0">
          {saveError}
        </div>
      )}

      {/* Form fields */}
      <div className="flex-1 flex flex-col gap-2.5 min-h-0 overflow-y-auto pr-1">
        {/* Name */}
        <div className="shrink-0 flex flex-col gap-1">
          <label className="text-[#555] text-[10px] uppercase font-bold">[ Skill Name ]</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={isSaving}
            placeholder="e.g. system-attunement"
            className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] px-2 py-1.5 rounded text-[11px] font-mono w-full focus:outline-none focus:border-[#a78bfa]/50"
          />
        </div>

        {/* Type / Always Active */}
        <div className="shrink-0 flex flex-col gap-1">
          <label className="text-[#555] text-[10px] uppercase font-bold">[ Activation Mode ]</label>
          <div className="flex gap-4 mt-0.5">
            <label className="flex items-center gap-1.5 cursor-pointer text-[#bbb]">
              <input
                type="radio"
                checked={!alwaysActive}
                onChange={() => setAlwaysActive(false)}
                disabled={isSaving}
                className="accent-[#a78bfa] cursor-pointer"
              />
              On-Demand Capability
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer text-[#bbb]">
              <input
                type="radio"
                checked={alwaysActive}
                onChange={() => setAlwaysActive(true)}
                disabled={isSaving}
                className="accent-[#a78bfa] cursor-pointer"
              />
              Baseline Disposition (Always Active)
            </label>
          </div>
        </div>

        {/* Description */}
        <div className="shrink-0 flex flex-col gap-1">
          <label className="text-[#555] text-[10px] uppercase font-bold">[ Short Description ]</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isSaving}
            placeholder="Brief explanation of when the skill is relevant."
            className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] p-2 rounded text-[11px] font-serif leading-relaxed w-full focus:outline-none focus:border-[#a78bfa]/50 min-h-[50px] resize-y"
          />
        </div>

        {/* Trigger keywords */}
        {!alwaysActive && (
          <div className="shrink-0 flex flex-col gap-1">
            <label className="text-[#555] text-[10px] uppercase font-bold">[ Triggers (comma-separated) ]</label>
            <input
              type="text"
              value={triggers}
              onChange={(e) => setTriggers(e.target.value)}
              disabled={isSaving}
              placeholder="e.g. system state, diagnostics, attunement"
              className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] px-2 py-1.5 rounded text-[11px] font-mono w-full focus:outline-none focus:border-[#a78bfa]/50"
            />
          </div>
        )}

        {/* Full Content */}
        <div className="flex-1 flex flex-col gap-1 min-h-[120px]">
          <label className="text-[#555] text-[10px] uppercase font-bold">[ Full Instructions / Content (Optional) ]</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            disabled={isSaving}
            placeholder="Detailed markdown content. If left empty, a default template will be generated."
            className="flex-1 bg-[#08080c] border border-[#1a1a24] text-[#ccc] p-2 rounded text-[11px] font-mono leading-relaxed w-full focus:outline-none focus:border-[#a78bfa]/50 resize-none overflow-y-auto"
          />
        </div>
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────

export const SkillsSection = memo(SkillsSectionComponent)

function SkillsSectionComponent() {
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
        all: d?.all || [...(d?.always_active || []), ...(d?.on_demand || [])],
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

  const handleUpdate = (updatedSkill: DbSkillInfo, updatedContent: string) => {
    setData(prev => {
      if (!prev) return null
      const updateList = (list: DbSkillInfo[]) =>
        list.map(s => s.id === updatedSkill.id ? updatedSkill : s)
      return {
        always_active: updateList(prev.always_active),
        on_demand: updateList(prev.on_demand),
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
        all: prev.all.filter(s => s.id !== skillId),
      }
    })
    setSelectedName(null)
  }

  if (error && !data) return <p className="text-[11px] text-[#ef4444] font-mono">{error}</p>
  if (!data) return <p className="text-[11px] text-[#555] font-mono animate-pulse">loading skills...</p>

  const { always_active, on_demand } = data
  const allSkills = [...always_active, ...on_demand]
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
      <div className="md:w-[38%] shrink-0 w-full flex flex-col min-h-0">
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
