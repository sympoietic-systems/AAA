import { useState, useMemo, useCallback, memo } from "react"
import type { ConversationFile, ChatMessage, NoteInfo, ConversationTagInfo, ConversationTreeNode } from "../api/client"
import { getMessagePath } from "../api/client"
import { InputBar } from "./InputBar"
import { MessageBubble } from "./MessageBubble"

interface Props {
  selectedNode: ChatMessage | null
  parentNode: ChatMessage | null
  siblingNodes: ConversationTreeNode[]
  childNodes: ConversationTreeNode[]
  treeNodes: ConversationTreeNode[]
  loading: boolean
  error: string | null
  agentName: string
  conversationId: string
  conversationTitle: string
  uploadedFiles: ConversationFile[]
  onSend: (text: string) => void
  onUploadFiles: (files: File[]) => void
  isIndexing: boolean
  onClearError: () => void
  onRegenerate?: (userMsgId?: number) => void
  onRenameTitle: (title: string) => void
  onGenerateTitle: () => void
  className?: string
  notes?: NoteInfo[]
  isPassword?: boolean
  onAddNote?: (messageId: number, selectedText: string, comment: string, visibility: "personal" | "shared" | "agent", startOffset?: number) => void
  onDeleteNote?: (noteId: string) => void
  onUpdateNote?: (noteId: string, comment?: string, visibility?: "personal" | "shared" | "agent") => void
  tags?: ConversationTagInfo[]
  onAddTag?: (tag: string) => void
  onRemoveTag?: (tag: string) => void
  onNavigateToMessage: (messageId: number) => void
  onGoHome?: () => void
  history?: { id: number; speaker: string; snippet: string }[]
}

const EMPTY_ARRAY: NoteInfo[] = []

// Parent Message Card (Memoized)
const ParentNodeCard = memo(function ParentNodeCard({
  parentMsg,
  onNavigate,
  notes = [],
  onAddNote,
  onDeleteNote,
  onUpdateNote,
}: {
  parentMsg: ChatMessage | null
  onNavigate: (id: number) => void
  notes: NoteInfo[]
  onAddNote?: (messageId: number, selectedText: string, comment: string, visibility: "personal" | "shared" | "agent", startOffset?: number) => void
  onDeleteNote?: (noteId: string) => void
  onUpdateNote?: (noteId: string, comment?: string, visibility?: "personal" | "shared" | "agent") => void
}) {
  if (!parentMsg) {
    return (
      <div className="border border-dashed border-[#222] bg-[#070708]/40 rounded-sm p-4 text-center select-none">
        <span className="text-[10px] text-[#444] uppercase font-mono tracking-wider">
          Origin Cut (No Predecessor Strata)
        </span>
      </div>
    )
  }

  return (
    <div className="border border-[#1f1f24] bg-[#0c0c0e]/80 rounded-sm p-4 hover:border-[#333] transition-all relative group/parentcard">
      <div className="flex items-center justify-between border-b border-[#1b1b20] pb-2 mb-3 select-none">
        <span className="text-[9px] text-[#666] font-mono uppercase tracking-widest">
          Predecessor Node : {parentMsg.speaker === "human" ? "Human" : "Apparatus"}
        </span>
        <button
          onClick={() => onNavigate(parentMsg.id)}
          className="text-[9px] text-[#888] hover:text-[#4ade80] font-mono border border-[#333] hover:border-[#4ade80]/50 px-2 py-0.5 rounded-sm bg-[#121214] transition-all duration-150 cursor-pointer"
        >
          [^ Navigate to Parent]
        </button>
      </div>
      <div className="opacity-70 group-hover/parentcard:opacity-100 transition-opacity duration-200">
        <MessageBubble
          msg={parentMsg}
          notes={notes}
          onAddNote={onAddNote}
          onDeleteNote={onDeleteNote}
          onUpdateNote={onUpdateNote}
        />
      </div>
    </div>
  )
})

// Sediment Fold Overlay (Self-Contained & Lazy-Loaded)
const SedimentFold = memo(function SedimentFold({
  selectedNodeId,
  onNavigate,
}: {
  selectedNodeId: number | null
  onNavigate: (id: number) => void
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [ancestors, setAncestors] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [prevSelectedNodeId, setPrevSelectedNodeId] = useState<number | null>(selectedNodeId)

  const handleToggle = useCallback(async () => {
    if (isOpen) {
      setIsOpen(false)
      return
    }
    setIsOpen(true)
    if (!selectedNodeId) return

    setLoading(true)
    try {
      const path = await getMessagePath(selectedNodeId)
      // The path returns ancestors, with the selected node at the end.
      // We want to show everything before the selected node.
      const list = path.filter((m) => m.id !== selectedNodeId)
      setAncestors(list)
    } catch (err) {
      console.error("Failed to load ancestor path for sediment fold:", err)
    } finally {
      setLoading(false)
    }
  }, [isOpen, selectedNodeId])
  if (selectedNodeId !== prevSelectedNodeId) {
    setPrevSelectedNodeId(selectedNodeId)
    setIsOpen(false)
    setAncestors([])
  }

  return (
    <div className="flex flex-col items-center my-3 relative w-full">
      {/* Visual Divider Line */}
      <div className="absolute inset-0 flex items-center" aria-hidden="true">
        <div className="w-full border-t border-[#18181b]" />
      </div>

      <button
        onClick={handleToggle}
        className="relative z-10 flex items-center gap-1.5 px-3 py-1 text-[9px] font-mono text-[#555] hover:text-[#aaa] bg-[#0c0c0e] border border-[#1b1b20] hover:border-[#3f3f46] rounded-full transition-all duration-150 cursor-pointer shadow-lg uppercase tracking-wider"
      >
        <span>{isOpen ? "▼" : "▶"}</span>
        <span>Sediment Fold ({isOpen ? "Collapse" : "Expand Enfolded Strata"})</span>
      </button>

      {isOpen && (
        <div className="w-full mt-3 border border-[#1b1b20] bg-[#09090b]/90 rounded-sm p-3 z-20 max-h-60 overflow-y-auto shadow-2xl flex flex-col gap-2">
          <div className="text-[9px] text-[#444] uppercase font-mono tracking-wider border-b border-[#18181b] pb-1.5 mb-1 select-none">
            Deep Memory Strata Chain
          </div>
          {loading ? (
            <div className="text-[10px] text-[#555] font-mono animate-pulse py-2">
              Retrieving enfolded sediment path...
            </div>
          ) : ancestors.length === 0 ? (
            <div className="text-[10px] text-[#444] font-mono py-2 italic select-none">
              No deeper historical strata folded below this cut.
            </div>
          ) : (
            ancestors.map((item, idx) => (
              <div
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className="group/item flex items-start justify-between p-2 rounded-sm bg-[#121214]/60 hover:bg-[#18181c] border border-transparent hover:border-[#222]/80 cursor-pointer transition-all duration-150"
              >
                <div className="flex-1 min-w-0 pr-4">
                  <div className="flex items-center gap-2 mb-1 select-none">
                    <span className="text-[8px] text-[#555] font-mono">
                      #{idx + 1}
                    </span>
                    <span className={`text-[8px] font-mono uppercase tracking-wider ${
                      item.speaker === "human" ? "text-[#6bc28c]" : "text-[#a892ee]"
                    }`}>
                      {item.speaker === "human" ? "Human" : "Apparatus"}
                    </span>
                    {item.timestamp && (
                      <span className="text-[8px] text-[#3c3c44] font-mono">
                        {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-[#888] group-hover/item:text-[#bbb] truncate font-mono">
                    {item.content || "..."}
                  </p>
                </div>
                <span className="text-[9px] text-[#444] group-hover/item:text-[#4ade80] font-mono select-none self-center transition-colors">
                  [Jump]
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
})

// Sibling & Child Transition Links (Memoized)
const GlimmerLinks = memo(function GlimmerLinks({
  siblingNodes,
  childNodes,
  onNavigate,
}: {
  siblingNodes: ConversationTreeNode[]
  childNodes: ConversationTreeNode[]
  onNavigate: (id: number) => void
}) {
  const hasSiblings = siblingNodes.length > 0
  const hasChildren = childNodes.length > 0

  if (!hasSiblings && !hasChildren) return null

  return (
    <div className="mt-4 border-t border-[#18181b] pt-3 flex flex-col gap-2.5 select-none">
      {hasSiblings && (
        <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
          <span className="text-[#555] uppercase tracking-wider text-[9px]">Lateral Strata (Siblings):</span>
          {siblingNodes.map((sib, index) => (
            <button
              key={sib.id}
              onClick={() => onNavigate(sib.id)}
              className="px-2 py-0.5 border border-[#222] hover:border-[#e09b67]/60 hover:text-[#e09b67] bg-[#0c0c0e] hover:bg-[#141210] rounded-sm text-[#888] transition-all duration-150 cursor-pointer max-w-48 truncate"
              title={`Jump to sibling: ${sib.content}`}
            >
              Alternative {index + 1}: "{sib.content || "..."}"
            </button>
          ))}
        </div>
      )}

      {hasChildren && (
        <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
          <span className="text-[#555] uppercase tracking-wider text-[9px]">Forward Flight (Children):</span>
          {childNodes.map((child) => (
            <button
              key={child.id}
              onClick={() => onNavigate(child.id)}
              className="px-2 py-0.5 border border-[#222] hover:border-[#4ade80]/60 hover:text-[#4ade80] bg-[#0c0c0e] hover:bg-[#0e1410] rounded-sm text-[#888] transition-all duration-150 cursor-pointer max-w-64 truncate"
              title={`Jump to child: ${child.content}`}
            >
              Cut -&gt; "{child.content || "..."}"
            </button>
          ))}
        </div>
      )}
    </div>
  )
})

// Active Selected Node Card (Memoized)
const SelectedNodeCard = memo(function SelectedNodeCard({
  selectedMsg,
  notes = [],
  onAddNote,
  onDeleteNote,
  onUpdateNote,
  onRegenerate,
  siblingIds = [],
  onBranch,
}: {
  selectedMsg: ChatMessage | null
  notes: NoteInfo[]
  onAddNote?: (messageId: number, selectedText: string, comment: string, visibility: "personal" | "shared" | "agent", startOffset?: number) => void
  onDeleteNote?: (noteId: string) => void
  onUpdateNote?: (noteId: string, comment?: string, visibility?: "personal" | "shared" | "agent") => void
  onRegenerate?: (userMsgId?: number) => void
  siblingIds?: number[]
  onBranch?: (messageId: number) => void
}) {
  if (!selectedMsg) {
    return (
      <div className="border border-dashed border-[#222] bg-[#0c0c0e] rounded-sm p-10 text-center select-none">
        <span className="text-xs text-[#555] uppercase font-mono tracking-widest animate-pulse">
          Awaiting Observation Target...
        </span>
      </div>
    )
  }

  return (
    <div className="border border-[#2a2a35] bg-[#0f0f13] rounded-sm p-4 relative shadow-inner">
      <div className="flex items-center justify-between border-b border-[#21212a] pb-2 mb-3 select-none">
        <span className="text-[9px] text-[#888] font-mono uppercase tracking-widest font-semibold text-[#6bc28c]">
          Active Focus Cut : {selectedMsg.speaker === "human" ? "Human" : "Apparatus"}
        </span>
      </div>
      <MessageBubble
        msg={selectedMsg}
        notes={notes}
        onAddNote={onAddNote}
        onDeleteNote={onDeleteNote}
        onUpdateNote={onUpdateNote}
        onBranch={onBranch}
        onRegenerate={onRegenerate}
        siblingIds={siblingIds}
      />
    </div>
  )
})

export function NodeExplorer({
  selectedNode,
  parentNode,
  siblingNodes,
  childNodes,
  treeNodes,
  loading,
  error,
  conversationTitle,
  onSend,
  onUploadFiles,
  isIndexing,
  onClearError,
  onRegenerate,
  onRenameTitle,
  onGenerateTitle,
  className = "",
  notes = [],
  isPassword = false,
  onAddNote,
  onDeleteNote,
  onUpdateNote,
  tags = [],
  onAddTag,
  onRemoveTag,
  onNavigateToMessage,
  onGoHome,
  history = [],
}: Props) {
  const [editingTitle, setEditingTitle] = useState(false)
  const [titleVal, setTitleVal] = useState(conversationTitle)
  const [prevTitle, setPrevTitle] = useState(conversationTitle)
  const [newTagVal, setNewTagVal] = useState("")

  if (conversationTitle !== prevTitle) {
    setPrevTitle(conversationTitle)
    setTitleVal(conversationTitle)
  }

  const handleAddTagSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = newTagVal.trim().toLowerCase()
    if (trimmed && onAddTag) {
      onAddTag(trimmed)
      setNewTagVal("")
    }
  }

  const handleTitleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = titleVal.trim()
    if (trimmed && trimmed !== conversationTitle) {
      onRenameTitle(trimmed)
    }
    setEditingTitle(false)
  }

  const notesByMessageId = useMemo(() => {
    const map = new Map<number, NoteInfo[]>()
    notes.forEach((note) => {
      if (note.message_id !== undefined && note.message_id !== null) {
        if (!map.has(note.message_id)) {
          map.set(note.message_id, [])
        }
        map.get(note.message_id)!.push(note)
      }
    })
    return map
  }, [notes])

  // Derive sibling message IDs for local regeneration navigation inside bubble
  const selectedNodeSiblings = useMemo(() => {
    if (!selectedNode) return []
    const parentId = selectedNode.parent_message_id
    // Find all sibling IDs in the tree sharing same parent and same speaker
    return treeNodes
      .filter((n) => n.parent_message_id === parentId && n.speaker === selectedNode.speaker)
      .map((n) => n.id)
  }, [treeNodes, selectedNode])

  const parentNotes = parentNode ? (notesByMessageId.get(parentNode.id) || EMPTY_ARRAY) : EMPTY_ARRAY
  const selectedNotes = selectedNode ? (notesByMessageId.get(selectedNode.id) || EMPTY_ARRAY) : EMPTY_ARRAY

  return (
    <div className={`flex flex-col h-full bg-[#070709] border-r border-[#1a1a1a] ${className}`}>
      {/* Title Bar */}
      <div className="flex items-center gap-3 border-b border-[#151515] px-4 py-3 select-none">
        {onGoHome && (
          <button
            onClick={onGoHome}
            className="text-xs text-[#555] hover:text-[#aaa] transition-colors border border-[#222] px-2 py-1 rounded-sm bg-[#0c0c0e] cursor-pointer"
            title="Go to Home"
          >
            home
          </button>
        )}
        <div className="flex-1 min-w-0">
          {editingTitle ? (
            <form onSubmit={handleTitleSubmit}>
              <input
                type="text"
                value={titleVal}
                onChange={(e) => setTitleVal(e.target.value)}
                onBlur={handleTitleSubmit}
                className="bg-[#0f0f11] border border-[#333] px-2 py-0.5 text-xs text-[#ddd] font-mono rounded-sm outline-none focus:border-[#4ade80] w-full"
                autoFocus
              />
            </form>
          ) : (
            <div className="flex items-center gap-2">
              <h1
                onClick={() => setEditingTitle(true)}
                className="text-xs font-mono font-bold tracking-wider text-[#aaa] hover:text-[#fff] cursor-pointer truncate max-w-xs uppercase"
              >
                {conversationTitle || "Untitled Entanglement"}
              </h1>
              <button
                onClick={onGenerateTitle}
                className="text-[9px] text-[#444] hover:text-[#4ade80] font-mono cursor-pointer transition-colors"
                title="Auto-generate title"
              >
                #generate_title
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Tags Bar */}
      {tags.length > 0 || onAddTag ? (
        <div className="px-4 py-1.5 border-b border-[#121212] bg-[#09090b] flex flex-wrap items-center gap-x-2 gap-y-1 select-none">
          {tags.map((t, i) => {
            const tagStyle = "text-[#6bc28c] bg-[#0f1b13] border border-[#1a3f28]/60 px-1 rounded-[2px]"
            const isDeletable = true
            return (
              <span key={t.tag} className={`text-[9px] ${tagStyle} font-mono flex items-center gap-0.5`}>
                {i > 0 && <span className="text-[#444] select-none">{" // "}</span>}
                {t.tag}
                {isDeletable && onRemoveTag && (
                  <button
                    onClick={() => onRemoveTag(t.tag)}
                    className="text-[9px] text-[#888] hover:text-[#ef4444] cursor-pointer font-bold select-none"
                    title="Remove tag"
                  >
                    &times;
                  </button>
                )}
              </span>
            )
          })}
          {onAddTag && (
            <form onSubmit={handleAddTagSubmit} className="flex items-center ml-1">
              <input
                type="text"
                placeholder="+ tag"
                value={newTagVal}
                onChange={(e) => setNewTagVal(e.target.value)}
                className="bg-transparent border-0 text-[9px] text-[#888] font-mono outline-none focus:text-[#aaa] w-14 focus:w-24 transition-all duration-150 placeholder:text-[#444] border-b border-transparent focus:border-[#4ade80]"
              />
            </form>
          )}
        </div>
      ) : null}

      {/* Explorer Space */}
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col justify-start">
        {isPassword ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6 select-none max-w-sm mx-auto my-auto border border-[#222] bg-[#0c0c0c] rounded-sm">
            <span className="text-2xl text-[#ef4444] mb-3 animate-pulse">⚙</span>
            <h2 className="text-[#ddd] text-xs font-mono tracking-widest mb-1.5 uppercase">SYSTEM LOCK</h2>
            <p className="text-[#555] text-[10px] font-mono leading-relaxed uppercase">
              Authentication required. Enter credentials in prompt below.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            {/* Traversal History Trail */}
            {history && history.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 px-3 py-1.5 bg-[#0c0c0e]/80 border border-[#1b1b20] rounded-sm text-[9px] font-mono mb-3 select-none">
                <span className="text-[#555] uppercase tracking-wider">Recent:</span>
                {history.map((item, idx) => (
                  <div key={item.id} className="flex items-center gap-1.5">
                    {idx > 0 && <span className="text-[#333]">&gt;</span>}
                    <button
                      onClick={() => onNavigateToMessage(item.id)}
                      className="px-1.5 py-0.5 rounded-sm bg-[#121214] border border-[#222] text-[#888] hover:text-[#4ade80] hover:border-[#4ade80]/40 transition-all cursor-pointer truncate max-w-[130px] font-mono leading-none"
                      title={`Jump to ${item.speaker === "human" ? "Human" : "Apparatus"} message: ${item.snippet}`}
                    >
                      {item.speaker === "human" ? "H" : "A"}: {item.snippet}
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* 1. Parent Node Panel */}
            <ParentNodeCard
              parentMsg={parentNode}
              onNavigate={onNavigateToMessage}
              notes={parentNotes}
              onAddNote={onAddNote}
              onDeleteNote={onDeleteNote}
              onUpdateNote={onUpdateNote}
            />

            {/* 2. Sediment Fold Divider */}
            <SedimentFold
              selectedNodeId={selectedNode ? selectedNode.id : null}
              onNavigate={onNavigateToMessage}
            />

            {/* 3. Selected Node Panel */}
            <SelectedNodeCard
              selectedMsg={selectedNode}
              notes={selectedNotes}
              onAddNote={onAddNote}
              onDeleteNote={onDeleteNote}
              onUpdateNote={onUpdateNote}
              onRegenerate={onRegenerate}
              siblingIds={selectedNodeSiblings}
              onBranch={onNavigateToMessage}
            />

            {/* 4. Sibling & Child links */}
            <GlimmerLinks
              siblingNodes={siblingNodes}
              childNodes={childNodes}
              onNavigate={onNavigateToMessage}
            />

            {/* 5. In-flight Loading state */}
            {loading && (
              <div className="flex items-center gap-2 py-3 px-1 text-[#4ade80]">
                <span className="animate-pulse">▊</span>
                <span className="text-[10px] font-mono uppercase tracking-wider">Metabolizing agential output...</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Error Bar */}
      {error && (
        <div className="mx-4 mb-2 flex items-center gap-2 bg-[#1a1010] border border-[#3a1a1a] px-4 py-2 text-xs text-[#ef4444]">
          <span className="flex-1 truncate uppercase font-mono">{error}</span>
          {onRegenerate && (
            <button
              onClick={() => onRegenerate()}
              className="text-[#4ade80] hover:text-[#22c55e] border border-[#276a3e]/50 px-2.5 py-0.5 rounded-sm text-[10px] tracking-wider font-mono mr-2 bg-[#0d1c12] hover:bg-[#122b1c] transition-colors cursor-pointer"
            >
              retry
            </button>
          )}
          <button onClick={onClearError} className="text-[#884444] hover:text-[#ef4444] font-mono uppercase cursor-pointer">
            dismiss
          </button>
        </div>
      )}

      {/* Input Gap (Diffractive Input) */}
      <InputBar
        onSend={onSend}
        onUploadFiles={onUploadFiles}
        disabled={loading}
        isIndexing={isIndexing}
        isPassword={isPassword}
      />
    </div>
  )
}
