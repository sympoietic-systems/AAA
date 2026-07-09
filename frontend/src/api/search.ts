import { BASE } from "./http"

export interface SearchMatch {
  id: string
  type: "message" | "note" | "memory_node"
  conversation_id: string
  title: string
  snippet: string
  relevance_score: number
  timestamp: string
}

export interface SearchQueryParams {
  q: string
  conversation_id?: string
  mode?: "text" | "semantic" | "diffractive" | "glitch"
  w_text?: number
  w_semantic?: number
  w_structural?: number
  w_glitch?: number
}

export async function searchArchive(params: SearchQueryParams): Promise<SearchMatch[]> {
  const url = new URL(`${window.location.origin}${BASE}/search`)
  
  if (params.q) url.searchParams.set("q", params.q)
  if (params.conversation_id) url.searchParams.set("conversation_id", params.conversation_id)
  if (params.mode) url.searchParams.set("mode", params.mode)
  
  if (params.w_text !== undefined) url.searchParams.set("w_text", String(params.w_text))
  if (params.w_semantic !== undefined) url.searchParams.set("w_semantic", String(params.w_semantic))
  if (params.w_structural !== undefined) url.searchParams.set("w_structural", String(params.w_structural))
  if (params.w_glitch !== undefined) url.searchParams.set("w_glitch", String(params.w_glitch))

  const resp = await fetch(url)
  if (!resp.ok) {
    throw new Error(`Search request failed with status ${resp.status}`)
  }
  return resp.json()
}
