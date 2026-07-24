import { useState, useMemo, memo } from "react"

export type DailyIndexItem = {

  date: string
  has_conversations: boolean
  message_count: number
  memory_node_count: number
  research_task_count: number
  evolution_count: number
  has_summary: boolean
}


interface CalendarPickerProps {
  dates: DailyIndexItem[]
  selectedDate: string
  onSelectDate: (date: string) => void
  isLoading?: boolean
}

export const CalendarPicker = memo(function CalendarPicker({
  dates,
  selectedDate,
  onSelectDate,
  isLoading,
}: CalendarPickerProps) {
  // Derive current month/year view from selectedDate or today
  const [viewDate, setViewDate] = useState<Date>(() => {
    if (selectedDate && /^\d{4}-\d{2}-\d{2}$/.test(selectedDate)) {
      const [y, m, d] = selectedDate.split("-").map(Number)
      return new Date(y, m - 1, d)
    }
    const d = new Date()
    d.setDate(d.getDate() - 1) // default yesterday
    return d
  })

  // Lookup map for fast date info retrieval
  const dateMap = useMemo(() => {
    const map = new Map<string, DailyIndexItem>()
    for (const item of dates) {
      map.set(item.date, item)
    }
    return map
  }, [dates])

  const year = viewDate.getFullYear()
  const month = viewDate.getMonth()

  // Generate calendar grid for month
  const calendarGrid = useMemo(() => {
    const firstDayOfMonth = new Date(year, month, 1)
    const startingDayOfWeek = firstDayOfMonth.getDay() // 0 = Sun
    const daysInMonth = new Date(year, month + 1, 0).getDate()

    const grid: ({ day: number; dateStr: string } | null)[] = []
    for (let i = 0; i < startingDayOfWeek; i++) {
      grid.push(null)
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const mm = String(month + 1).padStart(2, "0")
      const dd = String(d).padStart(2, "0")
      grid.push({ day: d, dateStr: `${year}-${mm}-${dd}` })
    }
    return grid
  }, [year, month])

  const handlePrevMonth = () => {
    setViewDate(new Date(year, month - 1, 1))
  }

  const handleNextMonth = () => {
    setViewDate(new Date(year, month + 1, 1))
  }

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ]

  return (
    <div className="flex flex-col space-y-4 font-mono text-[11px] select-none pr-2">
      {/* Calendar Card View */}
      <div className="border border-[#222] p-3 space-y-3">
        {/* Month Header */}
        <div className="flex items-center justify-between text-[#8a7d74] text-[10px] uppercase tracking-wider">
          <span>{monthNames[month]} {year}</span>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrevMonth}
              className="text-[#666] hover:text-[#ccc] transition-colors cursor-pointer px-1"
              title="Previous Month"
            >
              &lt;
            </button>
            <button
              onClick={handleNextMonth}
              className="text-[#666] hover:text-[#ccc] transition-colors cursor-pointer px-1"
              title="Next Month"
            >
              &gt;
            </button>
          </div>
        </div>

        {/* Days of Week */}
        <div className="grid grid-cols-7 gap-1 text-center text-[9px] text-[#444] font-semibold uppercase">
          <span>Su</span><span>Mo</span><span>Tu</span><span>We</span><span>Th</span><span>Fr</span><span>Sa</span>
        </div>

        {/* Month Grid */}
        <div className="grid grid-cols-7 gap-1 text-center">
          {calendarGrid.map((cell, idx) => {
            if (!cell) {
              return <div key={`empty-${idx}`} className="h-6" />
            }

            const info = dateMap.get(cell.dateStr)
            const isSelected = cell.dateStr === selectedDate
            const hasActivity = !!info
            const hasSummary = info?.has_summary

            let dayClasses = "h-6 flex flex-col items-center justify-center cursor-pointer transition-colors text-[10px] relative "
            if (isSelected) {
              dayClasses += "border border-action-hover bg-action-hover/10 text-ui-primary font-bold "
            } else if (hasActivity) {
              dayClasses += "text-[#ccc] hover:bg-[#181818] "
            } else {
              dayClasses += "text-[#444] hover:text-[#666] "
            }

            return (
              <button
                key={cell.dateStr}
                onClick={() => onSelectDate(cell.dateStr)}
                className={dayClasses}
              >
                <span>{cell.day}</span>
                {/* Indicator dots */}
                {hasActivity && (
                  <span className="absolute bottom-0.5 flex gap-0.5 items-center">
                    {hasSummary ? (
                      <span className="text-[7px] text-semantic-green leading-none">★</span>
                    ) : (
                      <span className="w-1 h-1 rounded-full bg-semantic-blue" />
                    )}
                  </span>
                )}
              </button>
            )
          })}
        </div>

        {/* Legend */}
        <div className="flex items-center justify-between text-[9px] text-[#555] pt-1 border-t border-[#1a1a1a]">
          <span className="flex items-center gap-1">
            <span className="text-semantic-green text-[9px]">★</span> Summarized
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-semantic-blue" /> Active Logs
          </span>
        </div>
      </div>

      {/* Active Days List */}
      <div className="space-y-1.5">
        <div className="text-[#8a7d74] text-[9px] uppercase tracking-wider flex items-center justify-between">
          <span>Active Days Index</span>
          <span className="text-[#444]">({dates.length})</span>
        </div>

        {isLoading ? (
          <div className="text-[#555] animate-pulse py-2 text-[10px]">Loading daily index...</div>
        ) : dates.length === 0 ? (
          <div className="text-[#444] italic text-[10px] py-2">No active logs recorded yet.</div>
        ) : (
          <div className="space-y-1 max-h-[300px] overflow-y-auto pr-1">
            {dates.map((item) => {
              const isSelected = item.date === selectedDate
              return (
                <button
                  key={item.date}
                  onClick={() => onSelectDate(item.date)}
                  className={`w-full flex items-center justify-between p-1.5 text-left border-l-2 transition-colors cursor-pointer ${
                    isSelected
                      ? "border-action-hover bg-action-hover/5 text-[#eee]"
                      : "border-transparent text-[#bbb] hover:bg-[#111]"
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    {item.has_summary ? (
                      <span className="text-semantic-green text-[10px] shrink-0" title="Summarized">★</span>
                    ) : (
                      <span className="w-1.5 h-1.5 rounded-full bg-semantic-blue shrink-0" title="Active logs" />
                    )}
                    <span className="font-mono text-[11px] shrink-0">{item.date}</span>
                  </div>

                  <div className="flex items-center gap-2 text-[9px] font-mono text-[#555]">
                    {item.message_count > 0 && <span>msgs:{item.message_count}</span>}
                    {item.memory_node_count > 0 && <span className="text-semantic-blue">nodes:{item.memory_node_count}</span>}
                    {item.evolution_count > 0 && <span className="text-semantic-green">evo:{item.evolution_count}</span>}
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
})
