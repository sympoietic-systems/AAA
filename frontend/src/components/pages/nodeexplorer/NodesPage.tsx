import { useState, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useChat } from "../../../hooks/useChat"
import { useConversations } from "../../../hooks/useConversations"
import { useConversationNotes } from "../../../hooks/useNotes"
import { dismissByMatch } from "../../../stores/notificationStore"
import { NodeExplorer } from "./NodeExplorer"
import { SidePanel } from "../../panels/sidepanel/SidePanel"
import ConnectionCloud from "../../panels/leftpanel/ConnectionCloud"
import { SpectralEchoes } from "../../panels/leftpanel/SpectralEchoes"
import SearchTab from "../../panels/leftpanel/SearchTab"
import { addConversationTag, deleteMessage, downloadExport } from "../../../api/client"
import { usePanelResizer } from "../../../hooks/usePanelResizer"
import {
  HeaderContainer,
  HeaderIndicator,
  HeaderLogo,
  HeaderSeparator,
  HeaderLabel,
  HeaderActionButton,
  CreasesDropdown,
  UnifiedFooter,
} from "../../UI"
import { ConversationTitleBar } from "../../shared/ConversationTitleBar"
import { ConversationLandingPage } from "../landing/ConversationLandingPage"

export interface NodesPageProps {
  isAuthEnabled: boolean
  handleLogout: () => void
  agentFlux: boolean
}

const EMPTY_STRING_ARRAY: string[] = []

export function NodesPage({ isAuthEnabled, handleLogout, agentFlux }: NodesPageProps) {
  const navigate = useNavigate()
  const [isNewChatMode, setIsNewChatMode] = useState(false)

  const {
    conversations,
    activeId,
    setActiveId,
    loading: convLoading,
    loadingMore: convLoadingMore,
    hasMore: convHasMore,
    totalCount: convTotalCount,
    loadMore: loadMoreConvs,
    refresh: refreshConvs,
    deleteConversation,
    addConversation,
    newConversation,
    refreshTitle,
    renameConversation,
    generateTitle,
  } = useConversations()

  const {
    messages,
    fullTreeMessages,
    activeMessageId,
    setActiveMessageId,
    activePathIds,
    commitProposedBranch,
    navigateToMessage,
    loading,
    error,
    send,
    regenerate,
    clearError,
    agentName,
    uploadedFiles,
    isIndexing,
    upload,
    deleteFile,
    reprocess,
    refreshMessages,
    refreshTree,
    selectedNode,
    parentNode,
    siblingNodes,
    childNodes,
    treeNodes,
    history,
    links,
  } = useChat(activeId)

  const handleNavigateToNotification = useCallback((convId: string, msgId: number) => {
    dismissByMatch(convId, msgId)
    if (convId === activeId) {
      navigateToMessage(msgId)
    } else {
      setIsNewChatMode(false)
      setActiveId(convId, msgId)
    }
  }, [activeId, navigateToMessage, setActiveId])

  const {
    notes,
    addNote,
    editNote,
    removeNote,
    refreshNotes,
  } = useConversationNotes(activeId || "")

  const handleNavigateNode = useCallback((noteId: string) => {
    const note = notes.find(n => n.id === noteId)
    if (!note) return
    const msgId = Number(note.asset_id)
    if (!Number.isNaN(msgId)) navigateToMessage(msgId)
  }, [notes, navigateToMessage])

  const handleAddNote = async (
    messageId: number,
    selectedText: string,
    comment: string,
    visibility: "personal" | "shared" | "agent",
    startOffset?: number
  ) => {
    const res = await addNote(messageId, selectedText, comment, visibility, startOffset)
    if (res) {
      refreshMessages()
    }
  }

  const handleDeleteNote = useCallback(async (noteId: string) => {
    await removeNote(noteId)
    refreshMessages()
  }, [removeNote, refreshMessages])

  const handleUpdateNote = useCallback(async (noteId: string, comment?: string, visibility?: "personal" | "shared" | "agent") => {
    await editNote(noteId, comment, visibility)
    refreshMessages()
  }, [editNote, refreshMessages])

  const handleDeleteFile = useCallback((fileName: string) => {
    deleteFile(fileName)
  }, [deleteFile])

  const handleDeleteMessage = useCallback(async (messageId: number) => {
    if (!activeId) return
    if (!confirm("Delete this node permanently?")) return
    try {
      await deleteMessage(activeId, messageId)
      refreshMessages()
      refreshTree()
    } catch (err: any) {
      console.error("Failed to delete message:", err)
    }
  }, [activeId, refreshMessages, refreshTree])

  const handleReprocessFile = useCallback((fileName: string) => {
    reprocess(fileName)
  }, [reprocess])

  // Left panel tab: "cloud" | "search"
  const [leftPanelTab, setLeftPanelTab] = useState<"cloud" | "search">("cloud")

  // Collapsible and resizable left panel state (for Connection Cloud DAG)
  const {
    width: leftPanelWidth,
    collapsed: leftPanelCollapsed,
    setCollapsed: setLeftPanelCollapsed,
    handleResizeStart,
  } = usePanelResizer({
    storageKey: "aaa_leftPanelWidth",
    defaultWidth: 320,
    computeMaxWidth: () => Math.floor(window.innerWidth * 0.35),
  })

  // Collapsible and resizable right panel state (for SidePanel information)
  const {
    width: rightPanelWidth,
    collapsed: rightPanelCollapsed,
    setCollapsed: setRightPanelCollapsed,
    handleResizeStart: handleRightResizeStart,
  } = usePanelResizer({
    storageKey: "aaa_rightPanelWidth",
    defaultWidth: 320,
    direction: "left",
    computeMaxWidth: () => Math.floor(window.innerWidth * 0.35),
  })

  const activeIdRef = useRef(activeId)
  activeIdRef.current = activeId

  const activeConv = conversations.find((c) => c.id === activeId)
  const conversationTitle = activeConv?.title || ""
  const conversationId = activeId

  const handleRenameTitle = (title: string) => {
    if (activeId) renameConversation(activeId, title)
  }

  const handleGenerateTitle = async () => {
    if (activeId) await generateTitle(activeId)
  }

  const handleExportConversation = async () => {
    if (activeId) {
      try {
        await downloadExport(activeId)
      } catch (err) {
        console.error("Failed to export conversation:", err)
      }
    }
  }

  const handleAddTag = async (tag: string) => {
    if (activeId) {
      try {
        await addConversationTag(activeId, tag)
        refreshConvs()
      } catch (err) {
        console.error("Failed to add tag:", err)
      }
    }
  }

  const handleSend = async (content: string) => {
    const currentActiveId = activeIdRef.current
    const response = await send(content)

    if (response && response.conversation_id) {
      if (!currentActiveId) {
        setIsNewChatMode(false)
        setActiveId(response.conversation_id)
        addConversation({
          id: response.conversation_id,
          title: "",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          message_count: 2,
        })
        setTimeout(() => refreshTitle(response.conversation_id!), 2000)
      } else {
        refreshConvs()
        refreshNotes()
        const conv = conversations.find((c) => c.id === currentActiveId)
        if (conv && !conv.title.trim() && conv.message_count >= 2) {
          setTimeout(() => generateTitle(currentActiveId), 3000)
        }
      }
    }
  }

  const handleUploadFiles = async (files: File[]) => {
    const currentActiveId = activeIdRef.current
    const newId = await upload(files)
    if (newId && !currentActiveId) {
      setIsNewChatMode(false)
      setActiveId(newId)
      const firstFilename = files[0].name
      const titleBase = firstFilename.substring(0, firstFilename.lastIndexOf('.')) || firstFilename
      addConversation({
        id: newId,
        title: `File trace: ${titleBase.substring(0, 50)}`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        message_count: 0,
      })
      setTimeout(() => refreshTitle(newId), 3000)
    } else {
      refreshConvs()
    }
  }

  const handleSelectConversation = (id: string) => {
    setIsNewChatMode(false)
    setActiveId(id)
  }

  const handleNewConversation = () => {
    setIsNewChatMode(true)
    newConversation()
  }

  const handleGoHome = () => {
    setIsNewChatMode(false)
    setActiveId("")
  }

  // Inside /nodes: If no active conversation and not in new chat mode, show the Landing Page (conversation list)
  if (!activeId && !isNewChatMode) {
    return (
      <ConversationLandingPage
        conversations={conversations}
        loading={convLoading}
        loadingMore={convLoadingMore}
        hasMore={convHasMore}
        totalCount={convTotalCount}
        onLoadMore={loadMoreConvs}
        onSelect={handleSelectConversation}
        onDelete={deleteConversation}
        onNew={handleNewConversation}
        onSearchAndFilter={refreshConvs}
        showLogout={isAuthEnabled}
        onLogout={handleLogout}
        agentFlux={agentFlux}
      />
    )
  }

  // Active chat workspace layout (inside /nodes)
  return (
    <div className="flex flex-col h-screen bg-[#0c0c0c]">
      <HeaderContainer>
        <span className="text-[11px] text-semantic-header tracking-widest uppercase select-none flex items-center gap-1.5 min-w-0">
          <HeaderIndicator intent="green" />
          <HeaderLogo to="/nodes" onClick={handleGoHome} />
          <HeaderSeparator />
          <HeaderLabel intent="green">entanglement</HeaderLabel>
          <HeaderSeparator className="hidden sm:inline" />
          
          <ConversationTitleBar
            title={conversationTitle}
            onRename={handleRenameTitle}
            onGenerateTitle={handleGenerateTitle}
          />
        </span>

        <div className="flex items-center gap-3 sm:gap-4 shrink-0">
          {conversationId && (
            <HeaderActionButton
              onClick={handleExportConversation}
              title="Export conversation as Markdown"
              className="hidden md:inline"
            >
              #export
            </HeaderActionButton>
          )}

          <HeaderActionButton
            onClick={() => setLeftPanelCollapsed(prev => !prev)}
            title="Toggle Connection Cloud (DAG)"
            className="md:hidden"
          >
            {leftPanelCollapsed ? "show cloud" : "hide cloud"}
          </HeaderActionButton>

          <HeaderActionButton
            onClick={() => setRightPanelCollapsed(prev => !prev)}
            title="Toggle Metadata Pipeline"
            className="md:hidden"
          >
            {rightPanelCollapsed ? "show pipeline" : "hide pipeline"}
          </HeaderActionButton>

          <CreasesDropdown
            conversations={conversations}
            onNavigateToNotification={handleNavigateToNotification}
          />
          
          <HeaderActionButton to="/agent">
            agent
          </HeaderActionButton>

          <HeaderActionButton to="/research">
            research
          </HeaderActionButton>

          {/* Compact search box in header (desktop) */}
          <form
            onSubmit={(e) => { e.preventDefault(); navigate("/search?q=" + encodeURIComponent((e.currentTarget.elements.namedItem("hq") as HTMLInputElement)?.value || "")) }}
            className="hidden md:flex items-center bg-[#141414] border border-[#2a2a2a] rounded px-2.5 gap-1.5 focus-within:border-emerald-400/40 transition-colors"
          >
            <span className="text-[#555] text-xs select-none">⌕</span>
            <input
              name="hq"
              type="text"
              placeholder="search..."
              className="bg-transparent text-xs text-[#c8c8c8] placeholder-[#555] focus:outline-none w-28 py-1"
            />
          </form>

          {/* Mobile search icon — navigates to /search */}
          <HeaderActionButton
            onClick={() => navigate("/search")}
            title="Search"
            className="md:hidden"
          >
            ⌕
          </HeaderActionButton>

          <HeaderActionButton onClick={handleNewConversation}>
            + new
          </HeaderActionButton>

          {isAuthEnabled && (
            <HeaderActionButton
              onClick={handleLogout}
              className="hover:text-red-500! hidden sm:inline"
            >
              logout
            </HeaderActionButton>
          )}
        </div>
      </HeaderContainer>

      <ConversationTitleBar
        title={conversationTitle}
        onRename={handleRenameTitle}
        onGenerateTitle={handleGenerateTitle}
        variant="mobile"
        conversationId={conversationId}
        onExport={handleExportConversation}
      />

      {/* Workspace Area: Left Panel, NodeExplorer, SidePanel */}
      <div className="flex-1 flex flex-row min-h-0 overflow-hidden relative">
        {/* Backdrop for Left Panel overlay on mobile */}
        {!leftPanelCollapsed && (
          <div
            onClick={() => setLeftPanelCollapsed(true)}
            className="md:hidden fixed inset-0 z-20 bg-black/60 backdrop-blur-xs"
          />
        )}

        {/* Sleek, collapsible Left Panel for Connection Cloud DAG */}
        <div
          className={`
            border-[#222] bg-[#0c0c0c]
            md:border-r md:border-b-0 md:h-full
            flex flex-col shrink-0
            overflow-hidden
            transition-all duration-200
            ${leftPanelCollapsed 
              ? "hidden md:flex md:w-9 md:h-full" 
              : "absolute md:relative z-30 left-0 top-0 bottom-0 w-[85vw] max-w-[340px] md:max-w-none md:w-auto md:h-full md:flex md:z-auto border-r md:border-r-0 bg-[#0c0c0e]/95"
            }
          `}
          style={!leftPanelCollapsed ? { width: `${leftPanelWidth}px` } : undefined}
        >
          {leftPanelCollapsed ? (
            <div className="flex flex-col items-center gap-3 py-3">
              <button
                onClick={() => { setLeftPanelCollapsed(false); setLeftPanelTab("cloud") }}
                title="Connection Cloud"
                className="flex flex-col items-center gap-1 text-[#555] hover:text-[#888] transition-colors cursor-pointer select-none"
              >
                <span className="text-[10px]">▶</span>
                <span className="[writing-mode:vertical-rl] text-[9px] font-mono tracking-wider uppercase">Cloud</span>
              </button>
              <button
                onClick={() => { setLeftPanelCollapsed(false); setLeftPanelTab("search") }}
                title="Search"
                className="flex flex-col items-center gap-1 text-[#555] hover:text-emerald-400 transition-colors cursor-pointer select-none mt-1"
              >
                <span className="text-[12px]">⌕</span>
                <span className="[writing-mode:vertical-rl] text-[9px] font-mono tracking-wider uppercase">Search</span>
              </button>
            </div>
          ) : (
            <>
              {/* Tab bar: Cloud | Search */}
              <div className="flex items-center shrink-0 border-b border-[#222]">
                <button
                  onClick={() => setLeftPanelTab("cloud")}
                  className={`flex-1 text-[9px] font-mono uppercase tracking-wider py-2 transition-colors cursor-pointer border-b-2 ${
                    leftPanelTab === "cloud"
                      ? "text-[#aaa] border-emerald-400"
                      : "text-[#555] border-transparent hover:text-[#888]"
                  }`}
                >
                  Cloud
                </button>
                <button
                  onClick={() => setLeftPanelTab("search")}
                  className={`flex-1 text-[9px] font-mono uppercase tracking-wider py-2 transition-colors cursor-pointer border-b-2 ${
                    leftPanelTab === "search"
                      ? "text-emerald-400 border-emerald-400"
                      : "text-[#555] border-transparent hover:text-[#888]"
                  }`}
                >
                  ⌕ Search
                </button>
                <button
                  onClick={() => setLeftPanelCollapsed(true)}
                  className="px-2 py-2 text-[10px] text-[#555] hover:text-[#888] transition-colors cursor-pointer"
                  title="Collapse panel"
                >
                  ◀
                </button>
              </div>

              {/* Cloud tab content */}
              {leftPanelTab === "cloud" && (
                <>
                  {/* DAG — 2/3 height */}
                  <div className="overflow-hidden relative" style={{ flex: 2 }}>
                    {activeId ? (
                      <ConnectionCloud
                        activeLoadedMessages={fullTreeMessages}
                        notes={notes}
                        activeMessageId={activeMessageId}
                        activePathIds={activePathIds}
                        setActiveMessageId={setActiveMessageId}
                        commitProposedBranch={commitProposedBranch}
                        refreshTree={refreshTree}
                        conversationId={activeId}
                        onNavigateToMessage={navigateToMessage}
                        agentFlux={agentFlux}
                        onDeleteMessage={handleDeleteMessage}
                        treeNodes={treeNodes}
                        treeLinks={links}
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full text-[#444] text-[10px] font-mono px-4 text-center select-none">
                        DAG will initialize upon first message inscription
                      </div>
                    )}
                  </div>

                  {/* Spectral Echoes — 1/3 height */}
                  <div className="flex flex-col shrink-0 border-t border-[#222] overflow-y-auto" style={{ flex: 1 }}>
                    <div className="px-3 py-1.5 shrink-0">
                      <span className="text-[9px] font-mono uppercase tracking-wider text-[#555]">Spectral Echoes</span>
                    </div>
                    <div className="flex-1 overflow-y-auto px-2 pb-2">
                      {activeId ? (
                        <SpectralEchoes
                          conversationId={activeId}
                          activeMessageId={activeMessageId}
                          refreshTree={refreshTree}
                        />
                      ) : (
                        <div className="text-[10px] font-mono text-[#333] px-2 select-none">
                          no active node
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}

              {/* Search tab content */}
              {leftPanelTab === "search" && (
                <div className="flex-1 min-h-0 overflow-hidden">
                  <SearchTab
                    conversationId={activeId || null}
                    onNavigateFromSearch={(convId, msgId) => {
                      if (convId !== activeId) {
                        setActiveId(convId, msgId > 0 ? msgId : undefined)
                      } else if (msgId > 0) {
                        navigateToMessage(msgId)
                      }
                      setLeftPanelCollapsed(false)
                    }}
                  />
                </div>
              )}
            </>
          )}
        </div>

        {!leftPanelCollapsed && (
          <div
            onMouseDown={handleResizeStart}
            className="w-1 cursor-col-resize hover:bg-action-hover/20 active:bg-action-hover/40 transition-colors shrink-0 hidden md:block"
          />
        )}

        {/* Main node explorer interface */}
        <NodeExplorer
          selectedNode={selectedNode}
          parentNode={parentNode}
          siblingNodes={siblingNodes}
          childNodes={childNodes}
          treeNodes={treeNodes}
          loading={loading}
          error={error}
          agentName={agentName}
          conversationId={conversationId}
          uploadedFiles={uploadedFiles}
          onSend={handleSend}
          onUploadFiles={handleUploadFiles}
          isIndexing={isIndexing}
          onClearError={clearError}
          onRegenerate={regenerate}
          notes={notes}
          onAddNote={handleAddNote}
          onDeleteNote={handleDeleteNote}
          onUpdateNote={handleUpdateNote}
          tags={(activeConv?.tags ?? EMPTY_STRING_ARRAY) as any}
          onAddTag={handleAddTag}
          onNavigateToMessage={navigateToMessage}
          className="flex-1 min-w-0"
          history={history}
          onDeleteMessage={agentFlux ? handleDeleteMessage : undefined}
        />

        {/* Backdrop for Right Panel overlay on mobile */}
        {!rightPanelCollapsed && (
          <div
            onClick={() => setRightPanelCollapsed(true)}
            className="md:hidden fixed inset-0 z-20 bg-black/60 backdrop-blur-xs"
          />
        )}

        {/* Resizer handle for SidePanel */}
        {!rightPanelCollapsed && (
          <div
            onMouseDown={handleRightResizeStart}
            className="w-1 cursor-col-resize hover:bg-action-hover/20 active:bg-action-hover/40 transition-colors shrink-0 hidden md:block"
          />
        )}

        {/* Right side panel */}
        <SidePanel
          uploadedFiles={uploadedFiles}
          conversationId={conversationId}
          onDeleteFile={handleDeleteFile}
          onReprocessFile={handleReprocessFile}
          onUploadFiles={handleUploadFiles}
          messageCount={messages.length}
          notes={notes}
          onDeleteNote={handleDeleteNote}
          onUpdateNote={handleUpdateNote}
          summary={activeConv?.summary}
          humanSummary={activeConv?.human_summary}
          width={rightPanelWidth}
          panelCollapsed={rightPanelCollapsed}
          onPanelToggle={() => setRightPanelCollapsed(p => !p)}
          onNavigateNode={handleNavigateNode}
        />
      </div>
      <UnifiedFooter />
    </div>
  )
}
