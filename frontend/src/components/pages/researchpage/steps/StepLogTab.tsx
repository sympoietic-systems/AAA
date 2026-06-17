import React, { memo } from "react"
import { LogEntries } from "./LogEntries"

interface StepLogTabProps {
  entries: any[]
  loading: boolean
}

export const StepLogTab = memo(function StepLogTab({ entries, loading }: StepLogTabProps) {
  return <LogEntries entries={entries} loading={loading} emptyMsg="no additional log entries" />
})
