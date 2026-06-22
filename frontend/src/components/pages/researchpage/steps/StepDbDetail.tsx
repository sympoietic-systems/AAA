type DetailTab = "input" | "result" | "log"

export const DETAIL_TABS: DetailTab[] = ["input", "result", "log"]

import { memo, useState, useEffect, useMemo } from "react"
import type { MetaLogResponse, TaskStepsResponse, StepPreview, ResearchStep } from "../../../../api/research"
import { getTaskMetaLog, getStepPreview, executeStep, reinitializeTask } from "../../../../api/research"
import { TerminalButton } from "../../../UI"
import { STEP_TO_PHASE, STEP_LABELS } from "../constants/taskConstants"
import { StepResultTab, repairTruncatedJson } from "./StepResultTab"
import { StepInputTab } from "./StepInputTab"
import { StepLogTab } from "./StepLogTab"

interface DbStepDetailProps {
  taskId: string
  data: TaskStepsResponse | null
  selectedId: string
  onSelectTab?: (tabId: "info" | "steps" | "report") => void
}

const getStepDepth = (step: ResearchStep): number => {
  if (step.step_type === "plan") return 0
  if (!step.step_data) return 0
  try {
    const parsed = JSON.parse(step.step_data)
    return typeof parsed.depth === "number" ? parsed.depth : 0
  } catch {
    return 0
  }
}

export const DbStepDetail = memo(function DbStepDetail({ taskId, data, selectedId, onSelectTab }: DbStepDetailProps) {
  const steps = data ? [...data.steps].reverse() : []
  const selected = steps.find(s => s.id === selectedId)
  if (!selected) return null
  const selectedResults = data ? (data.results_by_step[selectedId] || []) : []

  // Fallback to find search/digest results for a query_group if the step itself has no saved results (older runs or digest updates stored under parse step)
  const resolvedSearchResults = useMemo(() => {
    if (!data || !selected) return []
    const selectedDepth = getStepDepth(selected)
    if (selected.step_type === "search") {
      if (selectedResults.length > 0) return selectedResults
      const parseStep = data.steps.find(s => s.step_type === "parallel_parse" && s.query_group === selected.query_group && getStepDepth(s) === selectedDepth)
      if (parseStep && data.results_by_step[parseStep.id]?.length > 0) {
        return data.results_by_step[parseStep.id]
      }
      const digestStep = data.steps.find(s => s.step_type === "digest" && s.query_group === selected.query_group && getStepDepth(s) === selectedDepth)
      if (digestStep && data.results_by_step[digestStep.id]?.length > 0) {
        return data.results_by_step[digestStep.id]
      }
    }
    if (selected.step_type === "digest") {
      if (selectedResults.length > 0) return selectedResults
      const parseStep = data.steps.find(s => s.step_type === "parallel_parse" && s.query_group === selected.query_group && getStepDepth(s) === selectedDepth)
      if (parseStep && data.results_by_step[parseStep.id]?.length > 0) {
        return data.results_by_step[parseStep.id]
      }
    }
    return selectedResults
  }, [data, selected, selectedId, selectedResults])

  // For parse: the search step's results are the URLs to parse
  // For digest: the parse step's results are the pages to digest
  const parentInputUrls = useMemo(() => {
    if (!data || !selected) return []
    const selectedDepth = getStepDepth(selected)
    if (selected.step_type === "parallel_parse") {
      const searchStep = data.steps.find(s => s.step_type === "search" && s.query_group === selected.query_group && getStepDepth(s) === selectedDepth)
      if (searchStep) {
        const searchResults = data.results_by_step[searchStep.id] || []
        if (searchResults.length > 0) {
          return searchResults.map(r => ({ url: r.source_url || "", title: r.source_title || r.source_url?.slice(0, 80) || "" }))
        }
      }
      const parseResults = data.results_by_step[selectedId] || []
      return parseResults.map(r => ({ url: r.source_url || "", title: r.source_title || r.source_url?.slice(0, 80) || "" }))
    }
    if (selected.step_type === "digest") {
      const parseStep = data.steps.find(s => s.step_type === "parallel_parse" && s.query_group === selected.query_group && getStepDepth(s) === selectedDepth)
      if (parseStep) {
        const parseResults = data.results_by_step[parseStep.id] || []
        if (parseResults.length > 0) {
          return parseResults.map(r => ({
            url: r.source_url || "",
            title: r.source_title || r.source_url?.slice(0, 80) || "",
            error: r.error,
            raw_file_path: r.raw_file_path,
            content_preview: r.content_preview
          }))
        }
      }
      const digestResults = data.results_by_step[selectedId] || []
      return digestResults.map(r => ({
        url: r.source_url || "",
        title: r.source_title || r.source_url?.slice(0, 80) || "",
        error: r.error,
        raw_file_path: r.raw_file_path,
        content_preview: r.content_preview
      }))
    }
    return []
  }, [data, selected, selectedId])

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
      e.event_type === "orchestrator_evaluate" ||
      (d && (d.system_prompt || d.user_prompt))
  })
  const responseEntries = entries.filter(e =>
    e.event_type.endsWith("_response") && !e.event_type.endsWith("_prompt")
  )
  const searchEntries = entries.filter(e => e.event_type === "orchestrator_search")
  const otherEntries = entries.filter(e => !inputEntries.includes(e) && !responseEntries.includes(e))

  const parsedResult = useMemo(() => {
    const r: {
      queries: string[]
      goal: string
      completeness: number
      answer: string
      confidence: number
      learnings: string[]
      query: string
      urls: {url:string,title:string}[]
      reflection?: string
      key_insights?: string[]
      remaining_gaps?: string[]
      next_queries?: string[]
      next_direct_urls?: string[]
    } = {
      queries: [],
      goal: "",
      completeness: 0,
      answer: "",
      confidence: 0,
      learnings: [],
      query: "",
      urls: [],
      reflection: "",
    }
    for (const e of responseEntries) {
      try {
        const d = e.event_data as any
        const raw = d?.raw_response || d?.raw || d?.response || ""
        let parsed: any = null
        try { parsed = JSON.parse(raw) } catch {
          try { parsed = JSON.parse(repairTruncatedJson(raw)) } catch {
            try { parsed = JSON.parse(d?.raw_response || "") } catch {
              try { parsed = JSON.parse(d?.response || "") } catch { /* skip */ }
            }
          }
        }
        if (!parsed) continue
        const jd = parsed.json_data || parsed.content || parsed
        if (typeof jd === "string") {
          try { parsed = JSON.parse(jd) } catch {
            try { parsed = JSON.parse(repairTruncatedJson(jd)) } catch { /* skip */ }
          }
        } else {
          parsed = jd
        }
        if (typeof parsed !== "object" || !parsed) continue
        if (e.event_type === "orchestrator_plan_response") {
          r.goal = parsed.goal || ""
          r.queries = parsed.search_queries || []
        } else if (e.event_type === "orchestrator_digest_response") {
          if (parsed.learnings) r.learnings.push(...parsed.learnings)
        } else if (e.event_type.includes("reflect_response")) {
          r.completeness = parsed.completeness_score || parsed.completeness || 0
          r.reflection = parsed.reflection || ""
          r.key_insights = parsed.key_insights || []
          r.remaining_gaps = parsed.remaining_gaps || []
          r.next_queries = parsed.next_queries || []
          r.next_direct_urls = parsed.next_direct_urls || []
        } else if (e.event_type === "orchestrator_synthesize_response") {
          r.answer = parsed.report_markdown || parsed.answer || ""
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
    try { await executeStep(taskId, selected.step_type, selectedId) } catch {}
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
          selectedResults={resolvedSearchResults}
          parsedResult={parsedResult}
          responseEntries={responseEntries}
          inputEntries={inputEntries}
          parentInputUrls={parentInputUrls}
          onSelectTab={onSelectTab}
        />
      )}

      {tab === "input" && (
        <StepInputTab
          stepPhase={stepPhase}
          liveInput={liveInput}
          reinitLoading={reinitLoading}
          reinitLiveInput={reinitLiveInput}
          inputEntries={inputEntries}
          parentInputUrls={parentInputUrls}
          stepType={selected.step_type}
        />
      )}

      {tab === "log" && (
        <StepLogTab entries={[...otherEntries, ...searchEntries]} loading={logLoading} />
      )}
    </div>
  )
})
