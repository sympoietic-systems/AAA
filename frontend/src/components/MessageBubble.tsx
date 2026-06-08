import { useState, memo, useRef, useEffect } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import rehypeRaw from "rehype-raw"
import type { ChatMessage, MetricsInfo, NoteInfo } from "../api/client"
import { getMessageThinking, getMessageContext } from "../api/client"
import { StructuralAutopoieticGlyph } from "./StructuralAutopoieticGlyph"
import { ContextViewer } from "./ContextViewer"
const DIMENSION_NAMES = [
  "Homeostatic",
  "Amplifying",
  "Cyclic",
  "Bifurcated",
  "Decentralized",
  "Rhizomatic/Networked",
  "Boundary Permeability",
  "Recursion Depth",
  "Variety Filtering",
  "Negentropic Complexity",
  "Temporal Latency",
  "Attractor Depth",
  "Symbiotic",
  "Nomadic",
  "Conversational Co-Orientation",
  "Substrate Materiality"
];

function VitalityBar({ metrics }: { metrics: MetricsInfo }) {
  const items: { label: string; full: string; value: number | null; max: number; warn: number; crit: number; invert: boolean; hint: string }[] = [
    { label: "SIM", full: "pairwise similarity", value: metrics.pairwise_similarity, max: 1.0, warn: 0.7, crit: 0.85, invert: false,
      hint: "Is this input repeating the previous one? >0.85 = near-duplicate" },
    { label: "NOV", full: "conceptual novelty", value: metrics.conceptual_novelty, max: 1.0, warn: 0.15, crit: 0.07, invert: true,
      hint: "Has anything similar ever been said before? <0.15 = exhausted" },
    { label: "ENT", full: "rolling entropy", value: metrics.rolling_entropy, max: 0.25, warn: 0.01, crit: 0.005, invert: true,
      hint: "Is the conversation monotonous over time? <0.01 = entropy collapse" },
    { label: "COUP", full: "coupling coherence", value: metrics.coupling_coherence, max: 1.0, warn: 0.7, crit: 0.9, invert: false,
      hint: "Is the agent responding to what was said? <0.15 = dissociation, >0.85 = echo" },
    { label: "DIVR", full: "agent self-divergence", value: metrics.agent_self_divergence, max: 1.0, warn: 0.2, crit: 0.1, invert: true,
      hint: "Is the agent repeating itself? <0.15 = self-loop" },
    { label: "RP", full: "reverse perturbation", value: metrics.reverse_perturbation, max: 1.0, warn: 0.15, crit: 0.08, invert: true,
      hint: "Did the agent's last response reshape the human's next input? <0.10 = stagnant" },
    { label: "SRP", full: "surprise index", value: metrics.surprise_index, max: 1.0, warn: 0.3, crit: 0.5, invert: false,
      hint: "Distance from decay-weighted centroid of past human inputs (d=0.75). >0.40 = phase disruption" },
    { label: "MPI", full: "mutual perturbation", value: metrics.mutual_perturbation, max: 1.0, warn: 0.15, crit: 0.05, invert: true,
      hint: "Product of coupling x reverse perturbation — are both directions active?" },
    { label: "BORE", full: "boringness", value: metrics.boringness, max: 1.0, warn: 0.4, crit: 0.6, invert: false,
      hint: "Joint failure to perturb: (1 - rP_t) x (1 - MPI_{t-1}). >0.60 = Paskian boredom" },
    { label: "VEL", full: "conceptual velocity", value: metrics.conceptual_velocity, max: 1.0, warn: 0.5, crit: 0.8, invert: false,
      hint: "Disjoint centroid drift rate (last 3 vs preceding 3). <0.02 = frozen, >0.80 = noise" },
    { label: "DRR", full: "divergence resolution ratio", value: metrics.divergence_resolution_ratio, max: 1.0, warn: 0.3, crit: 0.5, invert: false,
      hint: "Does perturbation lead to resolution? Positive = convergence, negative = rejection" },
  ]

  const valueColor = (item: typeof items[0]) => {
    const { value, warn, crit, invert } = item
    if (value == null) return "#555"
    if (invert) {
      if (value <= crit) return "#ef4444"
      if (value <= (crit + warn) / 2) return "#f97316"
      if (value <= warn) return "#facc15"
      return "#4ade80"
    }
    if (value >= crit) return "#ef4444"
    if (value >= (crit + warn) / 2) return "#f97316"
    if (value >= warn) return "#facc15"
    return "#4ade80"
  }

  const fmtVal = (v: number | null) => {
    if (v == null) return "\u2014"
    return v < 0.01 ? v.toFixed(4) : v.toFixed(3)
  }

  return (
    <div className="mt-1 text-[10px] leading-relaxed select-none flex flex-wrap items-center gap-x-2 gap-y-0.5">
      {items.map((item) => {
        const color = valueColor(item)
        const valStr = fmtVal(item.value)
        return (
          <span key={item.label} className="group relative">
            <span className="text-[#555]">#</span>
            <span className="text-[#555]">{item.label}:</span>
            <span style={{ color }}>{valStr}</span>
            <div className="
              absolute bottom-full left-0 mb-1 px-2 py-1
              bg-[#1a1a1a] border border-[#333] rounded
              text-[10px] text-[#aaa] leading-snug
              whitespace-nowrap z-50
              opacity-0 group-hover:opacity-100
              transition-opacity duration-150
              pointer-events-none
            ">
              <div className="text-[#4ade80] text-[11px] font-bold">{item.full}</div>
              <div className="text-[#888]">{valStr} / {item.max}</div>
              <div className="text-[#666] max-w-48 whitespace-normal">{item.hint}</div>
            </div>
          </span>
        )
      })}
      {metrics.conversation_vitality != null && (
        <span className="group relative">
          <span className="text-[#555]">vit:</span>
          <span className={metrics.conversation_vitality < 0.35 ? "text-[#f87171]" : "text-[#4ade80]"}>
            {metrics.conversation_vitality.toFixed(2)}
          </span>
          <div className="
            absolute bottom-full left-0 mb-1 px-2 py-1
            bg-[#1a1a1a] border border-[#333] rounded
            text-[10px] text-[#aaa] leading-snug
            whitespace-nowrap z-50
            opacity-0 group-hover:opacity-100
            transition-opacity duration-150
            pointer-events-none
          ">
            <div className="text-[#4ade80] text-[11px] font-bold">conversation vitality</div>
            <div className="text-[#888]">{metrics.conversation_vitality.toFixed(3)} / 1.0</div>
            <div className="text-[#666]">Composite aliveness score. Higher = more alive.</div>
          </div>
        </span>
      )}
      {metrics.paskian_health != null && (
        <span className="group relative">
          <span className="text-[#555]">ph:</span>
          <span className={metrics.paskian_health < 0.25 ? "text-[#f87171]" : "text-[#4ade80]"}>
            {metrics.paskian_health.toFixed(2)}
          </span>
          <div className="
            absolute bottom-full left-0 mb-1 px-2 py-1
            bg-[#1a1a1a] border border-[#333] rounded
            text-[10px] text-[#aaa] leading-snug
            whitespace-nowrap z-50
            opacity-0 group-hover:opacity-100
            transition-opacity duration-150
            pointer-events-none
          ">
            <div className="text-[#4ade80] text-[11px] font-bold">Paskian health</div>
            <div className="text-[#888]">{metrics.paskian_health.toFixed(3)} / 1.0</div>
            <div className="text-[#666]">Productive zone between strict and permissive. Higher = better.</div>
          </div>
        </span>
      )}
      {metrics.phase_shifts && metrics.phase_shifts.length > 0 && (
        <span className="text-[#facc15]">
          {"\u26A1"}{metrics.phase_shifts.length}
        </span>
      )}
    </div>
  )
}

export const MessageBubble = memo(function MessageBubble({
  msg,
  previousSignature,
  notes = [],
  onAddNote,
  onDeleteNote,
  onUpdateNote
}: {
  msg: ChatMessage
  previousSignature?: number[] | null
  notes?: NoteInfo[]
  onAddNote?: (messageId: number, selectedText: string, comment: string, visibility: "personal" | "shared", startOffset?: number) => void
  onDeleteNote?: (noteId: string) => void
  onUpdateNote?: (noteId: string, comment?: string, visibility?: "personal" | "shared") => void
}) {
  const isHuman = msg.speaker === "human"
  const isSystem = msg.speaker === "system"
  const [thinkingOpen, setThinkingOpen] = useState(false)
  const [contextOpen, setContextOpen] = useState(false)
  const [sigOpen, setSigOpen] = useState(false)
  const [userExpanded, setUserExpanded] = useState(false)
  const [systemOpen, setSystemOpen] = useState(false)

  const bubbleRef = useRef<HTMLDivElement>(null)
  const [selectedText, setSelectedText] = useState("")
  const [showSelectionToolbar, setShowSelectionToolbar] = useState(false)
  const [showNoteCreator, setShowNoteCreator] = useState(false)
  const [noteComment, setNoteComment] = useState("")
  const [noteVisibility, setNoteVisibility] = useState<"personal" | "shared">("personal")
  const [popupCoords, setPopupCoords] = useState<{ x: number; y: number } | null>(null)
  const [selectedStartOffset, setSelectedStartOffset] = useState<number | undefined>(undefined)
  const [editingNote, setEditingNote] = useState<NoteInfo | null>(null)
  const [copied, setCopied] = useState(false)

  const handleMouseUp = () => {
    if (editingNote) return
    const selection = window.getSelection()
    if (!selection) return
    const text = selection.toString().trim()
    if (text && text.length > 0 && bubbleRef.current && msg.id) {
      if (bubbleRef.current.contains(selection.anchorNode)) {
        setSelectedText(text)
        setShowSelectionToolbar(false)
        setShowNoteCreator(false)
        setCopied(false)

        const container = selection.anchorNode?.parentElement?.closest('.markdown-body') as HTMLElement
        if (container) {
          const { start } = getSelectionCharacterOffsetWithin(container)
          setSelectedStartOffset(start)
        }

        if (selection.rangeCount > 0) {
          const range = selection.getRangeAt(0)
          const rect = range.getBoundingClientRect()

          const showAbove = rect.bottom + 36 > window.innerHeight
          setPopupCoords({
            x: rect.left,
            y: showAbove ? rect.top - 36 - 8 : rect.bottom + 8
          })
          setEditingNote(null)
          setShowSelectionToolbar(true)
        }
      }
    }
  }

  const handleSaveNote = () => {
    if (editingNote) {
      if (onUpdateNote) {
        onUpdateNote(editingNote.id, noteComment, noteVisibility)
      }
      setEditingNote(null)
      setShowNoteCreator(false)
      setSelectedText("")
      setNoteComment("")
      setPopupCoords(null)
    } else if (onAddNote && msg.id && selectedText) {
      onAddNote(msg.id, selectedText, noteComment, noteVisibility, selectedStartOffset)
      setShowNoteCreator(false)
      setSelectedText("")
      setNoteComment("")
      setPopupCoords(null)
      setSelectedStartOffset(undefined)
      window.getSelection()?.removeAllRanges()
    }
  }

  useEffect(() => {
    if (!showSelectionToolbar && !showNoteCreator) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (showNoteCreator) {
          setEditingNote(null)
          setShowNoteCreator(false)
          setSelectedText("")
          setNoteComment("")
          setPopupCoords(null)
          window.getSelection()?.removeAllRanges()
        } else if (showSelectionToolbar) {
          setShowSelectionToolbar(false)
        }
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [showSelectionToolbar, showNoteCreator])

  const [thinkingText, setThinkingText] = useState<string | null>(msg.thinking || null)
  const [loadingThinking, setLoadingThinking] = useState(false)
  const [contextText, setContextText] = useState<string | null>(msg.context_sent || null)
  const [loadingContext, setLoadingContext] = useState(false)

  const handleToggleThinking = async () => {
    if (thinkingOpen) {
      setThinkingOpen(false)
      return
    }
    setThinkingOpen(true)
    if (!thinkingText && msg.id) {
      setLoadingThinking(true)
      try {
        const res = await getMessageThinking(msg.id)
        setThinkingText(res.thinking || "No thinking trace available.")
      } catch (err) {
        console.error("Failed to load thinking trace:", err)
        setThinkingText("Failed to load thinking trace.")
      } finally {
        setLoadingThinking(false)
      }
    }
  }

  const handleToggleContext = async () => {
    if (contextOpen) {
      setContextOpen(false)
      return
    }
    setContextOpen(true)
    if (!contextText && msg.id) {
      setLoadingContext(true)
      try {
        const res = await getMessageContext(msg.id)
        setContextText(res.context_sent || "No context available.")
      } catch (err) {
        console.error("Failed to load context:", err)
        setContextText("Failed to load context.")
      } finally {
        setLoadingContext(false)
      }
    }
  }

  if (isSystem) {
    const lines = msg.content.split("\n")
    const title = lines[0] || "System trace"
    const remainingBody = lines.slice(1).join("\n")

    return (
      <div className="mb-3 pl-4 border-l border-[#222]">
        <button
          onClick={() => setSystemOpen(!systemOpen)}
          className="text-[10px] text-[#eab308]/80 hover:text-[#eab308] transition-colors flex items-center gap-1.5 font-mono"
        >
          <span>{systemOpen ? "▼" : "▶"}</span>
          <span>{title}</span>
        </button>
        {systemOpen && remainingBody && (
          <div className="mt-2 text-xs text-[#aaa] leading-relaxed markdown-body pl-3 border-l border-[#1a1a1a]">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
              {remainingBody}
            </ReactMarkdown>
          </div>
        )}
      </div>
    )
  }

  const showThinkingButton = !!msg.thinking || (msg.thinking_tokens != null && msg.thinking_tokens > 0)
  const showContextButton = !!msg.context_sent || !!msg.has_context

  const getStructuralJson = () => {
    if (!msg.structural_signature) return null;
    const scoresMap: Record<string, number> = {};
    msg.structural_signature.forEach((val, idx) => {
      const dimName = DIMENSION_NAMES[idx] || `Dimension ${idx + 1}`;
      scoresMap[dimName] = val;
    });
    return JSON.stringify({
      scores: scoresMap,
      justification: msg.structural_justification || null
    }, null, 2);
  };

  const renderNoteComponent = ({ node, ...props }: any) => {
    const noteId = props.id;
    if (!noteId) {
      return <mark {...props} className="bg-yellow-500/20 text-yellow-100 px-0.5 rounded" />;
    }
    const note = notes.find((n: any) => n.id === noteId);
    if (!note) {
      return (
        <span className="underline decoration-dotted decoration-gray-500 bg-transparent px-0.5 rounded cursor-help" title="Unloaded note">
          {props.children}
        </span>
      );
    }
    const isShared = note.visibility === "shared";
    const highlightColorClass = isShared
      ? "bg-purple-950/50 text-purple-200 border-b border-purple-500/60 cursor-pointer px-0.5 rounded-sm"
      : "bg-yellow-950/60 text-yellow-100 border-b border-yellow-500/60 cursor-pointer px-0.5 rounded-sm";

    const handleHighlightClick = (e: React.MouseEvent) => {
      e.stopPropagation();
      e.preventDefault();
      setSelectedText(note.selected_text);
      setNoteComment(note.comment);
      setNoteVisibility(note.visibility);
      setEditingNote(note);
      
      const rect = e.currentTarget.getBoundingClientRect();
      const showAbove = rect.bottom + 180 > window.innerHeight;
      setPopupCoords({
        x: rect.left,
        y: showAbove ? rect.top - 180 - 8 : rect.bottom + 8
      });
      setShowNoteCreator(true);
    };

    return (
      <span 
        id={`note-highlight-${noteId}`}
        onClick={handleHighlightClick}
        className={`relative group inline ${highlightColorClass}`}
      >
        {props.children}
        {note.comment && (
          <span className="
            absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 p-2
            bg-[#121212] border border-[#2a2a2a] rounded shadow-2xl
            text-[10px] text-gray-200 leading-snug
            whitespace-normal min-w-48 max-w-xs z-50
            opacity-0 group-hover:opacity-100
            transition-opacity duration-150
            pointer-events-none font-sans
          ">
            <div className={`font-mono text-[8px] mb-1 font-bold ${isShared ? "text-purple-400" : "text-yellow-400"}`}>
              {isShared ? "SHARED NOTE" : "PERSONAL NOTE"}
            </div>
            {note.comment}
          </span>
        )}
      </span>
    );
  };

  return (
    <div ref={bubbleRef} className={`mb-3 ${isHuman ? "" : "pl-4"}`}>
      <div className={`text-sm leading-relaxed ${isHuman ? "text-[#777]" : "text-[#c8c8c8]"}`}>
        {isHuman ? (
          <div className="markdown-body" onMouseUp={handleMouseUp}>
            <span className="text-[#555] select-none">&gt; </span>
            <div className={userExpanded ? "" : "max-h-24 overflow-y-auto"}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkBreaks]}
                rehypePlugins={[rehypeRaw]}
                components={{
                  'aaa-note': renderNoteComponent,
                  mark: renderNoteComponent,
                } as any}
              >
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ) : (
          <div className="markdown-body" onMouseUp={handleMouseUp}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkBreaks]}
              rehypePlugins={[rehypeRaw]}
              components={{
                'aaa-note': renderNoteComponent,
                mark: renderNoteComponent,
              } as any}
            >
              {msg.content}
            </ReactMarkdown>
          </div>
        )}
      </div>

      <div className="text-[9px] text-[#444] mt-0.5 select-none flex items-center justify-between">
        <div className="flex items-center gap-2">
          {msg.timestamp && (
            <span className="text-[#555] font-mono">
              {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
            </span>
          )}
          {!isHuman && (msg.model_used || msg.provider_used) && (
            <span className="text-[#555] font-mono">
              [{msg.provider_used || "unknown"} :: {msg.model_used || "unknown"}]
            </span>
          )}
          {!isHuman && msg.active_skills && msg.active_skills.length > 0 && msg.active_skills.map(skill => (
            <span key={skill} className="text-[9px] text-[#4ade80] font-mono border border-[#1a3a1a] bg-[#0a1a0a] px-1 rounded">
              {skill}
            </span>
          ))}
          {!isHuman && msg.active_beliefs && msg.active_beliefs.length > 0 && msg.active_beliefs.map(belief => (
            <span key={belief} className="text-[9px] text-[#60a5fa] font-mono border border-[#1a2a3a] bg-[#0a1220] px-1 rounded">
              {belief}
            </span>
          ))}
        </div>
        <div>
          {msg.content_tokens != null && msg.content_tokens > 0 && (
            <span>
              ~{msg.content_tokens} tok
              {msg.thinking_tokens != null && msg.thinking_tokens > 0 && (
                <span className="text-[#3a3a3a]"> + {msg.thinking_tokens} thk</span>
              )}
            </span>
          )}
        </div>
      </div>

      {showSelectionToolbar && popupCoords && (
        <>
          <div
            className="fixed inset-0 z-40 bg-transparent cursor-default"
            onMouseDown={() => setShowSelectionToolbar(false)}
          />
          <div
            style={{
              position: 'fixed',
              top: `${popupCoords.y}px`,
              left: `${Math.min(window.innerWidth - 180, Math.max(10, popupCoords.x))}px`,
            }}
            onMouseUp={(e) => e.stopPropagation()}
            onClick={(e) => e.stopPropagation()}
            className="fixed z-50 flex items-center gap-0 bg-[#1a1a1a] border border-[#333] shadow-xl rounded-md px-1 py-1 select-none"
          >
            <button
              onClick={() => {
                navigator.clipboard.writeText(selectedText)
                setCopied(true)
                setTimeout(() => {
                  setShowSelectionToolbar(false)
                  setCopied(false)
                }, 800)
              }}
              className="text-[#888] hover:text-[#4ade80] px-2 py-0.5 text-[10px] font-mono transition-colors whitespace-nowrap"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
            <span className="text-[#333] text-[10px] px-0.5">|</span>
            <button
              onClick={() => {
                setShowSelectionToolbar(false)
                setShowNoteCreator(true)
              }}
              className="text-[#888] hover:text-[#e09b67] px-2 py-0.5 text-[10px] font-mono transition-colors whitespace-nowrap"
            >
              Note
            </button>
          </div>
        </>
      )}

      {showNoteCreator && popupCoords && (
        <>
          {/* Backdrop overlay to handle deselect and clicks outside */}
          <div 
            className="fixed inset-0 z-40 bg-transparent cursor-default"
            onMouseDown={() => {
              setShowNoteCreator(false)
              setEditingNote(null)
              setSelectedText("")
              setNoteComment("")
              setPopupCoords(null)
              window.getSelection()?.removeAllRanges() // Clear selection
            }}
          />
          
          <div 
            style={{
              position: 'fixed',
              top: `${popupCoords.y}px`,
              left: `${Math.min(window.innerWidth - 400, Math.max(10, popupCoords.x - 100))}px`,
            }}
            onMouseUp={(e) => e.stopPropagation()}
            onClick={(e) => e.stopPropagation()}
            className="fixed z-50 w-[380px] p-3 bg-[#111] border border-[#333] shadow-2xl rounded-md text-xs select-none"
          >
            <div className="text-gray-400 font-mono mb-2">
              {editingNote ? "EDIT NOTE FOR SELECTION:" : "ADD NOTE FOR SELECTION:"}
            </div>
            <div className={`italic text-gray-500 bg-[#090909] p-2 rounded mb-2 border-l-2 ${noteVisibility === 'shared' ? 'border-purple-500' : 'border-yellow-500'} overflow-x-auto whitespace-pre-wrap max-h-20 font-mono`}>
              "{selectedText}"
            </div>
            <textarea
              value={noteComment}
              onChange={(e) => setNoteComment(e.target.value)}
              placeholder="Add comment..."
              className="w-full bg-[#1a1a1a] border border-[#333] p-2 rounded text-[#ccc] placeholder-[#555] focus:outline-none focus:border-[#4ade80] resize-none h-16 mb-2"
              autoFocus
            />
            <div className="flex items-center justify-between">
              <div className="flex gap-2">
                <button
                  onClick={() => setNoteVisibility("personal")}
                  className={`px-2 py-1 rounded text-[10px] transition-colors ${
                    noteVisibility === "personal"
                      ? "bg-[#333] text-white border border-[#555]"
                      : "bg-transparent text-[#555] border border-transparent hover:text-gray-300"
                  }`}
                >
                  Personal
                </button>
                <button
                  onClick={() => setNoteVisibility("shared")}
                  className={`px-2 py-1 rounded text-[10px] transition-colors ${
                    noteVisibility === "shared"
                      ? "bg-purple-950 text-purple-200 border border-purple-800"
                      : "bg-transparent text-[#555] border border-transparent hover:text-purple-400"
                  }`}
                >
                  Shared
                </button>
              </div>
              <div className="flex gap-2">
                {editingNote && onDeleteNote && (
                  <button
                    onClick={() => {
                      onDeleteNote(editingNote.id)
                      setEditingNote(null)
                      setShowNoteCreator(false)
                      setSelectedText("")
                      setNoteComment("")
                      setPopupCoords(null)
                    }}
                    className="text-[#ef4444] hover:text-red-400 hover:underline px-2 py-1 mr-2 text-[10px]"
                  >
                    Delete
                  </button>
                )}
                <button
                  onClick={() => {
                    setEditingNote(null);
                    setShowNoteCreator(false);
                    setSelectedText("");
                    setNoteComment("");
                    setPopupCoords(null);
                    window.getSelection()?.removeAllRanges();
                  }}
                  className="text-gray-500 hover:text-gray-300 px-2 py-1"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveNote}
                  className="bg-green-800 hover:bg-green-700 text-green-100 px-3 py-1 rounded font-mono text-[10px]"
                >
                  Save
                </button>
              </div>
            </div>
          </div>
        </>
      )}

      {isHuman && msg.metrics && <VitalityBar metrics={msg.metrics} />}

      {!isHuman && msg.truncated && (
        <div className="mt-2 px-3 py-2 border border-[#f59e0b]/40 bg-[#f59e0b]/5 rounded text-xs text-[#f59e0b]/90 leading-relaxed">
          <div className="flex items-center gap-1.5 font-semibold mb-0.5">
            <span>{'\u26A0'}</span>
            <span>Response truncated</span>
          </div>
          <div className="text-[#f59e0b]/60">
            The model stopped before finishing (reason: {msg.finish_reason || "token limit"}).
            The output may be incomplete. Try breaking your request into smaller parts.
          </div>
        </div>
      )}

      {showThinkingButton && (
        <div className="mt-1">
          <button
            onClick={handleToggleThinking}
            className="text-[10px] text-[#555] hover:text-[#888] transition-colors flex items-center gap-1 font-mono"
          >
            <span>{thinkingOpen ? "▼" : "▶"}</span>
            <span>thinking</span>
          </button>
          {thinkingOpen && (
            <div className="mt-1 pl-3 border-l border-[#2a2a2a] text-xs text-[#666] leading-relaxed whitespace-pre-wrap font-mono bg-[#090909]/40 py-1 pr-2 rounded">
              {loadingThinking ? (
                <span className="animate-pulse">Loading thinking trace...</span>
              ) : (
                thinkingText
              )}
            </div>
          )}
        </div>
      )}

      {isHuman && msg.content && msg.content.length > 200 && (
        <div className="mt-1">
          <button
            onClick={() => setUserExpanded(!userExpanded)}
            className="text-[10px] text-[#555] hover:text-[#888] transition-colors flex items-center gap-1 font-mono"
          >
            <span>{userExpanded ? "▼" : "▶"}</span>
            <span>{userExpanded ? "collapse" : "expand"}</span>
          </button>
        </div>
      )}

      {showContextButton && (
        <div className="mt-1">
          <button
            onClick={handleToggleContext}
            className="text-[10px] text-[#555] hover:text-[#888] transition-colors flex items-center gap-1 font-mono"
          >
            <span>{contextOpen ? "▼" : "▶"}</span>
            <span>context</span>
          </button>
          {contextOpen && (
            <div className="mt-2 w-full">
              {loadingContext ? (
                <div className="pl-3 border-l border-[#2a2a2a] text-xs text-[#666] font-mono py-1 animate-pulse">
                  Loading context...
                </div>
              ) : (
                <ContextViewer contextText={contextText || ""} />
              )}
            </div>
          )}
        </div>
      )}

      {msg.structural_signature && msg.structural_signature.length > 0 && (
        <div className="mt-2">
          <button
            onClick={() => setSigOpen(!sigOpen)}
            className="text-[10px] text-[#555] hover:text-[#888] transition-colors flex items-center gap-1 font-mono mb-1.5"
          >
            <span>{sigOpen ? "▼" : "▶"}</span>
            <span>structural signature</span>
          </button>
          {sigOpen && (
            <StructuralAutopoieticGlyph
              signature={msg.structural_signature}
              previousSignature={previousSignature}
              isStagnant={msg.metrics && msg.metrics.boringness != null ? msg.metrics.boringness > 0.5 : false}
              payloadJson={getStructuralJson()}
              justification={msg.structural_justification}
            />
          )}
        </div>
      )}
    </div>
  )
}, (prevProps, nextProps) => {
  return prevProps.msg.id === nextProps.msg.id &&
         prevProps.msg.speaker === nextProps.msg.speaker &&
         prevProps.msg.content === nextProps.msg.content &&
         prevProps.msg.thinking === nextProps.msg.thinking &&
         prevProps.msg.context_sent === nextProps.msg.context_sent &&
         prevProps.msg.metrics === nextProps.msg.metrics &&
         prevProps.msg.structural_justification === nextProps.msg.structural_justification &&
         prevProps.msg.truncated === nextProps.msg.truncated &&
          prevProps.msg.finish_reason === nextProps.msg.finish_reason &&
          areStringArraysEqual(prevProps.msg.active_skills, nextProps.msg.active_skills) &&
          areStringArraysEqual(prevProps.msg.active_beliefs, nextProps.msg.active_beliefs) &&
         areNumberArraysEqual(prevProps.msg.structural_signature, nextProps.msg.structural_signature) &&
         areNumberArraysEqual(prevProps.previousSignature, nextProps.previousSignature) &&
         areNotesEqual(prevProps.notes, nextProps.notes);
})

function areNumberArraysEqual(a?: number[] | null, b?: number[] | null) {
  if (a === b) return true;
  if (!a || !b) return false;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

function areStringArraysEqual(a?: string[] | null | undefined, b?: string[] | null | undefined) {
  if (a === b) return true;
  if (!a || !b) return false;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

function areNotesEqual(a?: NoteInfo[] | null, b?: NoteInfo[] | null) {
  if (a === b) return true;
  if (!a || !b) return false;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i].id !== b[i].id || 
        a[i].comment !== b[i].comment || 
        a[i].visibility !== b[i].visibility || 
        a[i].selected_text !== b[i].selected_text) {
      return false;
    }
  }
  return true;
}

function getSelectionCharacterOffsetWithin(element: HTMLElement) {
  let start = 0
  let end = 0
  const doc = element.ownerDocument || document
  const win = doc.defaultView || window
  const sel = win.getSelection()
  if (sel && sel.rangeCount > 0) {
    const range = sel.getRangeAt(0)
    const preCORSectRange = range.cloneRange()
    preCORSectRange.selectNodeContents(element)
    preCORSectRange.setEnd(range.startContainer, range.startOffset)
    start = preCORSectRange.toString().length
    end = start + range.toString().length
  }
  return { start, end }
}
