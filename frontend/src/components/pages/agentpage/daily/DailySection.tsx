import { useState, useEffect, useCallback, memo } from "react"
import { CalendarPicker, type DailyIndexItem } from "./CalendarPicker"
import { DailyDetailPanel, type DailyDetail } from "./DailyDetailPanel"


function getYesterdayDateStr(): string {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, "0")
  const dd = String(d.getDate()).padStart(2, "0")
  return `${yyyy}-${mm}-${dd}`
}

export const DailySection = memo(function DailySection() {
  const [indexDates, setIndexDates] = useState<DailyIndexItem[]>([])
  const [isIndexLoading, setIsIndexLoading] = useState<boolean>(true)

  const [selectedDate, setSelectedDate] = useState<string>(() => {
    const params = new URLSearchParams(window.location.search)
    const d = params.get("date")
    if (d && /^\d{4}-\d{2}-\d{2}$/.test(d)) return d
    return getYesterdayDateStr()
  })

  const [activeSubTab, setActiveSubTab] = useState<string>(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get("sub") || "summary"
  })

  const [dailyDetail, setDailyDetail] = useState<DailyDetail | null>(null)
  const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false)
  const [isGeneratingSummary, setIsGeneratingSummary] = useState<boolean>(false)

  // 1. Fetch Daily Index
  const fetchIndex = useCallback(async () => {
    setIsIndexLoading(true)
    try {
      const res = await fetch("/api/agent/daily/index")
      if (res.ok) {
        const data = await res.json()
        setIndexDates(data.dates || [])
      }
    } catch (e) {
      console.error("Failed to fetch daily index:", e)
    } finally {
      setIsIndexLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchIndex()
  }, [fetchIndex])

  // 2. Fetch Daily Details for selectedDate
  const fetchDetail = useCallback(async (dateStr: string) => {
    if (!dateStr) return
    setIsDetailLoading(true)
    try {
      const res = await fetch(`/api/agent/daily/${dateStr}`)
      if (res.ok) {
        const data = await res.json()
        setDailyDetail(data)
      }
    } catch (e) {
      console.error("Failed to fetch daily detail:", e)
    } finally {
      setIsDetailLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDetail(selectedDate)
  }, [selectedDate, fetchDetail])

  // 3. Sync State to URL Query Parameters
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    params.set("tab", "daily")
    params.set("date", selectedDate)
    params.set("sub", activeSubTab)
    const newUrl = `${window.location.pathname}?${params.toString()}`
    window.history.replaceState(null, "", newUrl)
  }, [selectedDate, activeSubTab])

  // 4. Generate Summary Handler
  const handleGenerateSummary = async () => {
    if (!selectedDate || isGeneratingSummary) return
    setIsGeneratingSummary(true)
    try {
      const res = await fetch(`/api/agent/daily/${selectedDate}/summarize`, {
        method: "POST",
      })
      if (res.ok) {
        const data = await res.json()
        setDailyDetail((prev) => (prev ? { ...prev, summary: data.summary } : null))
        // Refresh index to update calendar summary indicator badge
        fetchIndex()
      }
    } catch (e) {
      console.error("Failed to generate daily summary:", e)
    } finally {
      setIsGeneratingSummary(false)
    }
  }

  const handleSelectDate = (d: string) => {
    setSelectedDate(d)
  }

  return (
    <div className="flex flex-col md:flex-row gap-6 h-full w-full">
      {/* Left Column: Calendar & Date Index (md:w-[450px]) */}
      <div className="md:w-[450px] shrink-0 w-full">
        <CalendarPicker
          dates={indexDates}
          selectedDate={selectedDate}
          onSelectDate={handleSelectDate}
          isLoading={isIndexLoading}
        />
      </div>

      {/* Right Column: Daily Details & Subtabs (flex-1) */}
      <DailyDetailPanel
        detail={dailyDetail}
        activeSubTab={activeSubTab}
        onSubTabChange={setActiveSubTab}
        onGenerateSummary={handleGenerateSummary}
        isGeneratingSummary={isGeneratingSummary}
        isLoading={isDetailLoading}
      />
    </div>
  )
})
