type DetailTab = "input" | "result" | "log"

export const DETAIL_TABS: DetailTab[] = ["input", "result", "log"]

import React, { memo, useState, useEffect, useMemo } from "react"
import type { MetaLogResponse, TaskStepsResponse, StepPreview } from "../../../../api/research"
import { getTaskMetaLog, getStepPreview, executeStep, reinitializeTask } from "../../../../api/research"
import { TerminalButton } from "../../../UI"
import { STEP_TO_PHASE, STEP_LABELS } from "../constants/taskConstants"
import { StepResultTab } from "./StepResultTab"
import { StepInputTab } from "./StepInputTab"
import { StepLogTab } from "./StepLogTab"

interface DbStepDetailProps {
  taskId: string
  data: TaskStepsResponse | null
  selectedId: string
}

export const DbStepDetail = memo(function DbStepDetail({ taskId, data, selectedId }: DbStepDetailProps) {
  const steps = data ? [...data.steps].reverse() : []
  const selected = steps.find(s => s.id === selectedId)
  if (!selected) return null
  const selectedResults = data ? (data.results_by_step[selectedId] || []) : []
  const [tab, setTab] = useState<DetailTab>("result")
  const [metaLog, setMetaLog] = useState<MetaLogResponse | null>(null)
  const [logLoading, setLogLoading] = useState(false)
  const [liveInput, setLiveInput] = useState<StepPreview | null>(null)
  const [reinitLoading, setReinitLoading] = useState(false)

  const stepPhase = STEP_TO_PHASE[selected.step_type] || ""

  useEffect(() => {
    setLogLoading(true)
    getTaskMetaLog(taskId, selectedId).then(m => { setMetaLog(m); setTab("result") }).catch(() => setMetaLog(null)).finally(() => setLogLoading(false))
  }, [selectedId, taskId])

  const fetchLiveInput = () => {
    if (!stepPhase) return
    setReinitLoading(true)
    getStepPreview(taskId, stepPhase).then(setLiveInput).catch(() => setLiveInput(null)).finally(() => setReinitLoading(false))
  }

  const reinitLiveInput = async () => {
    if (!stepPhase) return
    setReinitLoading(true)
    try {
      await reinitializeTask(taskId)
      const preview = await getStepPreview(taskId, stepPhase)
      setLiveInput(preview)
    } catch { setLiveInput(null) }
    finally { setReinitLoading(false) }
  }

  useEffect(() => { if (tab === "input" && !liveInput) fetchLiveInput() }, [tab])

  const entries = metaLog?.entries ?? []
  const inputEntries = entries.filter(e => {
    const d = e.event_data as any
    return e.event_type.endsWith("_prompt") || e.event_type === "orchestrator_search" ||
      (d && (d.system_prompt || d.user_prompt))
  })
  const responseEntries = entries.filter(e =>
    e.event_type.endsWith("_response") && !e.event_type.endsWith("_prompt")
  )
  const searchEntries = entries.filter(e => e.event_type === "orchestrator_search")
  const otherEntries = entries.filter(e => !inputEntries.includes(e) && !responseEntries.includes(e))

  const parsedResult = useMemo(() => {
    const r: { queries: string[], goal: string, completeness: number, answer: string, confidence: number, learnings: string[], query: string, urls: {url:string,title:string}[] } =
      { queries: [], goal: "", completeness: 0, answer: "", confidence: 0, learnings: [], query: "", urls: [] }
    for (const e of responseEntries) {
      try {
        const d = e.event_data as any
        const raw = d?.raw_response || ""
        let parsed: any = null
        try { parsed = JSON.parse(raw) } catch {
          try { parsed = JSON.parse(d?.response || "") } catch { /* skip */ }
        }
        if (!parsed) continue
        const jd = parsed.json_data || parsed.content || parsed
        if (typeof jd === "string") try { parsed = JSON.parse(jd) } catch { /* skip */ }
        else parsed = jd
        if (typeof parsed !== "object" || !parsed) continue
        if (e.event_type === "orchestrator_plan_response") {
          r.goal = parsed.goal || ""
          r.queries = parsed.search_queries || []
        } else if (e.event_type === "orchestrator_digest_response") {
          if (parsed.learnings) r.learnings.push(...parsed.learnings)
        } else if (e.event_type.includes("reflect_response")) {
          r.completeness = parsed.completeness_score || parsed.completeness || 0
        } else if (e.event_type === "orchestrator_synthesize_response") {
          r.answer = parsed.answer || ""
          r.confidence = parsed.confidence || 0
        }
      } catch { /* skip unparseable */ }
    }
    if (!r.goal && !r.queries.length && data?.plan?.plan_json) {
      try {
        const plan = JSON.parse(data.plan.plan_json)
        r.goal = plan.goal || ""
        r.queries = plan.search_queries || []
      } catch { /* skip */ }
    }
    return r
  }, [responseEntries, data])

  const handleRerunStep = async () => {
    setLogLoading(true)
    try { await executeStep(taskId, selected.step_type) } catch {}
    // Step was updated in-place — reload meta log for same step ID
    getTaskMetaLog(taskId, selectedId).then(setMetaLog).catch(() => {}).finally(() => setLogLoading(false))
  }

  const tabBadges = entries.length > 0 ? {
    input: inputEntries.length,
    result: entries.length,
    log: otherEntries.length + searchEntries.length,
  } : undefined

  return (
    <div className="space-y-2 text-[10px]">
      <div className="flex items-center justify-between">
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">
          [ Step #{selected.step_number}: {STEP_LABELS[selected.step_type] || selected.step_type}
          <span className={selected.status === "stale" ? "text-[#f97316]" : "text-[#555]"}>
            ({selected.status})
          </span> ]
        </div>
        {(selected.status === "completed" || selected.status === "stale") && (
          <TerminalButton onClick={handleRerunStep} intent="edit">⟳ rerun step</TerminalButton>
        )}
      </div>

      <div className="flex gap-3 border-b border-[#1a1a1a] pb-1">
        {DETAIL_TABS.map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`text-[9px] uppercase cursor-pointer transition-colors
              ${tab === t ? "text-[#94a3b8]" : "text-[#444] hover:text-[#777]"}`}>
            {t}{tabBadges ? ` (${tabBadges[t]})` : ""}
          </button>
        ))}
      </div>

      {tab === "result" && (
        <StepResultTab
          selected={selected}
          selectedResults={selectedResults}
          parsedResult={parsedResult}
          responseEntries={responseEntries}
          inputEntries={inputEntries}
        />
      )}

      {tab === "input" && (
        <StepInputTab
          stepPhase={stepPhase}
          liveInput={liveInput}
          reinitLoading={reinitLoading}
          reinitLiveInput={reinitLiveInput}
          inputEntries={inputEntries}
        />
      )}

      {tab === "log" && (
        <StepLogTab entries={[...otherEntries, ...searchEntries]} loading={logLoading} />
      )}
    </div>
  )
})
