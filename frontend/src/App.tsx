import { useState, useEffect, lazy, Suspense, useCallback } from "react"
import { Routes, Route, Navigate, useNavigate, useSearchParams } from "react-router-dom"
import { checkAuthStatus, verifyPassword, logout, getAgent } from "./api/client"
import type { AuthCheckResult } from "./api/auth"

const TeaserPreview = lazy(() => import("./components/TeaserPreview").then(m => ({ default: m.TeaserPreview })))
const LoginPage = lazy(() => import("./components/pages/login/LoginPage").then(m => ({ default: m.LoginPage })))
const AgentPage = lazy(() => import("./components/pages/agentpage/AgentPage").then(m => ({ default: m.AgentPage })))
const ResearchPage = lazy(() => import("./components/pages/researchpage/ResearchPage").then(m => ({ default: m.ResearchPage })))
const ResearchTaskPage = lazy(() => import("./components/pages/researchpage/ResearchTaskPage").then(m => ({ default: m.ResearchTaskPage })))
const SearchPage = lazy(() => import("./components/pages/search/SearchPage").then(m => ({ default: m.SearchPage })))
const NodesPage = lazy(() => import("./components/pages/nodeexplorer/NodesPage").then(m => ({ default: m.NodesPage })))

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-screen bg-[#0c0c0c] text-sm font-mono text-[#555] select-none">
      <span className="animate-pulse">loading...</span>
    </div>
  )
}

export default function App() {
  const [authState, setAuthState] = useState<AuthCheckResult>({ status: "checking", authenticated: false, authEnabled: true })
  const [authError, setAuthError] = useState<string | null>(null)
  const [agentFlux, setAgentFlux] = useState<boolean>(false)
  const navigate = useNavigate()

  const verifyStatus = useCallback(() => {
    setAuthState({ status: "checking", authenticated: false, authEnabled: true })
    checkAuthStatus().then((status) => {
      setAuthState(status)
      if (status.authenticated || !status.authEnabled) {
        getAgent().then(info => setAgentFlux(!!info.agent_flux)).catch(() => setAgentFlux(false))
      }
    })
  }, [])

  useEffect(() => {
    verifyStatus()
  }, [verifyStatus])

  const handlePasswordSubmit = async (password: string) => {
    setAuthError(null)
    const success = await verifyPassword(password)
    if (success) {
      localStorage.setItem("aaa_password", password)
      setAuthState({ status: "authenticated", authenticated: true, authEnabled: true })
      navigate("/nodes")
    } else {
      setAuthError("Incorrect password")
    }
  }

  const handleLogout = () => {
    logout()
    setAuthState({ status: "locked", authenticated: false, authEnabled: true })
    navigate("/")
  }

  if (authState.status === "checking") {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0c0c0c] text-sm font-mono text-[#555] select-none">
        <span className="animate-pulse">initializing system...</span>
      </div>
    )
  }

  if (authState.status === "unavailable") {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-[#0c0c0c] text-mono text-[#888] select-none gap-4">
        <div className="flex items-center gap-2 text-sm text-semantic-gold">
          <span>■</span>
          <span className="tracking-widest uppercase">system gateway unreachable</span>
        </div>
        <p className="text-xs text-[#555] max-w-sm text-center">
          {authState.error || "The backend cognitive service is offline or unreachable."}
        </p>
        <button
          onClick={verifyStatus}
          className="text-xs px-3 py-1.5 border border-[#333] hover:border-action-hover text-action-dim hover:text-action-hover font-mono uppercase tracking-wider transition-colors cursor-pointer"
        >
          [retry connection]
        </button>
      </div>
    )
  }

  const { authenticated, authEnabled } = authState

  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={
          authEnabled && !authenticated
            ? <Navigate to="/login" replace />
            : (<div className="h-screen w-screen overflow-hidden"><TeaserPreview /></div>)
        } />
        <Route path="/login" element={
          !authEnabled || authenticated
            ? <Navigate to="/nodes" replace />
            : <LoginPage onPasswordSubmit={handlePasswordSubmit} authError={authError} onClearError={() => setAuthError(null)} />
        } />
        <Route path="/agent" element={
          authEnabled && !authenticated
            ? <Navigate to="/login" replace />
            : <AgentPage onGoHome={() => navigate("/nodes")} />
        } />
        <Route path="/research" element={
          authEnabled && !authenticated
            ? <Navigate to="/login" replace />
            : <ResearchRouter />
        } />
        <Route path="/nodes" element={
          authEnabled && !authenticated
            ? <Navigate to="/login" replace />
            : (<NodesPage isAuthEnabled={authEnabled} handleLogout={handleLogout} agentFlux={agentFlux} />)
        } />
        <Route path="/search" element={
          authEnabled && !authenticated
            ? <Navigate to="/login" replace />
            : <SearchPage />
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
