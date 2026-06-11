import { useState, useEffect } from "react"
import type { MemoryNodeInfo } from "../../api/client"
import { getMemoryNodes } from "../../api/client"
import { MemoryNodeCard } from "./MemoryNodeCard"

interface MemoryNodesSectionProps {
  conversationId?: string
}

export function MemoryNodesSection({ conversationId }: MemoryNodesSectionProps) {
  const [memoryNodes, setMemoryNodes] = useState<MemoryNodeInfo[]>([])
  const [loadingNodes, setLoadingNodes] = useState(false)
  const [hasFetched, setHasFetched] = useState(false)

  useEffect(() => {
    setMemoryNodes([])
    setHasFetched(false)
  }, [conversationId])

  useEffect(() => {
    if (!conversationId || hasFetched) return
    setLoadingNodes(true)
    getMemoryNodes(conversationId)
      .then((data) => setMemoryNodes(data.nodes))
      .catch(() => setMemoryNodes([]))
      .finally(() => {
        setLoadingNodes(false)
        setHasFetched(true)
      })
  }, [conversationId, hasFetched])

  if (loadingNodes) {
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
