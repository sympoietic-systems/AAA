// researchStore — pub-sub store for research task telemetry.
// Lazy polling: starts when first subscriber arrives, stops when last leaves.

import { getResearchSummary, type ResearchSummary } from "../api/research"

type Listener = () => void

let state: ResearchSummary = { active_count: 0, queued_count: 0, pending_proposals: 0 }
let loading = false
const listeners = new Set<Listener>()
let timer: ReturnType<typeof setInterval> | null = null

const POLL_INTERVAL = 8000 // 8 seconds

async function poll() {
  try {
    loading = true
    const data = await getResearchSummary()
    state = data
    loading = false
    emit()
  } catch {
    loading = false
  }
}

function emit() {
  listeners.forEach((fn) => fn())
}

export function subscribeResearch(fn: Listener): () => void {
  listeners.add(fn)
  if (listeners.size === 1) {
    poll()
    timer = setInterval(poll, POLL_INTERVAL)
  }
  return () => {
    listeners.delete(fn)
    if (listeners.size === 0 && timer) {
      clearInterval(timer)
      timer = null
    }
  }
}

export function getResearchState(): ResearchSummary {
  return state
}

export function isResearchLoading(): boolean {
  return loading
}
