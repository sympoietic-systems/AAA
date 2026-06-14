import { useState, useEffect, useCallback, memo } from "react"
import { getNotifications, dismissNotification, markNotificationRead, clearNotifications } from "../../../api/client"
import type { SedimentNotification } from "../../../api/client"
import { syncNotifications } from "../../../stores/notificationStore"

interface Props {
  onNavigateToEntity?: (type: string, id: string) => void
}

export const TracesSection = memo(function TracesSection({ onNavigateToEntity }: Props) {
  const [notifications, setNotifications] = useState<SedimentNotification[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [typeFilter, setTypeFilter] = useState<'all' | 'sediment' | 'glitch' | 'trace'>('all')
  const [viewFilter, setViewFilter] = useState<'all' | 'active' | 'dismissed'>('all')

  const fetchTraces = useCallback(async () => {
    setLoading(true)
    try {
      const isDismissed = viewFilter === 'all' ? undefined : (viewFilter === 'dismissed')
      const type = typeFilter === 'all' ? undefined : typeFilter
      const list = await getNotifications(isDismissed, 150, type, search || undefined)
      setNotifications(list)
    } catch (err) { console.error("Failed to load historical traces:", err) }
    finally { setLoading(false) }
  }, [typeFilter, viewFilter, search])

  useEffect(() => { fetchTraces() }, [fetchTraces])

  const handleDismiss = async (id: string) => {
    try {
      await dismissNotification(id)
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, dismissed: true } : n))
      syncNotifications()
    } catch (err) { console.error("Failed to dismiss trace:", err) }
  }

  const handleMarkRead = async (id: string) => {
    try {
      await markNotificationRead(id)
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
      syncNotifications()
    } catch (err) { console.error("Failed to mark trace read:", err) }
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
    try { await clearNotifications(typeFilter === 'all' ? undefined : typeFilter); fetchTraces(); syncNotifications() }
    catch (err) { console.error("Failed to fold active traces:", err) }
  }

  const formatTimestamp = (ts: string) => {
    try { return new Date(ts).toISOString().replace("T", " ").substring(0, 19) } catch { return ts }
  }

  const typeColor = (t: string) => t === "glitch" ? "#f43f5e" : t === "sediment" ? "#e09b67" : "#38bdf8"

  return (
    <div className="flex flex-col h-full font-mono text-[11px] leading-relaxed text-[#bbb] px-4 py-2">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-3">
        <div>
          <span className="text-[13px] text-[#eee] font-bold tracking-wider">sedimentary traces</span>
          <span className="text-[10px] text-[#666] ml-2">geological log of system transitions</span>
        </div>
        <div className="flex items-center gap-2">
          <input type="text" placeholder="search..." value={search} onChange={e => setSearch(e.target.value)}
            className="bg-[#0c0c0e] border border-[#222] text-[#eee] px-2 py-1 rounded-sm w-40 focus:outline-none focus:border-[#444] transition-colors" />
          <button onClick={handleFoldAll}
            className="text-[10px] text-[#666] hover:text-[#e09b67] cursor-pointer select-none">[fold active]</button>
        </div>
      </div>

      {/* Filter tabs — terminal-style */}
      <div className="flex flex-wrap gap-x-3 gap-y-1 pb-2 text-[10px] select-none">
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
        {(['all', 'active', 'dismissed'] as const).map((v, i) => (
          <span key={v} className="flex items-center gap-x-2">
            {true && <span className="text-[#333]">•</span>}
            <button onClick={() => setViewFilter(v)}
              className={`cursor-pointer transition-colors ${viewFilter === v ? "text-[#94a3b8]" : "text-[#444] hover:text-[#777]"}`}>
              {v}
            </button>
          </span>
        ))}
      </div>

      {/* Trace list */}
      <div className="flex-1 overflow-y-auto pr-1 min-h-[300px]">
        {loading && notifications.length === 0 ? (
          <div className="text-center py-20 text-[#555] animate-pulse">hydrating sedimentary layer...</div>
        ) : notifications.length === 0 ? (
          <div className="text-center py-20 text-[#555] italic">No traces matched this slice.</div>
        ) : (
          <div className="space-y-2">
            {notifications.map(n => {
              const color = typeColor(n.type)
              return (
                <div key={n.id} className="group flex items-start gap-3 text-[10px]">
                  <span className="mt-0.5 shrink-0" style={{ color }}>
                    {n.read ? "◆" : "◈"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                      <span className="text-[#666]">{formatTimestamp(n.timestamp)}</span>
                      {n.source && <span className="text-[#555]">{n.source}</span>}
                      <span className="text-[8px] font-bold" style={{ color }}>{n.type}</span>
                      {n.dismissed && <span className="text-[#444] text-[8px]">folded</span>}
                      {!n.read && <span className="text-[#e09b67] text-[8px] font-bold">unread</span>}
                    </div>
                    <div className="text-[#eee] mt-0.5 break-words select-text">{n.snippet}</div>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity self-center shrink-0">
                    {(n.sourceType === "belief" || n.sourceType === "skill" || n.sourceType === "conversation" || !!n.conversationId) && (
                      <button onClick={() => handleJump(n)} className="text-[9px] text-[#666] hover:text-[#4ade80] cursor-pointer select-none">[jump]</button>
                    )}
                    {!n.read && <button onClick={() => handleMarkRead(n.id)} className="text-[9px] text-[#666] hover:text-[#eee] cursor-pointer select-none">[read]</button>}
                    {!n.dismissed && <button onClick={() => handleDismiss(n.id)} className="text-[9px] text-[#666] hover:text-[#ef4444] cursor-pointer select-none">[fold]</button>}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
})
