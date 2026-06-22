import React, { memo } from "react"

interface TwoPanelLayoutProps {
  left: React.ReactNode
  right: React.ReactNode
}

export const TwoPanelLayout = memo(function TwoPanelLayout({ left, right }: TwoPanelLayoutProps) {
  return (
    <div className="flex flex-col md:flex-row gap-3 flex-1 min-h-0 h-full">
      <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0 md:h-full max-h-[40vh] md:max-h-none">
        {left}
      </div>
      <div className="flex-1 min-w-0 w-full flex flex-col min-h-0 md:h-full overflow-y-auto">
        {right}
      </div>
    </div>
  )
})
