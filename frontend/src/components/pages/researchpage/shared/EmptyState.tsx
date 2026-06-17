import React, { memo } from "react"

interface EmptyStateProps {
  message: string
}

export const EmptyState = memo(function EmptyState({ message }: EmptyStateProps) {
  return (
    <div className="text-[#444] italic text-xs text-center mt-8 select-none">
      [{message}]
    </div>
  )
})
