import { useState, useEffect, useCallback, memo, useRef } from "react"
import { getNotification, getNotifications, dismissNotification, markNotificationRead, markNotificationUnread, clearNotifications, markAllNotificationsRead } from "../../../api/client"
import type { SedimentNotification } from "../../../api/client"
import { syncNotifications } from "../../../stores/notificationStore"
import { formatTimestamp } from "../../../utils/dateFormat"

interface Props {
  onNavigateToEntity?: (type: string, id: string) => void
}

export const TracesSection = memo(function TracesSection({ onNavigateToEntity }: Props) {
  const [notifications, setNotifications] = useState<SedimentNotification[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [typeFilter, setTypeFilter] = useState<'all' | 'sediment' | 'glitch' | 'trace'>('all')
  const [viewFilter, setViewFilter] = useState<'all' | 'unread' | 'read'>('unread')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detailTrace, setDetailTrace] = useState<SedimentNotification | null>(null)
  const [, setDetailLoading] = useState(false)
  const detailRef = useRef<HTMLDivElement>(null)

  // Lazy-load full trace detail when selected
  useEffect(() => {
    if (!selectedId) {
      setDetailTrace(null)
      return
    }
    let cancelled = false
    setDetailLoading(true)
    getNotification(selectedId)
      .then(t => { if (!cancelled) { setDetailTrace(t); setDetailLoading(false) } })
      .catch(() => { if (!cancelled) setDetailLoading(false) })
    return () => { cancelled = true }
  }, [selectedId])

  const fetchTraces = useCallback(async () => {
    setLoading(true)
    try {
      // Fetch all (up to limit) and filter by read state client-side
      // Backend only supports filtering by dismissed, not read, so we handle read filtering here
      const type = typeFilter === 'all' ? undefined : typeFilter
      const list = await getNotifications(undefined, 150, type, search || undefined)
      // Client-side filter by read state only
      if (viewFilter === 'unread') {
        setNotifications(list.filter(n => !n.read))
      } else if (viewFilter === 'read') {
        setNotifications(list.filter(n => n.read))
      } else {
        setNotifications(list)
      }
    } catch (err) { console.error("Failed to load historical traces:", err) }
    finally { setLoading(false) }
  }, [typeFilter, viewFilter, search])

  useEffect(() => { fetchTraces() }, [fetchTraces])

  const updateAndKeepSelection = (updater: (prev: SedimentNotification[]) => SedimentNotification[]) => {
    setNotifications(prev => {
      const next = updater(prev)
      // If selected item was removed, update selection to first available
      if (selectedId && !next.find(n => n.id === selectedId)) {
        setSelectedId(next.length > 0 ? next[0].id : null)
      }
      return next
    })
  }

  const handleDismiss = async (id: string) => {
    try {
      await dismissNotification(id)
      await markNotificationRead(id)
      if (viewFilter === 'unread') {
        updateAndKeepSelection(prev => prev.filter(n => n.id !== id))
      } else {
        updateAndKeepSelection(prev => prev.map(n => n.id === id ? { ...n, dismissed: true, read: true } : n))
      }
      syncNotifications()
    } catch (err) { console.error("Failed to dismiss trace:", err) }
  }

  const handleMarkRead = async (id: string) => {
    try {
      await markNotificationRead(id)
      if (viewFilter === 'unread') {
        updateAndKeepSelection(prev => prev.filter(n => n.id !== id))
      } else {
        updateAndKeepSelection(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
      }
      syncNotifications()
    } catch (err) { console.error("Failed to mark trace read:", err) }
  }

  const handleToggleRead = async (n: SedimentNotification) => {
    if (n.read) {
      try {
        await markNotificationUnread(n.id)
        if (viewFilter === 'read') {
          updateAndKeepSelection(prev => prev.filter(x => x.id !== n.id))
        } else {
          updateAndKeepSelection(prev => prev.map(x => x.id === n.id ? { ...x, read: false } : x))
        }
        syncNotifications()
      } catch (err) { console.error("Failed to mark trace unread:", err) }
    } else {
      handleMarkRead(n.id)
    }
  }

  const handleJump = (n: SedimentNotification) => {
    if (!n.read) handleMarkRead(n.id)
    if (onNavigateToEntity && (n.sourceType === "belief" || n.sourceType === "skill")) {
      if (n.sourceId) onNavigateToEntity(n.sourceType, n.sourceId)
    } else if (n.sourceType === "belief" || n.sourceType === "skill") {
      window.open(`/agent?tab=${n.sourceType}s&id=${n.sourceId || ""}`, "_blank")
    } else if (n.sourceType === "conversation" || n.conversationId) {
      const convId = n.sourceId || n.conversationId
      if (convId) window.open(`/?c=${convId}${n.messageId ? `&m=${n.messageId}` : ""}`, "_blank")
    }
  }

  const handleFoldAll = async () => {
    try {
      await clearNotifications(typeFilter === 'all' ? undefined : typeFilter)
      if (viewFilter === 'unread') {
        setNotifications([])
      } else {
        setNotifications(prev => prev.map(n => ({ ...n, dismissed: true, read: true })))
      }
      syncNotifications()
    } catch (err) { console.error("Failed to fold active traces:", err) }
  }

  const handleReadAll = async () => {
    try {
      await markAllNotificationsRead(typeFilter === 'all' ? undefined : typeFilter)
      // If viewing "unread", clear the list instantly; otherwise re-fetch
      if (viewFilter === 'unread') {
        setNotifications([])
      } else {
        setNotifications(prev => prev.map(n => ({ ...n, read: true })))
      }
      syncNotifications()
    } catch (err) { console.error("Failed to mark all read:", err) }
  }

  const typeColor = (t: string) => t === "glitch" ? "#f43f5e" : t === "sediment" ? "#e09b67" : "#38bdf8"
  const typeIcon = (t: string) => t === "glitch" ? "✖" : t === "sediment" ? "◆" : "◇"
  const typeLabel = (t: string) => t === "glitch" ? "Glitch" : t === "sediment" ? "Sediment" : "Trace"

  const selectedTrace = detailTrace

  const handleListClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-trace-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-trace-id")
    if (id) setSelectedId(prev => prev === id ? null : id)
  }

  return (
    <div className="flex flex-col h-full font-mono text-[11px] leading-relaxed text-[#bbb]">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 px-4 pt-2 pb-3">
        <div>
          <span className="text-[13px] text-[#eee] font-bold tracking-wider">sedimentary traces</span>
          <span className="text-[10px] text-[#666] ml-2">geological log of system transitions</span>
        </div>
      </div>

      {/* Search + bulk actions */}
      <div className="flex items-center gap-2 px-4 pb-3">
        <div className="flex-1 relative">
          <input type="text" placeholder="search traces..." value={search} onChange={e => setSearch(e.target.value)}
            className="w-full bg-[#0c0c0e] border border-[#222] text-[#eee] text-[10px] px-2 py-1 rounded-sm focus:outline-none focus:border-[#444] transition-colors" />
        </div>
        <button onClick={handleReadAll}
          className="text-[10px] text-[#555] hover:text-[#eee] cursor-pointer select-none shrink-0">[read all]</button>
        <button onClick={handleFoldAll}
          className="text-[10px] text-[#555] hover:text-[#e09b67] cursor-pointer select-none shrink-0">[fold all]</button>
      </div>

      {/* Filter tabs — terminal-style */}
      <div className="flex flex-wrap gap-x-3 gap-y-1 px-4 pb-2 text-[10px] select-none">
        <span className="text-[#555]">category:</span>
        {(['all', 'sediment', 'glitch', 'trace'] as const).map((t, i) => (
          <span key={t} className="flex items-center gap-x-2">
            {i > 0 && <span className="text-[#333]">•</span>}
            <button onClick={() => setTypeFilter(t)}
              className={`cursor-pointer transition-colors ${typeFilter === t ? "text-[#94a3b8]" : "text-[#444] hover:text-[#777]"}`}>
              {t}
            </button>
          </span>
        ))}
        <span className="text-[#555] ml-3">state:</span>
        {(['all', 'unread', 'read'] as const).map((v) => (
          <span key={v} className="flex items-center gap-x-2">
            {true && <span className="text-[#333]">•</span>}
            <button onClick={() => setViewFilter(v)}
              className={`cursor-pointer transition-colors ${viewFilter === v ? "text-[#94a3b8]" : "text-[#444] hover:text-[#777]"}`}>
              {v}
            </button>
          </span>
        ))}
      </div>

      {/* Two-panel: left list + right detail */}
      <div className="flex flex-col md:flex-row gap-0 md:gap-3 flex-1 min-h-0 px-4 pb-2">
        {/* ── Left: scrollable list ── */}
        <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto pr-1 min-h-[200px]" onClick={handleListClick}>
            {loading && notifications.length === 0 ? (
              <div className="text-center py-20 text-[#555] animate-pulse">hydrating sedimentary layer...</div>
            ) : notifications.length === 0 ? (
              <div className="text-center py-20 text-[#555] italic">No traces matched this slice.</div>
            ) : (
              <div className="space-y-0.5">
                {notifications.map(n => {
                  const color = typeColor(n.type)
                  const icon = typeIcon(n.type)
                  const isSelected = n.id === selectedId
                  return (
                    <div
                      key={n.id}
                      data-trace-id={n.id}
                      className={`flex items-center gap-1.5 text-[10px] py-0.5 px-1 cursor-pointer font-mono transition-colors ${
                        isSelected ? "text-[#ccc]" : "text-[#555] hover:text-[#888]"
                      }`}
                    >
                      <span
                        className="shrink-0 select-none text-[11px]"
                        style={{ color }}
                        onClick={(e) => { e.stopPropagation(); handleToggleRead(n) }}
                        title={n.read ? "mark unread" : "mark read"}
                      >{icon}</span>
                      <span className="shrink-0 text-[#666]">{formatTimestamp(n.timestamp)}</span>
                      {n.source && <span className="truncate min-w-0">{n.source}</span>}
                      {!n.dismissed && (
                        <button onClick={(e) => { e.stopPropagation(); handleDismiss(n.id) }} className="shrink-0 text-[#555] hover:text-[#ef4444] cursor-pointer select-none leading-none ml-auto">[fold]</button>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* ── Right: Detail panel ── */}
        <div ref={detailRef} className="flex-1 min-w-0 w-full mt-3 md:mt-0 md:flex md:flex-col md:min-h-0">
          {!selectedTrace ? (
            <div className="flex-1 min-h-0 flex items-center justify-center">
              <span className="text-[11px] text-[#444] italic font-mono">select a log record</span>
            </div>
          ) : (() => {
            const t = selectedTrace
            const color = typeColor(t.type)
            return (
              <div className="flex-1 min-h-0 flex flex-col overflow-y-auto pr-1.5 gap-2 text-[11px]">
                {/* Header with actions */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 flex-wrap min-w-0">
                    <span className="text-[11px] shrink-0" style={{ color }}>{typeIcon(t.type)}</span>
                    <span className="text-[#a78bfa] text-[12px] font-bold font-mono tracking-tight">{typeLabel(t.type)} trace</span>
                    <span className="text-[#555] text-[9px] font-mono">{t.read ? "read" : "unread"}</span>
                    {t.dismissed && <span className="text-[#444] text-[9px] font-mono">· folded</span>}
                    {(t.sourceType === "belief" || t.sourceType === "skill" || t.sourceType === "conversation" || !!t.conversationId) && (
                      <button onClick={() => handleJump(t)} className="text-[10px] text-[#666] hover:text-[#4ade80] transition-colors cursor-pointer select-none font-mono font-bold">[jump]</button>
                    )}
                    <button onClick={() => handleToggleRead(t)} className="text-[10px] text-[#666] hover:text-[#ccc] transition-colors cursor-pointer select-none font-mono font-bold">{t.read ? "[unread]" : "[read]"}</button>
                  </div>
                  {!t.dismissed && (
                    <button onClick={() => handleDismiss(t.id)} className="shrink-0 text-[10px] text-[#666] hover:text-[#ef4444] transition-colors cursor-pointer select-none font-mono font-bold">[fold]</button>
                  )}
                </div>

                {/* Message — full text, no wrapper */}
                <div className="text-[#ccc] leading-relaxed whitespace-pre-wrap break-words">{t.snippet}</div>

                {/* Metadata + links — single inline line */}
                <div className="text-[10px]">
                  <span className="text-[#555]">{formatTimestamp(t.timestamp)}</span>
                  {t.source && <span className="text-[#555]"> · {t.source}</span>}
                  {t.speaker && <span className="text-[#555]"> · {t.speaker}</span>}
                  {t.sourceType && <span className="text-[#555]"> · {t.sourceType}{t.sourceId ? `:${t.sourceId}` : ""}</span>}
                  {t.conversationId && <span className="text-[#555]"> · {t.conversationId}{t.messageId ? `#${t.messageId}` : ""}</span>}
                  {/* Links */}
                  {(t.sourceType || t.conversationId) && (
                    <span>
                      {(t.sourceType === "belief" || t.sourceType === "skill") && t.sourceId && (
                        <button onClick={() => handleJump(t)} className="text-[#a78bfa] hover:underline cursor-pointer select-none font-mono ml-1">[{t.sourceType}]</button>
                      )}
                      {(t.sourceType === "conversation" || t.conversationId) && (
                        <button onClick={() => handleJump(t)} className="text-[#a78bfa] hover:underline cursor-pointer select-none font-mono ml-1">[conv]</button>
                      )}
                    </span>
                  )}
                </div>
              </div>
            )
          })()}
        </div>
      </div>
    </div>
  )
})
