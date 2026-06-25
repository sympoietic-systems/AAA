// ResearchTaskPage — single research task detail with tabbed Info, Steps, Report, Notes.
import { memo, useState, useEffect, useRef, useCallback, useMemo } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import rehypeRaw from "rehype-raw"
import { HeaderContainer, HeaderIndicator, HeaderLogo, HeaderSeparator, HeaderLabel, HeaderActionButton, CreasesDropdown, UnifiedFooter, TerminalButton } from "../../UI"
import type { ResearchTask } from "../../../api/research"
import { getResearchTask } from "../../../api/research"
import { STATUS_COLORS } from "./constants/taskConstants"
import { useTaskPolling } from "./shared/useTaskPolling"
import { InfoTab } from "./tabs/InfoTab"
import { StepsTab } from "./tabs/StepsTab"
import { NewResearchForm } from "./NewResearchForm"
import { useNotes } from "../../../hooks/useNotes"
import { NotesSection } from "../../shared/NotesSection"
import { SelectionToolbar } from "../nodeexplorer/SelectionToolbar"
import { NoteEditorPopover } from "../nodeexplorer/NoteEditorPopover"
import type { NoteInfo } from "../../../api/client"
import { wrapSelectedTextInMarks } from "../../../utils/noteHighlight"
import { copyToClipboard } from "../../../utils/clipboard"

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
  const noteHook = useNotes("research_task", task.id)

  const defaultTab: SubTabId = task.status === "completed" && task.result_summary ? "report" : "info"
  const [tab, setTab] = useState<SubTabId>(defaultTab)

  const [selectedText, setSelectedText] = useState("")
  const [showToolbar, setShowToolbar] = useState(false)
  const [showEditor, setShowEditor] = useState(false)
  const [noteComment, setNoteComment] = useState("")
  const [noteVisibility, setNoteVisibility] = useState<"personal" | "shared" | "agent">("personal")
  const [popupCoords, setPopupCoords] = useState<{ x: number; y: number } | null>(null)
  const [editingNote, setEditingNote] = useState<NoteInfo | null>(null)
  const [copied, setCopied] = useState(false)
  const reportRef = useRef<HTMLDivElement>(null)
  const [highlightedReport, setHighlightedReport] = useState(task.result_summary || "")

  useEffect(() => {
    try {
      setHighlightedReport(wrapSelectedTextInMarks(task.result_summary || "", noteHook.notes))
    } catch (e) {
      console.error("wrapSelectedTextInMarks failed:", e)
    }
  }, [task.result_summary, noteHook.notes])

  const handleMouseUp = useCallback(() => {
    if (editingNote) return
    const sel = window.getSelection()
    if (!sel) return
    const text = sel.toString().trim()
    if (!text) return
    const anchorNode = sel.anchorNode
    if (!anchorNode || !reportRef.current?.contains(anchorNode)) return
    setSelectedText(text)
    setShowEditor(false)
    setCopied(false)
    if (sel.rangeCount > 0) {
      const range = sel.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      setPopupCoords({ x: rect.left, y: rect.bottom + 8 })
      setEditingNote(null)
      setShowToolbar(true)
    }
  }, [editingNote])

  const handleDismissToolbar = () => {
    setShowToolbar(false)
  }

  const handleOpenEditor = () => {
    setNoteComment("")
    setNoteVisibility("personal")
    setShowToolbar(false)
    setShowEditor(true)
  }

  const handleSaveNote = async () => {
    if (editingNote) {
      await noteHook.editNote(editingNote.id, noteComment, noteVisibility)
      setEditingNote(null)
    } else if (selectedText) {
      await noteHook.addNote(selectedText, noteComment, noteVisibility)
    }
    setShowEditor(false)
    setSelectedText("")
    setNoteComment("")
    setPopupCoords(null)
    window.getSelection()?.removeAllRanges()
  }

  const handleDismissEditor = () => {
    setEditingNote(null)
    setShowEditor(false)
    setSelectedText("")
    setNoteComment("")
    setPopupCoords(null)
    window.getSelection()?.removeAllRanges()
  }

  useEffect(() => {
    if (!showToolbar && !showEditor) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleDismissEditor()
        setShowToolbar(false)
        setSelectedText("")
        setPopupCoords(null)
        window.getSelection()?.removeAllRanges()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [showToolbar, showEditor])

  const handleNoteGoto = (noteId: string) => {
    setTab("report")
    setTimeout(() => {
      import("../../../utils/noteHighlight")
        .then(({ scrollToNoteHighlight }) => scrollToNoteHighlight(noteId))
        .catch(() => {})
    }, 100)
  }

  const handleNoteClick = useCallback((e: React.MouseEvent<HTMLElement>) => {
    e.stopPropagation()
    e.preventDefault()
    const noteId = e.currentTarget.dataset.noteId
    if (!noteId) return
    const note = noteHook.notes.find(n => n.id === noteId)
    if (!note) return
    setSelectedText(note.selected_text)
    setNoteComment(note.comment)
    setNoteVisibility(note.visibility)
    setEditingNote(note)
    const rect = e.currentTarget.getBoundingClientRect()
    const showAbove = rect.bottom + 180 > window.innerHeight
    setPopupCoords({ x: rect.left, y: showAbove ? rect.top - 180 - 8 : rect.bottom + 8 })
    setShowEditor(true)
  }, [noteHook.notes])

  const markComponents = useMemo(() => ({
    mark: ({ node, ...props }: any) => {
      const properties = node?.properties ?? {}
      const noteId = properties['data-note-id'] ?? props['data-note-id']
      const styleString = properties['style'] ?? ''
      const styleObj: Record<string, string> = {}
      if (typeof styleString === 'string' && styleString) {
        styleString.split(';').forEach(pair => {
          const [k, v] = pair.split(':').map(s => s.trim())
          if (!k || !v) return
          if (k.startsWith('--')) {
            styleObj[k] = v
          } else {
            const camelKey = k.replace(/-([a-z])/g, (_, c) => c.toUpperCase())
            styleObj[camelKey] = v
          }
        })
      }
      return (
        <mark
          {...{ 'data-note-id': noteId }}
          className={properties['className'] || ''}
          style={styleObj}
          onClick={handleNoteClick}
        >
          {props.children}
        </mark>
      )
    },
  }), [handleNoteClick])

  const color = STATUS_COLORS[current.status] ?? "#666"
  const baseName = slugify(extractReportTitle(current.result_summary ?? "") ?? current.title)
  const reportContent = current.result_summary || ""

  const notesAppendixMd = noteHook.notes.length > 0
    ? "\n\n---\n\n## Notes\n\n" + noteHook.notes.map(n => {
        const visLabel = n.visibility === "shared" ? "Shared" : n.visibility === "agent" ? "Agent" : "Personal"
        let md = `### ${visLabel} Note\n\n**Selected text:** "${n.selected_text}"\n`
        if (n.comment) md += `\n**Comment:**\n> ${n.comment.replace(/\n/g, '\n> ')}\n`
        return md
      }).join("\n")
    : ""

  const notesAppendixHtml = noteHook.notes.length > 0
    ? `<hr><h2>Notes</h2>` + noteHook.notes.map(n => {
        const visLabel = n.visibility === "shared" ? "Shared" : n.visibility === "agent" ? "Agent" : "Personal"
        const colorCode = n.visibility === "shared" ? "#a855f7" : n.visibility === "agent" ? "#22d3ee" : "#eab308"
        let html = `<div style="margin:1em 0;padding:0.5em 0;border-bottom:1px solid #ddd">`
        html += `<strong style="color:${colorCode}">[${visLabel}]</strong> <em>"${n.selected_text.replace(/</g, '&lt;').replace(/>/g, '&gt;')}"</em>`
        if (n.comment) html += `<blockquote style="border-left:3px solid #ccc;margin:0.3em 0;padding-left:1em;color:#555">${n.comment.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</blockquote>`
        html += `</div>`
        return html
      }).join("")
    : ""

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]" onMouseUp={tab === "report" ? handleMouseUp : undefined}>
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
              {t.label}{t.key === "notes" && noteHook.notes.length > 0 ? ` (${noteHook.notes.length})` : ""}
            </button>
          </span>
        ))}
      </div>

      <div className="flex-1 min-h-0 flex flex-col px-4 pb-4 pt-1">
        {tab === "info"     && <div className="flex-1 overflow-y-auto pr-1"><InfoTab task={current} orchPhase={orchPhase} onRefreshTask={refreshAll} /></div>}
        {tab === "steps"    && <StepsTab taskId={current.id} orchPhase={orchPhase} taskStatus={current.status} onRefreshTask={refreshAll} onSelectTab={setTab} />}

        {tab === "report"   && (
          <div className="flex-1 min-h-0 flex flex-col pr-1">
            {reportContent ? (
              <div className="flex-1 flex flex-col min-h-0">
                <div className="flex items-center justify-between mb-1 shrink-0">
                  <span className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Research Synthesis Report ]</span>
                  <div className="flex items-center gap-2">
                    <TerminalButton onClick={async () => { const ok = await copyToClipboard(reportContent); if (ok) { setCopied(true); setTimeout(() => setCopied(false), 1500) } }} intent="neutral">
                      {copied ? "copied!" : "copy markdown"}
                    </TerminalButton>
                    <TerminalButton onClick={() => { const blob = new Blob([reportContent + notesAppendixMd], { type: "text/markdown;charset=utf-8" }); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = `${baseName}.md`; a.click(); URL.revokeObjectURL(url) }} intent="neutral">export markdown</TerminalButton>
                    <TerminalButton onClick={() => { const html = (reportRef.current?.innerHTML ?? "") + notesAppendixHtml; const w = window.open("", "_blank", "width=800,height=900"); if (!w) return; w.document.write(`<!DOCTYPE html><html><head><title>${baseName}</title><style>body{font-family:-apple-system,Segoe UI,Roboto,monospace;padding:2.5rem;color:#222;max-width:800px;margin:0 auto;line-height:1.7;font-size:13px}h1,h2{color:#333;margin-top:1.2em}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:6px 10px;text-align:left;font-size:12px}th{background:#f5f5f5}code{background:#f0f0f0;padding:2px 5px;border-radius:3px;font-size:12px}pre{background:#f6f6f6;padding:10px}a{color:#06c}img{max-width:100%}</style></head><body>${html}</body></html>`); w.document.close(); w.focus(); setTimeout(() => w.print(), 300) }} intent="cyan">export pdf</TerminalButton>
                  </div>
                </div>
                <div ref={reportRef} className="flex-1 min-h-0 overflow-y-auto text-[#94a3b8] text-[10px] leading-relaxed prose prose-invert prose-xs max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]} components={markComponents}>{highlightedReport}</ReactMarkdown>
                </div>
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
              <span className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Notes ]</span>
              <TerminalButton onClick={() => handleOpenEditor()}>+ new note</TerminalButton>
            </div>
            <NotesSection notes={noteHook.notes} onNavigate={handleNoteGoto} onDeleteNote={noteHook.removeNote} />
          </div>
        )}
      </div>

      {showToolbar && popupCoords && (
        <SelectionToolbar selectedText={selectedText} popupCoords={popupCoords} onDismiss={handleDismissToolbar} onOpenNoteEditor={handleOpenEditor} copied={copied} onCopied={setCopied} />
      )}
      {showEditor && popupCoords && (
        <NoteEditorPopover
          selectedText={selectedText}
          noteComment={noteComment}
          noteVisibility={noteVisibility}
          editingNote={editingNote}
          popupCoords={popupCoords}
          onCommentChange={setNoteComment}
          onVisibilityChange={setNoteVisibility}
          onSave={handleSaveNote}
          onDismiss={handleDismissEditor}
          onDeleteNote={editingNote ? noteHook.removeNote : undefined}
        />
      )}

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
