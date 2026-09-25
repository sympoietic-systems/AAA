import { useEffect, useState } from "react"
import { searchArchive, type SearchMatch, type SearchQueryParams } from "../api/search"

export function useArchiveSearch(params: SearchQueryParams) {
  const key = JSON.stringify(params)
  const enabled = Boolean(params.q.trim() || params.w_glitch)
  const [state, setState] = useState<{ key: string; results: SearchMatch[]; loading: boolean; error: string | null }>({ key: "", results: [], loading: false, error: null })
  useEffect(() => {
    if (!enabled) return
    const controller = new AbortController()
    const timer = setTimeout(async () => {
      setState({ key, results: [], loading: true, error: null })
      try {
        const results = await searchArchive(JSON.parse(key) as SearchQueryParams, controller.signal)
        if (!controller.signal.aborted) setState({ key, results, loading: false, error: null })
      } catch (error) {
        if (!controller.signal.aborted) setState({ key, results: [], loading: false, error: error instanceof Error ? error.message : "Search failed" })
      }
    }, 250)
    return () => { clearTimeout(timer); controller.abort() }
  }, [key, enabled])
  return enabled && state.key === key ? state : { results: [], loading: enabled, error: null }
}
