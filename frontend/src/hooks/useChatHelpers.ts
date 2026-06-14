import type { ChatMessage } from "../api/client"

export function estimateTokens(text: string): number {
  if (!text) return 0
  return Math.max(1, Math.floor(text.length / 4))
}

export function getAncestorPathIds(messages: ChatMessage[], leafId: number | null): Set<number> {
  const path = new Set<number>()
  if (!leafId) return path

  const sorted = [...messages].sort((a, b) => a.id - b.id)

  let currentId: number | null = leafId
  const parentMap = new Map<number, number | null>()
  for (let i = 0; i < sorted.length; i++) {
    const m = sorted[i]
    if (m.parent_message_id !== undefined && m.parent_message_id !== null) {
      parentMap.set(m.id, m.parent_message_id)
    } else {
      parentMap.set(m.id, null)
    }
  }

  const visited = new Set<number>()
  while (currentId !== null && !visited.has(currentId)) {
    visited.add(currentId)
    path.add(currentId)
    currentId = parentMap.get(currentId) || null
  }

  return path
}
