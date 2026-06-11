import { useState, useEffect, memo } from "react"
import type { MemoryNodeInfo } from "../../api/client"
import { getMemoryNodes } from "../../api/client"
import { MemoryNodeCard } from "./MemoryNodeCard"

interface MemoryNodesSectionProps {
  conversationId?: string
  enabled?: boolean
}

function MemoryNodesSectionComponent({ conversationId, enabled = false }: MemoryNodesSectionProps) {
  const [memoryNodes, setMemoryNodes] = useState<MemoryNodeInfo[]>([])
  const [loadingNodes, setLoadingNodes] = useState(false)
  const [hasFetched, setHasFetched] = useState(false)

  // Reset when conversation changes
  useEffect(() => {
    setMemoryNodes([])
    setHasFetched(false)
  }, [conversationId])

  // Fetch + poll
  useEffect(() => {
    if (!enabled || !conversationId) {
      return
    }

    let active = true
    let timeoutId: ReturnType<typeof setTimeout>

    const tick = async () => {
      if (!active) return
      setLoadingNodes(prev => !hasFetched || prev) // Only show initial loading
      try {
        const data = await getMemoryNodes(conversationId)
        if (active) {
          setMemoryNodes(data.nodes)
          setHasFetched(true)
        }
      } catch {
        if (active) {
          setMemoryNodes([])
        }
      } finally {
        if (active) setLoadingNodes(false)
      }

      if (active) {
        const delay = 30000 + (Math.random() - 0.5) * 2000 // 30s ± 1s
        timeoutId = setTimeout(tick, delay)
      }
    }

    tick()

    return () => {
      active = false
      clearTimeout(timeoutId)
    }
  }, [enabled, conversationId])

  if (loadingNodes && !hasFetched) {
    return (
      <div className="text-[10px] text-[#555] animate-pulse py-2 font-mono">
        intra-acting through memory strata...
      </div>
    )
  }

  if (memoryNodes.length === 0) {
    return (
      <div className="text-[10px] text-[#444] py-2 font-mono italic">
        No memory nodes yet — sedimentation runs when conversations reach the consolidation threshold.
      </div>
    )
  }

  return (
    <div className="mt-1.5 pt-1.5">
      <div className="text-[8px] text-[#555] mb-1.5 uppercase tracking-wider select-none font-bold">
        Intra-Active Memory Nodes ({memoryNodes.length})
      </div>
      <div className="flex flex-col gap-1.5">
        {memoryNodes.map((node) => (
          <MemoryNodeCard key={node.id} node={node} />
        ))}
      </div>
    </div>
  )
}

export const MemoryNodesSection = memo(MemoryNodesSectionComponent)
