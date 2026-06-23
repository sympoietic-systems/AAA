import { useState } from "react"
import { createSkill } from "../../../../api/client"
import type { DbSkillInfo } from "../../../../api/client"

interface NewSkillFormProps {
  onCancel: () => void
  onCreate: (newSkill: DbSkillInfo) => void
}

export function NewSkillForm({ onCancel, onCreate }: NewSkillFormProps) {
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
          <span className="text-[10px] shrink-0 text-semantic-purple">◆</span>
          <span className="font-mono text-[11px] font-bold text-[#ccc] truncate">CREATE NEW SKILL</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="text-[10px] text-action-dim hover:text-action-hover disabled:text-[#555] transition-colors cursor-pointer select-none"
          >
            {isSaving ? "[saving...]" : "[save]"}
          </button>
          <button
            onClick={onCancel}
            disabled={isSaving}
            className="text-[10px] text-action-dim hover:text-semantic-red disabled:text-[#555] transition-colors cursor-pointer select-none"
          >
            [cancel]
          </button>
        </div>
      </div>

      {saveError && (
        <div className="text-[10px] text-semantic-red bg-semantic-red/10 border border-semantic-red/20 p-1.5 rounded shrink-0">
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
            className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] px-2 py-1.5 rounded text-[11px] font-mono w-full focus:outline-none focus:border-action-hover/50"
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
                className="accent-semantic-purple cursor-pointer"
              />
              On-Demand Capability
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer text-[#bbb]">
              <input
                type="radio"
                checked={alwaysActive}
                onChange={() => setAlwaysActive(true)}
                disabled={isSaving}
                className="accent-semantic-purple cursor-pointer"
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
            className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] p-2 rounded text-[11px] font-serif leading-relaxed w-full focus:outline-none focus:border-action-hover/50 min-h-[50px] resize-y"
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
              className="bg-[#08080c] border border-[#1a1a24] text-[#ccc] px-2 py-1.5 rounded text-[11px] font-mono w-full focus:outline-none focus:border-action-hover/50"
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
            className="flex-1 bg-[#08080c] border border-[#1a1a24] text-[#ccc] p-2 rounded text-[11px] font-mono leading-relaxed w-full focus:outline-none focus:border-action-hover/50 resize-none overflow-y-auto"
          />
        </div>
      </div>
    </div>
  )
}
