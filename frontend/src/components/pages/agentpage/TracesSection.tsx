import { useState, useEffect, useCallback } from "react"
import { getNotifications, dismissNotification, markNotificationRead, clearNotifications } from "../../../api/client"
import type { SedimentNotification } from "../../../api/client"
import { syncNotifications } from "../../../stores/notificationStore"

export function TracesSection() {
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
    } catch (err) {
      console.error("Failed to load historical traces:", err)
    } finally {
      setLoading(false)
    }
  }, [typeFilter, viewFilter, search])

  useEffect(() => {
    fetchTraces()
  }, [fetchTraces])

  const handleDismiss = async (id: string) => {
    try {
      await dismissNotification(id)
      // Update local state
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, dismissed: true } : n)
      )
      // Sync global store so creases dropdown gets updated
      syncNotifications()
    } catch (err) {
      console.error("Failed to dismiss trace:", err)
    }
  }

  const handleMarkRead = async (id: string) => {
    try {
      await markNotificationRead(id)
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, read: true } : n)
      )
      syncNotifications()
    } catch (err) {
      console.error("Failed to mark trace read:", err)
    }
  }

  const handleFoldAll = async () => {
    try {
      const type = typeFilter === 'all' ? undefined : typeFilter
      await clearNotifications(type)
      fetchTraces()
      syncNotifications()
    } catch (err) {
      console.error("Failed to fold active traces:", err)
    }
  }

  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts)
      return d.toISOString().replace("T", " ").substring(0, 19)
    } catch {
      return ts
    }
  }

  const getIndicatorStyle = (type: string) => {
    switch (type) {
      case "glitch":
        return { color: "#f43f5e", bg: "bg-[#f43f5e]/10", border: "border-[#f43f5e]/20" }
      case "sediment":
        return { color: "#e09b67", bg: "bg-[#e09b67]/10", border: "border-[#e09b67]/20" }
      case "trace":
      default:
        return { color: "#38bdf8", bg: "bg-[#38bdf8]/10", border: "border-[#38bdf8]/20" }
    }
  }

  return (
    <div className="flex flex-col h-full font-mono text-[11px] leading-relaxed text-[#bbb]">
      {/* Top Header stats & Search bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-[#1a1a1a]">
        <div className="flex flex-col">
          <h2 className="text-[13px] text-[#eee] font-bold tracking-wider">SEDIMENTARY TRACES (ARCHAEOLOGY)</h2>
          <p className="text-[10px] text-[#666] mt-0.5">
            Geological core-sample log of system transitions, message sedimentation, and indexer glitches.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="search traces..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-[#0c0c0e] border border-[#222] text-[#eee] px-2.5 py-1 rounded-sm w-48 md:w-56 focus:outline-none focus:border-[#444] transition-colors"
          />
          <button
            onClick={handleFoldAll}
            className="border border-[#e09b67]/30 text-[#e09b67] bg-[#1a1410] px-2.5 py-1 rounded-sm hover:bg-[#e09b67]/15 hover:border-[#e09b67]/50 transition-colors cursor-pointer select-none"
            title="Archive all active traces shown by the current category"
          >
            fold active
          </button>
        </div>
      </div>

      {/* Control Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-2 py-2.5 border-b border-[#1a1a1a] select-none text-[10px]">
        {/* Category filters */}
        <div className="flex items-center gap-1">
          <span className="text-[#555] mr-1">category:</span>
          {(['all', 'sediment', 'glitch', 'trace'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`px-2 py-0.5 rounded-sm border cursor-pointer transition-all ${
                typeFilter === t
                  ? "bg-[#18181c] text-[#eee] border-[#444]"
                  : "bg-transparent text-[#666] border-transparent hover:text-[#888]"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* View / Fold filters */}
        <div className="flex items-center gap-1">
          <span className="text-[#555] mr-1">state:</span>
          {(['all', 'active', 'dismissed'] as const).map((v) => (
            <button
              key={v}
              onClick={() => setViewFilter(v)}
              className={`px-2 py-0.5 rounded-sm border cursor-pointer transition-all ${
                viewFilter === v
                  ? "bg-[#18181c] text-[#eee] border-[#444]"
                  : "bg-transparent text-[#666] border-transparent hover:text-[#888]"
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {/* Trace Log Timeline */}
      <div className="flex-1 overflow-y-auto pr-1 py-3 custom-scrollbar min-h-[300px]">
        {loading && notifications.length === 0 ? (
          <div className="flex items-center justify-center py-20 text-[#555]">
            <span className="animate-pulse">hydrating sedimentary layer...</span>
          </div>
        ) : notifications.length === 0 ? (
          <div className="text-center py-20 text-[#555] italic">
            No traces matched this slice of geological history.
          </div>
        ) : (
          <div className="space-y-2 relative before:absolute before:left-[19px] before:top-2 before:bottom-2 before:w-[1px] before:bg-[#1a1a1a]">
            {notifications.map((n) => {
              const styles = getIndicatorStyle(n.type)
              return (
                <div
                  key={n.id}
                  className={`group relative flex items-start gap-4 p-2 pl-3 rounded-sm transition-all duration-200 border ${
                    n.read ? "bg-[#070709]/30 border-transparent" : "bg-[#0b0b0e] border-[#222]/30 shadow-md"
                  } hover:bg-[#0f0f13]/60 hover:border-[#333]/40`}
                >
                  {/* Left bullet marker */}
                  <div className="w-4 h-4 mt-0.5 rounded-sm flex items-center justify-center shrink-0 z-10 bg-[#0c0c0e] border border-[#222]">
                    <span
                      className={`text-[8px] leading-none ${n.read ? "opacity-40" : "animate-pulse"}`}
                      style={{ color: styles.color }}
                    >
                      ◆
                    </span>
                  </div>

                  {/* Notification details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px]">
                      <span className="text-[#666]" title="Event occurrence time">
                        {formatTimestamp(n.timestamp)}
                      </span>
                      {n.source && (
                        <span className="text-[#555] px-1 py-px rounded bg-[#111] border border-[#222]/40" title="Source of the event">
                          {n.source}
                        </span>
                      )}
                      <span className="uppercase text-[8px] tracking-wider px-1 font-bold rounded" style={{ color: styles.color, backgroundColor: `${styles.color}15` }}>
                        {n.type}
                      </span>
                      {n.dismissed && (
                        <span className="text-[#444] border border-[#222] text-[8px] px-1 uppercase tracking-wider rounded select-none">
                          folded
                        </span>
                      )}
                      {!n.read && (
                        <span className="text-[#e09b67] text-[8px] uppercase font-bold tracking-wider">
                          unread
                        </span>
                      )}
                    </div>

                    <div className="text-[11px] text-[#eee] mt-1 break-words select-text">
                      {n.snippet}
                    </div>
                  </div>

                  {/* Actions (mark read / dismiss) */}
                  <div className="flex items-center gap-1 opacity-20 group-hover:opacity-100 transition-opacity self-center shrink-0">
                    {!n.read && (
                      <button
                        onClick={() => handleMarkRead(n.id)}
                        className="text-[9px] hover:text-[#eee] border border-[#222] hover:border-[#444] px-1.5 py-0.5 rounded bg-[#0c0c0e] cursor-pointer"
                        title="Mark trace as read"
                      >
                        read
                      </button>
                    )}
                    {!n.dismissed && (
                      <button
                        onClick={() => handleDismiss(n.id)}
                        className="text-[9px] hover:text-[#ef4444] border border-[#222] hover:border-[#ef4444]/30 px-1.5 py-0.5 rounded bg-[#0c0c0e] cursor-pointer"
                        title="Fold away (archive) this trace"
                      >
                        fold
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
