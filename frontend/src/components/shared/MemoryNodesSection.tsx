import { useState, useEffect, useRef, memo } from "react"
import type { MemoryNodeInfo } from "../../api/client"
import { getMemoryNodes } from "../../api/client"
import { MemoryNodeCard } from "./MemoryNodeCard"

interface MemoryNodesSectionProps {
  conversationId?: string
  enabled?: boolean
  className?: string
  style?: React.CSSProperties
}

function MemoryNodesSectionComponent({ conversationId, enabled = false, className, style }: MemoryNodesSectionProps) {
  const [memoryNodes, setMemoryNodes] = useState<MemoryNodeInfo[]>([])
  const [loadingNodes, setLoadingNodes] = useState(false)
  const [hasFetched, setHasFetched] = useState(false)
  const hasFetchedRef = useRef(false)

  // Keep ref in sync with state for the polling closure
  hasFetchedRef.current = hasFetched

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
      setLoadingNodes(prev => !hasFetchedRef.current || prev) // Only show loading on first fetch
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
      <div className="text-[10px] text-ui-dim animate-pulse py-2 font-mono">
        intra-acting through memory strata...
      </div>
    )
  }

  if (memoryNodes.length === 0) {
    return (
      <div className="text-[10px] text-ui-dim py-2 font-mono italic">
        No memory nodes yet — sedimentation runs when conversations reach the consolidation threshold.
      </div>
    )
  }

  const uniqueNodes = memoryNodes.filter(
    (n, i, a) => a.findIndex(x => x.id === n.id) === i
  )

  const sortedNodes = [...uniqueNodes].sort((a, b) => {
    const aTime = a.created_at ? new Date(a.created_at).getTime() : 0
    const bTime = b.created_at ? new Date(b.created_at).getTime() : 0
    return bTime - aTime
  })

  return (
    <div className="mt-1.5 pt-1.5 font-mono">
      <div className="text-[8px] text-ui-dim mb-1.5 uppercase tracking-wider select-none font-bold">
        Intra-Active Memory Nodes ({sortedNodes.length})
      </div>
      <div className={className || "flex flex-col gap-1.5"} style={style}>
        {sortedNodes.map((node) => (
          <MemoryNodeCard key={node.id} node={node} />
        ))}
      </div>
    </div>
  )
}

export const MemoryNodesSection = memo(MemoryNodesSectionComponent)
