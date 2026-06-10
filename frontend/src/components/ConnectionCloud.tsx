import { useEffect, useRef, useState } from "react"
import type { ChatMessage } from "../api/client"

interface ConnectionCloudProps {
  messages: ChatMessage[]
  links: any[]
  activeMessageId: number | null
  activePathIds: Set<number>
  setActiveMessageId: (id: number | null) => void
  commitProposedBranch: (parentMsgId: number, content: string) => Promise<any>
}

interface SimNode {
  id: string
  dbId?: number
  speaker: string
  content: string
  isProposed: boolean
  title?: string
  parentMsgId?: number | null
  x: number
  y: number
  vx: number
  vy: number
}

interface SimLink {
  source: string
  target: string
  type: "parent" | "resonance"
}

export default function ConnectionCloud({
  messages,
  links,
  activeMessageId,
  activePathIds,
  setActiveMessageId,
  commitProposedBranch,
}: ConnectionCloudProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 300, height: 300 })
  const [simNodes, setSimNodes] = useState<SimNode[]>([])
  const [simLinks, setSimLinks] = useState<SimLink[]>([])
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null)
  
  // Branch proposal commit overlay state
  const [committingNode, setCommittingNode] = useState<SimNode | null>(null)
  const [commitContent, setCommitContent] = useState("")
  const [isCommitLoading, setIsCommitLoading] = useState(false)

  // Track positions across renders to prevent layout resetting when messages change
  const nodePositionsRef = useRef<Record<string, { x: number; y: number }>>({})

  // Update container dimensions on resize
  useEffect(() => {
    if (!containerRef.current) return
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: Math.max(100, entry.contentRect.width),
          height: Math.max(150, entry.contentRect.height),
        })
      }
    })
    resizeObserver.observe(containerRef.current)
    return () => resizeObserver.disconnect()
  }, [])

  // Build nodes and links from messages, db links, and inline proposals
  useEffect(() => {
    const newNodes: SimNode[] = []
    const newLinks: SimLink[] = []

    // 1. Add all message nodes
    for (const m of messages) {
      const idStr = String(m.id)
      const prevPos = nodePositionsRef.current[idStr]
      
      newNodes.push({
        id: idStr,
        dbId: m.id,
        speaker: m.speaker,
        content: m.content,
        isProposed: false,
        parentMsgId: m.parent_message_id,
        x: prevPos ? prevPos.x : dimensions.width / 2 + (Math.random() - 0.5) * 40,
        y: prevPos ? prevPos.y : dimensions.height / 2 + (Math.random() - 0.5) * 40,
        vx: 0,
        vy: 0,
      })

      // Link to parent message if it is in the active messages list
      if (m.parent_message_id && messages.some((msg) => msg.id === m.parent_message_id)) {
        newLinks.push({
          source: String(m.parent_message_id),
          target: idStr,
          type: "parent",
        })
      }

      // Extract and add any proposed branches (virtual nodes)
      if (m.proposed_branches && m.proposed_branches.length > 0) {
        m.proposed_branches.forEach((b, idx) => {
          const propIdStr = `proposed_${m.id}_${idx}`
          const prevPropPos = nodePositionsRef.current[propIdStr]
          
          newNodes.push({
            id: propIdStr,
            speaker: "proposed",
            content: b.content,
            title: b.title,
            isProposed: true,
            parentMsgId: m.id,
            x: prevPropPos ? prevPropPos.x : (prevPos ? prevPos.x : dimensions.width / 2) + (Math.random() - 0.5) * 60,
            y: prevPropPos ? prevPropPos.y : (prevPos ? prevPos.y : dimensions.height / 2) + (Math.random() - 0.5) * 60,
            vx: 0,
            vy: 0,
          })

          newLinks.push({
            source: idStr,
            target: propIdStr,
            type: "parent", // Proposed branches are tethered to their parent
          })
        })
      }
    }

    // 2. Add database retroactive links (resonance links)
    for (const l of links) {
      const srcStr = String(l.source_id)
      const tgtStr = String(l.target_id)
      
      // Only include links where both nodes exist in the current message set
      if (newNodes.some((n) => n.id === srcStr) && newNodes.some((n) => n.id === tgtStr)) {
        newLinks.push({
          source: srcStr,
          target: tgtStr,
          type: "resonance",
        })
      }
    }

    setSimNodes(newNodes)
    setSimLinks(newLinks)
  }, [messages, links, dimensions.width, dimensions.height])

  // Run the force simulation loop
  useEffect(() => {
    if (simNodes.length === 0) return

    let animationFrameId: number
    const friction = 0.82
    const gravityStrength = 0.05
    const repulseStrength = 320
    const springLength = 45
    const springStrength = 0.09

    const runSimulation = () => {
      setSimNodes((currentNodes) => {
        // Create local copy to mutate for this step
        const nodes = currentNodes.map((n) => ({ ...n }))
        const nodeMap = new Map<string, SimNode>()
        nodes.forEach((n) => nodeMap.set(n.id, n))

        // Center coordinates
        const cx = dimensions.width / 2
        const cy = dimensions.height / 2

        // 1. Repulsion force between all node pairs
        for (let i = 0; i < nodes.length; i++) {
          const a = nodes[i]
          for (let j = i + 1; j < nodes.length; j++) {
            const b = nodes[j]
            const dx = b.x - a.x
            const dy = b.y - a.y
            const distSq = dx * dx + dy * dy + 1e-4
            const dist = Math.sqrt(distSq)

            if (dist < 180) {
              const force = repulseStrength / distSq
              const fx = (dx / dist) * force
              const fy = (dy / dist) * force

              a.vx -= fx
              a.vy -= fy
              b.vx += fx
              b.vy += fy
            }
          }
        }

        // 2. Attraction spring force along links
        for (const link of simLinks) {
          const a = nodeMap.get(link.source)
          const b = nodeMap.get(link.target)
          if (!a || !b) continue

          const dx = b.x - a.x
          const dy = b.y - a.y
          const dist = Math.sqrt(dx * dx + dy * dy) + 1e-4

          const displacement = dist - springLength
          const force = displacement * springStrength
          const fx = (dx / dist) * force
          const fy = (dy / dist) * force

          a.vx += fx
          a.vy += fy
          b.vx -= fx
          b.vy -= fy
        }

        // 3. Centering force (gravity)
        for (const n of nodes) {
          n.vx += (cx - n.x) * gravityStrength
          n.vy += (cy - n.y) * gravityStrength

          // Update positions
          n.x += n.vx
          n.y += n.vy

          // Clamp to dimensions to prevent nodes escaping viewport
          n.x = Math.max(15, Math.min(dimensions.width - 15, n.x))
          n.y = Math.max(15, Math.min(dimensions.height - 15, n.y))

          // Apply friction
          n.vx *= friction
          n.vy *= friction

          // Save current positions for persistence
          nodePositionsRef.current[n.id] = { x: n.x, y: n.y }
        }

        return nodes
      })

      animationFrameId = requestAnimationFrame(runSimulation)
    }

    animationFrameId = requestAnimationFrame(runSimulation)
    return () => cancelAnimationFrame(animationFrameId)
  }, [simNodes.length, simLinks, dimensions.width, dimensions.height])

  const handleNodeClick = (node: SimNode) => {
    if (node.isProposed) {
      setCommittingNode(node)
      setCommitContent(node.content)
    } else if (node.dbId) {
      setActiveMessageId(node.dbId)
    }
  }

  const handleCommitSubmit = async () => {
    if (!committingNode || !committingNode.parentMsgId || !commitContent.trim()) return
    setIsCommitLoading(true)
    try {
      await commitProposedBranch(committingNode.parentMsgId, commitContent)
      setCommittingNode(null)
    } catch (err) {
      console.error("Failed to commit proposed node:", err)
    } finally {
      setIsCommitLoading(false)
    }
  }

  // Helper to check if a link is part of the active path
  const isLinkActive = (link: SimLink) => {
    const srcId = parseInt(link.source)
    const tgtId = parseInt(link.target)
    if (isNaN(srcId) || isNaN(tgtId)) return false
    return activePathIds.has(srcId) && activePathIds.has(tgtId)
  }

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full bg-[#0a0a0c] border border-[#1b1b21] rounded-lg overflow-hidden flex flex-col"
    >
      {/* Header */}
      <div className="px-3 py-2 border-b border-[#1b1b21] flex justify-between items-center bg-[#0d0d11]">
        <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#79798c]">
          Connection Cloud
        </span>
        <span className="text-[10px] font-mono text-[#4b4b5c]">
          {simNodes.filter((n) => !n.isProposed).length} nodes | {links.length} cross-links
        </span>
      </div>

      {/* SVG Canvas */}
      <div className="flex-1 relative cursor-grab active:cursor-grabbing">
        <svg width={dimensions.width} height={dimensions.height} className="w-full h-full">
          {/* Grid lines */}
          <defs>
            <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#ffffff" strokeWidth="0.5" opacity="0.02" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Links */}
          {simLinks.map((link, idx) => {
            const srcNode = simNodes.find((n) => n.id === link.source)
            const tgtNode = simNodes.find((n) => n.id === link.target)
            if (!srcNode || !tgtNode) return null

            const isActive = isLinkActive(link)
            const isResonance = link.type === "resonance"
            const isProposed = srcNode.isProposed || tgtNode.isProposed

            let strokeColor = "#272730"
            let strokeWidth = "1.5"
            let strokeDash = ""

            if (isActive) {
              strokeColor = "#00e5ff" // Bright cyan for active path
              strokeWidth = "2.2"
            } else if (isProposed) {
              strokeColor = "#ec4899" // Dim pink for proposed links
              strokeDash = "3,3"
              strokeWidth = "1"
            } else if (isResonance) {
              strokeColor = "#f59e0b" // Gold for retroactive resonance links
              strokeDash = "2,2"
              strokeWidth = "1.5"
            }

            return (
              <line
                key={`link-${idx}`}
                x1={srcNode.x}
                y1={srcNode.y}
                x2={tgtNode.x}
                y2={tgtNode.y}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
                strokeDasharray={strokeDash}
                opacity={isActive ? 0.95 : isProposed ? 0.45 : 0.4}
                className="transition-all duration-300"
              />
            )
          })}

          {/* Nodes */}
          {simNodes.map((node) => {
            const isActive = node.dbId ? activePathIds.has(node.dbId) : false
            const isLeaf = activeMessageId === node.dbId
            const isHovered = hoveredNode?.id === node.id

            let fill = "#1e1e24"
            let stroke = "#3f3f4e"
            let strokeWidth = "1.5"
            let radius = "6"
            let nodeClass = "transition-all duration-200 cursor-pointer"

            if (node.isProposed) {
              fill = "transparent"
              stroke = "#ec4899" // Proposed pink
              strokeWidth = "1.5"
              radius = "7"
              nodeClass += " animate-pulse stroke-dasharray-[3,3]"
            } else if (node.speaker === "human") {
              if (isActive) {
                fill = "#00e5ff" // Cyan for active user msg
                stroke = "#ffffff"
                strokeWidth = isLeaf ? "2.5" : "1.5"
                radius = isLeaf ? "9" : "7.5"
              } else {
                fill = "#0891b2" // Dim cyan
                stroke = "#155e75"
                radius = "6"
              }
            } else if (node.speaker === "apparatus") {
              if (isActive) {
                fill = "#c084fc" // Purple for active agent msg
                stroke = "#ffffff"
                strokeWidth = isLeaf ? "2.5" : "1.5"
                radius = isLeaf ? "9" : "7.5"
              } else {
                fill = "#7c3aed" // Dim purple
                stroke = "#5b21b6"
                radius = "6"
              }
            } else {
              // System
              fill = "#4b5563"
              stroke = "#374151"
              radius = "4"
            }

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onClick={(e) => {
                  e.stopPropagation()
                  handleNodeClick(node)
                }}
                onMouseEnter={() => setHoveredNode(node)}
                onMouseLeave={() => setHoveredNode(null)}
                className={nodeClass}
              >
                {/* Visual Glow for Active Leaf Node */}
                {isLeaf && (
                  <circle
                    r="15"
                    fill={node.speaker === "human" ? "#00e5ff" : "#c084fc"}
                    opacity="0.2"
                    className="animate-ping"
                  />
                )}
                {/* Main Circle */}
                <circle
                  r={isHovered ? String(parseFloat(radius) + 2) : radius}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                  opacity={isActive || isLeaf || isHovered ? 1 : node.isProposed ? 0.7 : 0.45}
                  className="transition-all duration-150"
                />
                
                {/* Proposed Title Label */}
                {node.isProposed && (
                  <text
                    y="-12"
                    textAnchor="middle"
                    className="text-[9px] font-mono fill-[#ec4899] select-none font-bold"
                    opacity="0.8"
                  >
                    🚀 {node.title || "Flight"}
                  </text>
                )}
              </g>
            )
          })}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredNode && (
          <div
            className="absolute z-10 px-2 py-1.5 bg-[#0d0d12] border border-[#1b1b22] rounded shadow-xl text-[10px] font-mono max-w-[200px] pointer-events-none select-none"
            style={{
              left: `${Math.min(dimensions.width - 210, Math.max(10, hoveredNode.x - 100))}px`,
              top: `${Math.min(dimensions.height - 70, Math.max(10, hoveredNode.y - 65))}px`,
            }}
          >
            <div className="flex justify-between border-b border-[#1b1b22] pb-0.5 mb-1">
              <span className={`font-bold capitalize ${
                hoveredNode.speaker === "human" ? "text-[#00e5ff]" : 
                hoveredNode.speaker === "proposed" ? "text-[#ec4899]" : "text-[#c084fc]"
              }`}>
                {hoveredNode.speaker === "proposed" ? `Agential Proposal: ${hoveredNode.title}` : hoveredNode.speaker}
              </span>
              <span className="text-[#4b4b5c]">
                {hoveredNode.isProposed ? "Consent Required" : `ID: ${hoveredNode.dbId}`}
              </span>
            </div>
            <div className="text-[#a1a1b5] line-clamp-2">
              {hoveredNode.content}
            </div>
          </div>
        )}

        {/* Branch Commit Modal Overlay */}
        {committingNode && (
          <div className="absolute inset-0 bg-[#09090b]/80 flex flex-col justify-end p-3 z-20 animate-fade-in">
            <div className="bg-[#0e0e12] border border-[#ec4899]/30 rounded-lg p-3 shadow-2xl flex flex-col gap-2">
              <div className="flex justify-between items-center border-b border-[#1b1b21] pb-1">
                <span className="text-[10px] font-mono font-bold text-[#ec4899] uppercase tracking-wider">
                  Commit Line of Flight
                </span>
                <button
                  onClick={() => setCommittingNode(null)}
                  className="text-xs font-mono text-[#4b4b5c] hover:text-[#a1a1b5]"
                >
                  Cancel
                </button>
              </div>
              
              <div className="text-[10px] font-mono text-[#a1a1b5]">
                Topic: <strong className="text-white">{committingNode.title}</strong>
              </div>

              <textarea
                value={commitContent}
                onChange={(e) => setCommitContent(e.target.value)}
                rows={4}
                className="w-full bg-[#07070a] border border-[#1b1b21] rounded p-2 text-xs font-mono text-[#e4e4e7] focus:outline-none focus:border-[#ec4899] resize-none"
              />

              <button
                onClick={handleCommitSubmit}
                disabled={isCommitLoading || !commitContent.trim()}
                className="w-full py-1.5 rounded text-xs font-mono font-bold text-white bg-[#ec4899] hover:bg-[#db2777] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isCommitLoading ? "Committing..." : "Commit Branch to DAG"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
