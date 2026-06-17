import React, { memo } from "react"

interface BracketHeaderProps {
  text: string
  className?: string
}

export const BracketHeader = memo(function BracketHeader({ text, className = "" }: BracketHeaderProps) {
  return (
    <div className={`text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1 ${className}`}>
      [{text}]
    </div>
  )
})
