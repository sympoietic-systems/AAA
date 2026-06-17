import React, { memo } from "react"

interface TwoPanelLayoutProps {
  left: React.ReactNode
  right: React.ReactNode
}

export const TwoPanelLayout = memo(function TwoPanelLayout({ left, right }: TwoPanelLayoutProps) {
  return (
    <div className="flex flex-col md:flex-row gap-3 md:h-[calc(100vh-200px)]">
      <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0 md:max-h-full max-h-[40vh]">
        {left}
      </div>
      <div className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0 overflow-y-auto">
        {right}
      </div>
    </div>
  )
})
