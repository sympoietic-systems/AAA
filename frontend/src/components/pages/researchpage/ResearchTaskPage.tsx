// ResearchTaskPage — single research task detail with tabbed Info, Steps, Report, Notes.
import { memo, useState, useEffect, useRef, useMemo } from "react"
import { HeaderContainer, HeaderIndicator, HeaderLogo, HeaderSeparator, HeaderLabel, HeaderActionButton, CreasesDropdown, UnifiedFooter, TerminalButton } from "../../UI"
import type { ResearchTask, ResearchStep } from "../../../api/research"
import { getResearchTask, getTaskUnifiedNotes, getTaskSteps, type UnifiedNoteInfo } from "../../../api/research"
import { STATUS_COLORS, STEP_LABELS } from "./constants/taskConstants"
import { useTaskPolling } from "./shared/useTaskPolling"
import { InfoTab } from "./tabs/InfoTab"
import { StepsTab } from "./tabs/StepsTab"
import { NewResearchForm } from "./NewResearchForm"
import { NotableMarkdown } from "../../shared/NotableMarkdown"
import type { NoteInfo } from "../../../api/client"
import { copyToClipboard } from "../../../utils/clipboard"
import { COLOR_PALETTE } from "../../../config/colors"

type SubTabId = "info" | "steps" | "report" | "notes"

const SUB_TABS: { key: SubTabId; label: string }[] = [
  { key: "info",     label: "Info" },
  { key: "steps",    label: "Steps" },
  { key: "report",   label: "Report" },
  { key: "notes",    label: "Notes" },
]

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "-").slice(0, 60) || "research-report"
}

function extractReportTitle(markdown: string): string | null {
  const match = markdown.match(/^#{1,2}\s+(.+)$/m)
  return match?.[1]?.trim() ?? null
}

/* ── Shell — header, tab bar, content routing ── */
const TaskPageInner = memo(function TaskPageInner({ task }: { task: ResearchTask }) {
  const { current, orchPhase, refreshAll } = useTaskPolling(task.id, task.status, task)
  const [taskNotes, setTaskNotes] = useState<NoteInfo[]>([])
  const [unifiedNotes, setUnifiedNotes] = useState<UnifiedNoteInfo[]>([])
  const [copied, setCopied] = useState(false)
  const [navigateStepId, setNavigateStepId] = useState<string | null>(null)
  const reportRef = useRef<HTMLDivElement>(null)

  const defaultTab: SubTabId = task.status === "completed" && task.result_summary ? "report" : "info"
  const [tab, setTab] = useState<SubTabId>(defaultTab)

  const [steps, setSteps] = useState<ResearchStep[]>([])
  
  useEffect(() => {
    if (tab === "report") {
      getTaskSteps(task.id)
        .then(res => setSteps(res.steps || []))
        .catch(() => {})
    }
  }, [task.id, tab, current.status, current.result_summary])

  const reportVersions = useMemo(() => {
    const versions: { depth: number; stepId: string; markdown: string }[] = []
    for (const step of steps) {
      if (step.step_type === "synthesize" && step.status === "completed" && step.step_data) {
        try {
          const parsed = JSON.parse(step.step_data)
          if (parsed.report_markdown) {
            versions.push({
              depth: parsed.depth ?? 0,
              stepId: step.id,
              markdown: parsed.report_markdown,
            })
          }
        } catch {}
      }
    }
    versions.sort((a, b) => a.depth - b.depth)
    
    if (versions.length === 0 && current.result_summary) {
      const fallbackDepth = steps.reduce((max, s) => {
        try {
          const parsed = JSON.parse(s.step_data)
          return typeof parsed.depth === "number" ? Math.max(max, parsed.depth) : max
        } catch { return max }
      }, 0)
      
      versions.push({
        depth: fallbackDepth,
        stepId: "",
        markdown: current.result_summary,
      })
    }
    return versions
  }, [steps, current.result_summary])

  const [activeReportIndex, setActiveReportIndex] = useState<number | null>(null)

  useEffect(() => {
    if (reportVersions.length > 0) {
      setActiveReportIndex(reportVersions.length - 1)
    } else {
      setActiveReportIndex(null)
    }
  }, [reportVersions.length])

  const color = STATUS_COLORS[current.status] ?? "#666"
  const activeReport = activeReportIndex !== null && reportVersions[activeReportIndex] ? reportVersions[activeReportIndex] : null
  const reportContent = activeReport ? activeReport.markdown : (current.result_summary || "")
  const baseName = slugify(extractReportTitle(reportContent) ?? current.title)

  const notesAppendixMd = taskNotes.length > 0
    ? "\n\n---\n\n## Notes\n\n" + taskNotes.map(n => {
        const visLabel = n.visibility === "shared" ? "Shared" : n.visibility === "agent" ? "Agent" : "Personal"
        let md = `### ${visLabel} Note\n\n**Selected text:** "${n.selected_text}"\n`
        if (n.comment) md += `\n**Comment:**\n> ${n.comment.replace(/\n/g, '\n> ')}\n`
        return md
      }).join("\n")
    : ""

  const notesAppendixHtml = taskNotes.length > 0
    ? `<hr><h2>Notes</h2>` + taskNotes.map(n => {
        const visLabel = n.visibility === "shared" ? "Shared" : n.visibility === "agent" ? "Agent" : "Personal"
        const colorCode = n.visibility === "shared" ? COLOR_PALETTE.noteShared : n.visibility === "agent" ? COLOR_PALETTE.noteAgent : COLOR_PALETTE.notePersonal
        let html = `<div style="margin:1em 0;padding:0.5em 0;border-bottom:1px solid #ddd">`
        html += `<strong style="color:${colorCode}">[${visLabel}]</strong> <em>"${n.selected_text.replace(/</g, '&lt;').replace(/>/g, '&gt;')}"</em>`
        if (n.comment) html += `<blockquote style="border-left:3px solid #ccc;margin:0.3em 0;padding-left:1em;color:#555">${n.comment.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</blockquote>`
        html += `</div>`
        return html
      }).join("")
    : ""

  useEffect(() => {
    if (tab === "notes") {
      getTaskUnifiedNotes(task.id).then(setUnifiedNotes).catch(() => {})
    }
  }, [task.id, tab])

  const handleUnifiedNoteGoto = (note: UnifiedNoteInfo) => {
    if (note.asset_type === "research_task") {
      setTab("report")
      setTimeout(() => {
        import("../../../utils/noteHighlight")
          .then(({ scrollToNoteHighlight }) => scrollToNoteHighlight(note.id))
          .catch(() => {})
      }, 100)
    } else if (note.asset_type === "research_step") {
      setNavigateStepId(note.asset_id)
      setTab("steps")
    }
  }

  const handleExportNotes = () => {
    const lines: string[] = [`# Research Notes — ${current.title}`, ""]
    const groups = new Map<string, UnifiedNoteInfo[]>()
    for (const n of unifiedNotes) {
      const key = n.asset_type === "research_task"
        ? "Report"
        : n.step_number != null
          ? `Step #${n.step_number}: ${STEP_LABELS[n.step_type || ""] || n.step_type || "?"}`
          : "Unknown"
      const existing = groups.get(key) || []
      existing.push(n)
      groups.set(key, existing)
    }
    for (const [group, notes] of groups) {
      lines.push(`## ${group}`, "")
      for (const n of notes) {
        const visLabel = n.visibility === "shared" ? "Shared" : n.visibility === "agent" ? "Agent" : "Personal"
        lines.push(`### ${visLabel} Note`)
        lines.push("")
        lines.push(`**Selected text:** "${n.selected_text}"`)
        if (n.comment) {
          lines.push("")
          lines.push("**Comment:**")
          lines.push(`> ${n.comment.replace(/\n/g, "\n> ")}`)
        }
        lines.push("")
      }
    }
    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${slugify(current.title)}-notes.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
      <HeaderContainer>
        <div className="flex items-center gap-2 min-w-0">
          <a href="/research" className="text-[#666] hover:text-action-hover text-[11px] transition-colors cursor-pointer font-bold">[◀ back]</a>
          <span className="text-[#333]">|</span>
          <span className="text-[11px] text-semantic-header tracking-widest uppercase select-none shrink-0 flex items-center gap-1.5">
            <HeaderIndicator intent="gold" />
            <HeaderLogo onClick={() => window.location.href = '/nodes'} />
          </span>
          <HeaderSeparator />
          <span className="text-[#bbb] text-xs truncate font-bold">{current.title}</span>
          <span style={{ color }} className="text-[10px] ml-1 uppercase shrink-0 font-bold">{current.status}</span>
          {orchPhase && orchPhase !== "complete" && (
            <HeaderLabel intent="gold" className="text-[9px] ml-1">[{orchPhase}]</HeaderLabel>
          )}
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <CreasesDropdown />
          <HeaderActionButton onClick={() => window.location.href = '/agent'}>
            agent
          </HeaderActionButton>
        </div>
      </HeaderContainer>

      <div className="flex flex-wrap gap-x-1 gap-y-1 px-4 py-2 text-[10px] select-none shrink-0">
        {SUB_TABS.map((t, i) => (
          <span key={t.key} className="flex items-center gap-x-1 whitespace-nowrap">
            {i > 0 && <span className="text-[#333]">•</span>}
            <button
              onClick={() => setTab(t.key)}
              className={`cursor-pointer transition-colors ${tab === t.key ? "text-[#94a3b8]" : "text-[#444] hover:text-[#777]"}`}
            >
              {t.label}{t.key === "notes" && unifiedNotes.length > 0 ? ` (${unifiedNotes.length})` : ""}
            </button>
          </span>
        ))}
      </div>

      <div className="flex-1 min-h-0 flex flex-col px-4 pb-4 pt-1">
        {tab === "info"     && <div className="flex-1 overflow-y-auto pr-1"><InfoTab task={current} orchPhase={orchPhase} onRefreshTask={refreshAll} /></div>}
        {tab === "steps"    && <StepsTab taskId={current.id} orchPhase={orchPhase} taskStatus={current.status} onRefreshTask={refreshAll} onSelectTab={setTab} externalStepId={navigateStepId} />}

        {tab === "report"   && (
          <div className="flex-1 min-h-0 flex flex-col pr-1">
            {reportVersions.length > 1 && (
              <div className="flex flex-wrap items-center gap-1.5 border-b border-ui-border pb-2 mb-3 text-[9px] font-mono select-none shrink-0">
                <span className="text-ui-dim mr-1.5 uppercase font-bold">[ Versions ]</span>
                {reportVersions.map((ver, idx) => {
                  const isSelected = activeReportIndex === idx
                  return (
                    <button
                      key={ver.stepId || idx}
                      onClick={() => setActiveReportIndex(idx)}
                      className={`px-1.5 py-0.5 rounded-[2px] cursor-pointer transition-colors border font-mono
                        ${isSelected 
                          ? "text-semantic-gold border-semantic-gold/30 bg-action-hover/5 font-bold" 
                          : "text-ui-dim border-transparent hover:text-ui-secondary hover:bg-action-hover/5"}`}
                    >
                      {idx === reportVersions.length - 1 ? `Cycle ${ver.depth + 1} (Latest)` : `Cycle ${ver.depth + 1}`}
                    </button>
                  )
                })}
              </div>
            )}
            {reportContent ? (
              <div className="flex-1 flex flex-col min-h-0">
                <NotableMarkdown
                  assetType="research_task"
                  assetId={task.id}
                  content={reportContent}
                  title={activeReport ? `Cycle ${activeReport.depth + 1} Report` : "Research Synthesis Report"}
                  contentRef={reportRef}
                  onNotesChange={setTaskNotes}
                  className="flex-1 min-h-0 flex flex-col"
                  contentClassName="flex-1 overflow-y-auto text-[#94a3b8] text-[10px] leading-relaxed prose prose-invert prose-xs max-w-none"
                  headerActions={
                    <div className="flex items-center gap-2">
                      <TerminalButton onClick={async () => { const ok = await copyToClipboard(reportContent); if (ok) { setCopied(true); setTimeout(() => setCopied(false), 1500) } }} intent="neutral">
                        {copied ? "copied!" : "copy markdown"}
                      </TerminalButton>
                      <TerminalButton onClick={() => { const blob = new Blob([reportContent + notesAppendixMd], { type: "text/markdown;charset=utf-8" }); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = `${baseName}.md`; a.click(); URL.revokeObjectURL(url) }} intent="neutral">export markdown</TerminalButton>
                      <TerminalButton onClick={() => { const html = (reportRef.current?.innerHTML ?? "") + notesAppendixHtml; const w = window.open("", "_blank", "width=800,height=900"); if (!w) return; w.document.write(`<!DOCTYPE html><html><head><title>${baseName}</title><style>body{font-family:-apple-system,Segoe UI,Roboto,monospace;padding:2.5rem;color:#222;max-width:800px;margin:0 auto;line-height:1.7;font-size:13px}h1,h2{color:#333;margin-top:1.2em}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:6px 10px;text-align:left;font-size:12px}th{background:#f5f5f5}code{background:#f0f0f0;padding:2px 5px;border-radius:3px;font-size:12px}pre{background:#f6f6f6;padding:10px}a{color:#06c}img{max-width:100%}</style></head><body>${html}</body></html>`); w.document.close(); w.focus(); setTimeout(() => w.print(), 300) }} intent="cyan">export pdf</TerminalButton>
                    </div>
                  }
                />
              </div>
            ) : (
              <div className="text-[10px] text-[#444] py-2 font-mono italic">
                Synthesis in progress — the final report will be available here when completed.
              </div>
            )}
          </div>
        )}

        {tab === "notes"   && (
          <div className="flex-1 overflow-y-auto pr-1">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Unified Notes ]</span>
              {unifiedNotes.length > 0 && (
                <TerminalButton onClick={handleExportNotes} intent="neutral">export notes</TerminalButton>
              )}
            </div>
            {unifiedNotes.length === 0 ? (
              <div className="text-[10px] text-ui-dim py-2 font-mono italic">
                No notes yet. Add notes in the Report or any step's result panel.
              </div>
            ) : (
              <div className="space-y-1">
                {unifiedNotes.map((note) => {
                  const isAgent = note.visibility === "agent"
                  const isShared = note.visibility === "shared"
                  const label = isAgent ? "A" : isShared ? "SH" : "P"
                  const labelColor = isAgent ? "text-semantic-blue" : isShared ? "text-semantic-purple" : "text-semantic-gold"
                  const sourceLabel = note.asset_type === "research_task"
                    ? "Report"
                    : note.step_number != null
                      ? `Step #${note.step_number}: ${STEP_LABELS[note.step_type || ""] || note.step_type || "?"}`
                      : note.step_type
                        ? `Step: ${STEP_LABELS[note.step_type] || note.step_type}`
                        : "Unknown"

                  return (
                    <div key={note.id} className="flex flex-col gap-0.5 py-1 px-1.5 hover:bg-action-hover/5 transition-colors border border-transparent rounded-[2px] group/note">
                      <div className="flex items-start gap-1 font-mono text-[10px] leading-tight">
                        <span className={`${labelColor} font-bold shrink-0 w-3.5`}>{label}</span>
                        <span className="text-ui-dim font-bold shrink-0">&gt;&gt;</span>
                        <span className="text-ui-primary break-words flex-1 min-w-0 font-mono select-text">
                          "{note.selected_text}"
                        </span>
                        <button
                          onClick={() => handleUnifiedNoteGoto(note)}
                          className="shrink-0 text-ui-dim hover:text-action-hover transition-colors opacity-0 group-hover/note:opacity-100 ml-0.5"
                          title={note.asset_type === "research_task" ? "Go to Report" : "Go to Step"}
                        >
                          ↗
                        </button>
                      </div>
                      <div className="flex items-center gap-1 pl-4 font-mono text-[9px] leading-tight">
                        <span className="text-ui-dim shrink-0">source:</span>
                        <span className="text-ui-dim/70">{sourceLabel}</span>
                      </div>
                      {note.comment && (
                        <div className="flex items-start gap-1 pl-4 font-mono text-[9px] leading-tight text-ui-dim">
                          <span className="shrink-0 font-bold">&gt;&gt;</span>
                          <span className="break-words flex-1 min-w-0 italic font-mono select-text">
                            {note.comment}
                          </span>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>

      <UnifiedFooter />
    </div>
  )
})

/* ── New Task Form Shell ── */
const NewTaskInline = memo(function NewTaskInline() {
  const handleDispatch = async (payload: any): Promise<string | null> => {
    const { dispatchResearch } = await import("../../../api/research")
    const result = await dispatchResearch(payload)
    if (result) window.location.href = `/research?id=${result.task_id}`
    return result?.task_id ?? null
  }

  const handleClose = () => { window.location.href = "/research" }

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
      <HeaderContainer>
        <div className="flex items-center gap-2">
          <a href="/research" className="text-[#666] hover:text-action-hover text-[11px] transition-colors cursor-pointer font-bold">[◀ back]</a>
          <span className="text-[#333]">|</span>
          <span className="text-[11px] text-semantic-header tracking-widest uppercase select-none shrink-0 flex items-center gap-1.5">
            <HeaderIndicator intent="gold" />
            <HeaderLogo onClick={() => window.location.href = '/nodes'} />
          </span>
          <HeaderSeparator />
          <HeaderLabel intent="gold">new research</HeaderLabel>
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <CreasesDropdown />
        </div>
      </HeaderContainer>
      <div className="flex-1 overflow-y-auto px-4 py-4 max-w-lg">
        <NewResearchForm onDispatch={handleDispatch} onClose={handleClose} />
      </div>
      <UnifiedFooter />
    </div>
  )
})

interface Props {
  taskId: string
  isNew?: boolean
}

export const ResearchTaskPage = memo(function ResearchTaskPage({ taskId, isNew }: Props) {
  if (isNew) return <NewTaskInline />

  const [task, setTask] = useState<ResearchTask | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getResearchTask(taskId).then(setTask).catch(e => setError(e.message))
  }, [taskId])

  if (error) return (
    <div className="flex flex-col h-screen bg-[#0c0c0c] items-center justify-between text-[#ef4444] text-xs font-mono">
      <div className="flex-1 flex flex-col items-center justify-center">
        {error}
        <a href="/research" className="text-[#666] hover:text-[#bbb] mt-2">◀ back</a>
      </div>
      <UnifiedFooter className="w-full" />
    </div>
  )
  if (!task) return (
    <div className="flex flex-col h-screen bg-[#0c0c0c] items-center justify-between text-[#555] text-xs font-mono">
      <div className="flex-1 flex items-center justify-center animate-pulse">[ loading… ]</div>
      <UnifiedFooter className="w-full" />
    </div>
  )

  return <TaskPageInner task={task} />
})
