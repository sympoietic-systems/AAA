import { useState, useRef, useEffect, useCallback, lazy, Suspense } from "react"
import { Routes, Route, Navigate, useNavigate, useSearchParams } from "react-router-dom"
import { useChat } from "./hooks/useChat"
import { useConversations } from "./hooks/useConversations"
import { useConversationNotes } from "./hooks/useNotes"
import { dismissByMatch } from "./stores/notificationStore"
import { NodeExplorer } from "./components/pages/nodeexplorer/NodeExplorer"
import { SidePanel } from "./components/panels/sidepanel/SidePanel"
import ConnectionCloud from "./components/panels/leftpanel/ConnectionCloud"
import { SpectralEchoes } from "./components/panels/leftpanel/SpectralEchoes"
import { checkAuthStatus, verifyPassword, logout, addConversationTag, getAgent, deleteMessage, downloadExport } from "./api/client"
import { usePanelResizer } from "./hooks/usePanelResizer"
import { HeaderContainer, HeaderIndicator, HeaderLogo, HeaderSeparator, HeaderLabel, HeaderActionButton, CreasesDropdown, UnifiedFooter } from "./components/UI"
import { ConversationTitleBar } from "./components/shared/ConversationTitleBar"

const TeaserPreview = lazy(() => import("./components/TeaserPreview").then(m => ({ default: m.TeaserPreview })))
const LoginPage = lazy(() => import("./components/pages/login/LoginPage").then(m => ({ default: m.LoginPage })))
const AgentPage = lazy(() => import("./components/pages/agentpage/AgentPage").then(m => ({ default: m.AgentPage })))
const ResearchPage = lazy(() => import("./components/pages/researchpage/ResearchPage").then(m => ({ default: m.ResearchPage })))
const ResearchTaskPage = lazy(() => import("./components/pages/researchpage/ResearchTaskPage").then(m => ({ default: m.ResearchTaskPage })))
const ConversationLandingPage = lazy(() => import("./components/pages/landing/ConversationLandingPage").then(m => ({ default: m.ConversationLandingPage })))

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-screen bg-[#0c0c0c] text-sm font-mono text-[#555] select-none">
      <span className="animate-pulse">loading...</span>
    </div>
  )
}

const EMPTY_STRING_ARRAY: string[] = []

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)
  const [isAuthEnabled, setIsAuthEnabled] = useState<boolean>(false)
  const [authError, setAuthError] = useState<string | null>(null)
  const [agentFlux, setAgentFlux] = useState<boolean>(false)

  useEffect(() => {
    checkAuthStatus().then((status) => {
      setIsAuthenticated(status.authenticated)
      setIsAuthEnabled(status.authEnabled)
      // Only fetch agent info if authenticated (skip 401 on locked page)
      if (status.authenticated || !status.authEnabled) {
        getAgent().then(info => setAgentFlux(!!info.agent_flux)).catch(() => setAgentFlux(false))
      }
    })
  }, [])

  const navigate = useNavigate()

  const handlePasswordSubmit = async (password: string) => {
    setAuthError(null)
    const success = await verifyPassword(password)
    if (success) {
      localStorage.setItem("aaa_password", password)
      setIsAuthenticated(true)
      navigate("/nodes")
    } else {
      setAuthError("Incorrect password")
    }
  }

  const handleLogout = () => {
    logout()
    setIsAuthenticated(false)
    navigate("/")
  }

  if (isAuthenticated === null) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0c0c0c] text-sm font-mono text-[#555] select-none">
        <span className="animate-pulse">initializing system...</span>
      </div>
    )
  }

  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={
          isAuthEnabled && !isAuthenticated
            ? <Navigate to="/login" replace />
            : (<div className="h-screen w-screen overflow-hidden"><TeaserPreview /></div>)
        } />
        <Route path="/login" element={
          !isAuthEnabled || isAuthenticated
            ? <Navigate to="/nodes" replace />
            : <LoginPage onPasswordSubmit={handlePasswordSubmit} authError={authError} onClearError={() => setAuthError(null)} />
        } />
        <Route path="/agent" element={
          isAuthEnabled && !isAuthenticated
            ? <Navigate to="/login" replace />
            : <AgentPage onGoHome={() => navigate("/nodes")} />
        } />
        <Route path="/research" element={
          isAuthEnabled && !isAuthenticated
            ? <Navigate to="/login" replace />
            : <ResearchRouter />
        } />
        <Route path="/nodes" element={
          isAuthEnabled && !isAuthenticated
            ? <Navigate to="/login" replace />
            : (<NodesPage isAuthEnabled={isAuthEnabled} handleLogout={handleLogout} agentFlux={agentFlux} />)
        } />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}

function ResearchRouter() {
  const [searchParams] = useSearchParams()
  const taskId = searchParams.get("id")
  const isNew = taskId === "new"
  if (taskId && !isNew) {
    return <ResearchTaskPage taskId={taskId} />
  }
  if (isNew) {
    return <ResearchTaskPage taskId="" isNew />
  }
  return <ResearchPage />
}

/* --- Subcomponent for /nodes workspace to respect React rules of Hooks --- */

function NodesPage({ isAuthEnabled, handleLogout, agentFlux }: NodesPageProps) {
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

  // Collapsible and resizable left panel state (for Connection Cloud DAG)
  const {
    width: leftPanelWidth,
    collapsed: leftPanelCollapsed,
    setCollapsed: setLeftPanelCollapsed,
    handleResizeStart,
  } = usePanelResizer({
    storageKey: "aaa_leftPanelWidth",
    defaultWidth: 320,
    computeMaxWidth: () => Math.floor(window.innerWidth * 0.5),
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
    computeMaxWidth: () => {
      const maxRight = Math.floor(window.innerWidth * 0.3)
      const minChat = Math.floor(window.innerWidth * 0.3)
      return Math.min(maxRight, window.innerWidth - leftPanelWidth - minChat)
    },
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
          <HeaderLogo href="/nodes" />
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
          
          <HeaderActionButton href="/agent">
            agent
          </HeaderActionButton>

          <HeaderActionButton href="/research">
            research
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
              : "absolute md:relative z-30 left-0 top-0 bottom-0 w-[85vw] max-w-[340px] md:w-auto md:h-full md:flex md:z-auto border-r md:border-r-0 bg-[#0c0c0e]/95"
            }
          `}
          style={!leftPanelCollapsed ? { width: `${leftPanelWidth}px` } : undefined}
        >
          {leftPanelCollapsed ? (
            <button
              onClick={() => setLeftPanelCollapsed(false)}
              className="
                flex items-center gap-1.5 shrink-0
                text-xs text-[#555] hover:text-[#888]
                transition-colors
                md:flex-col md:justify-start md:gap-2 md:py-3 md:px-0
                md:h-full
                select-none cursor-pointer
              "
            >
              <span className="text-[10px]">▶</span>
              <span className="md:[writing-mode:vertical-rl] md:text-[10px] md:tracking-wider text-[11px] font-mono">
                CONNECTION CLOUD
              </span>
            </button>
          ) : (
            <>
              <div className="flex items-center justify-between shrink-0 px-3 py-2 border-b border-[#222]">
                <span className="text-[10px] font-mono uppercase text-[#666]">Connection Cloud</span>
                <button
                  onClick={() => setLeftPanelCollapsed(true)}
                  className="flex items-center gap-1 text-[10px] text-[#555] hover:text-[#888] transition-colors cursor-pointer"
                >
                  <span>◀</span>
                  <span>collapse</span>
                </button>
              </div>

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

              {/* Spectral Echoes — 1/3 height, always open */}
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

        {!rightPanelCollapsed && (
          <div
            onMouseDown={handleRightResizeStart}
            className="w-1 cursor-col-resize hover:bg-action-hover/20 active:bg-action-hover/40 transition-colors shrink-0 hidden md:block"
          />
        )}

        <SidePanel
          uploadedFiles={uploadedFiles}
          conversationId={conversationId}
          onDeleteFile={handleDeleteFile}
          onReprocessFile={handleReprocessFile}
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
