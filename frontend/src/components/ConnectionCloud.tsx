import { useEffect, useRef, useState } from "react"
import type { ChatMessage, NoteInfo } from "../api/client"
import { confirmResonanceLink, deleteResonanceLink } from "../api/client"

interface ConnectionCloudProps {
  messages: ChatMessage[]
  links: any[]
  notes: NoteInfo[]
  activeMessageId: number | null
  activePathIds: Set<number>
  setActiveMessageId: (id: number | null) => void
  commitProposedBranch: (parentMsgId: number, content: string) => Promise<any>
  refreshTree: () => void
  conversationId: string
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
  targetX?: number
  targetY?: number
}

interface SimLink {
  id?: string
  source: string
  target: string
  type: "parent" | "resonance"
  status?: "active" | "proposed"
  justification?: string
}

export default function ConnectionCloud({
  messages,
  links,
  notes,
  activeMessageId,
  activePathIds,
  setActiveMessageId,
  commitProposedBranch,
  refreshTree,
  conversationId,
}: ConnectionCloudProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 300, height: 300 })
  const [simNodes, setSimNodes] = useState<SimNode[]>([])
  const [simLinks, setSimLinks] = useState<SimLink[]>([])
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null)
  
  // Resonance link selection state
  const [selectedLink, setSelectedLink] = useState<SimLink | null>(null)
  const [selectedLinkPos, setSelectedLinkPos] = useState<{ x: number; y: number } | null>(null)
  
  // Branch proposal commit overlay state
  const [committingNode, setCommittingNode] = useState<SimNode | null>(null)
  const [commitContent, setCommitContent] = useState("")
  const [isCommitLoading, setIsCommitLoading] = useState(false)

  // Track positions across renders to prevent layout resetting when messages change
  const nodePositionsRef = useRef<Record<string, { x: number; y: number }>>({})

  // Zoom and pan state
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const panStartRef = useRef({ x: 0, y: 0 })

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

    const sorted = [...messages].sort((a, b) => a.id - b.id)

    // 1. Add all message nodes
    for (let i = 0; i < sorted.length; i++) {
      const m = sorted[i]
      const idStr = String(m.id)
      
      newNodes.push({
        id: idStr,
        dbId: m.id,
        speaker: m.speaker,
        content: m.content,
        isProposed: false,
        parentMsgId: m.parent_message_id,
        x: 0,
        y: 0,
        vx: 0,
        vy: 0,
      })

      // Link to parent message (use chronological fallback if parent_message_id is null/undefined)
      const parentId = m.parent_message_id !== undefined && m.parent_message_id !== null
        ? m.parent_message_id
        : (i > 0 ? sorted[i - 1].id : null)

      if (parentId && sorted.some((msg) => msg.id === parentId)) {
        newLinks.push({
          source: String(parentId),
          target: idStr,
          type: "parent",
        })
      }

      // Extract and add any proposed branches (virtual nodes)
      if (m.proposed_branches && m.proposed_branches.length > 0) {
        m.proposed_branches.forEach((b, idx) => {
          const propIdStr = `proposed_${m.id}_${idx}`
          
          newNodes.push({
            id: propIdStr,
            speaker: "proposed",
            content: b.content,
            title: b.title,
            isProposed: true,
            parentMsgId: m.id,
            x: 0,
            y: 0,
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

    // 2. Calculate spiral target coordinates for sequential nodes
    const totalNodes = newNodes.length
    const cx = dimensions.width / 2
    const cy = dimensions.height / 2
    const maxTargetRadius = Math.min(dimensions.width, dimensions.height) * 0.42
    
    // Choose spiral density based on total nodes to keep it clean and fitting in canvas
    const radiusStep = totalNodes > 10 ? (maxTargetRadius - 20) / totalNodes : 12
    const angleStep = 0.55 // approx 31 degrees per step (prevents concentric overlays)

    for (let i = 0; i < totalNodes; i++) {
      const node = newNodes[i]
      const prevPos = nodePositionsRef.current[node.id]
      
      const angle = i * angleStep
      const radius = 20 + i * radiusStep
      const tx = cx + radius * Math.cos(angle)
      const ty = cy + radius * Math.sin(angle)

      node.targetX = tx
      node.targetY = ty
      
      // Keep previous position if it exists to prevent jitter on updates
      node.x = prevPos ? prevPos.x : tx
      node.y = prevPos ? prevPos.y : ty
    }

    // 3. Add database retroactive links (resonance links)
    for (const l of links) {
      const srcStr = String(l.source_id)
      const tgtStr = String(l.target_id)
      
      // Only include links where both nodes exist in the current message set
      if (newNodes.some((n) => n.id === srcStr) && newNodes.some((n) => n.id === tgtStr)) {
        newLinks.push({
          id: l.id,
          source: srcStr,
          target: tgtStr,
          type: "resonance",
          status: l.status || "active",
          justification: l.justification || "",
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
    let alpha = 1.0 // Simulation temperature
    const decay = 0.965 // Cooling rate
    const friction = 0.78 // Slightly lower friction for faster settling
    const repulseStrength = 180 // Reduced repulsion for smaller nodes
    const springLength = 32 // Shorter links for a more compact structure
    const springStrength = 0.08

    const runSimulation = () => {
      // Stop calculation once the system has cooled/settled
      if (alpha < 0.015) {
        return
      }

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

            if (dist < 120) {
              const force = (repulseStrength * alpha) / distSq
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
          const force = displacement * springStrength * alpha
          const fx = (dx / dist) * force
          const fy = (dy / dist) * force

          a.vx += fx
          a.vy += fy
          b.vx -= fx
          b.vy -= fy
        }

        // 3. Spiral target anchoring force (gravity replacement)
        const anchorStrength = 0.12 // Gentle anchoring force to preserve spiral layout
        for (const n of nodes) {
          const tx = n.targetX !== undefined ? n.targetX : cx
          const ty = n.targetY !== undefined ? n.targetY : cy
          n.vx += (tx - n.x) * anchorStrength * alpha
          n.vy += (ty - n.y) * anchorStrength * alpha

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

      alpha *= decay
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

  // Zoom and pan event handlers
  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    setIsPanning(true)
    panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }
    setSelectedLink(null)
    setSelectedLinkPos(null)
  }

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!isPanning) return
    setPan({
      x: e.clientX - panStartRef.current.x,
      y: e.clientY - panStartRef.current.y
    })
  }

  const handleMouseUpOrLeave = () => {
    setIsPanning(false)
  }

  const handleWheel = (e: React.WheelEvent<SVGSVGElement>) => {
    e.preventDefault()
    const zoomFactor = 1.08
    const nextZoom = Math.max(0.2, Math.min(4.0, e.deltaY < 0 ? zoom * zoomFactor : zoom / zoomFactor))
    
    // Zoom around center of the canvas
    const cx = dimensions.width / 2
    const cy = dimensions.height / 2
    const scaleRatio = nextZoom / zoom
    
    setPan({
      x: cx - (cx - pan.x) * scaleRatio,
      y: cy - (cy - pan.y) * scaleRatio
    })
    setZoom(nextZoom)
  }

  const handleZoomIn = (e: React.MouseEvent) => {
    e.stopPropagation()
    const nextZoom = Math.min(4.0, zoom * 1.2)
    const cx = dimensions.width / 2
    const cy = dimensions.height / 2
    const scaleRatio = nextZoom / zoom
    setPan({
      x: cx - (cx - pan.x) * scaleRatio,
      y: cy - (cy - pan.y) * scaleRatio
    })
    setZoom(nextZoom)
  }

  const handleZoomOut = (e: React.MouseEvent) => {
    e.stopPropagation()
    const nextZoom = Math.max(0.2, zoom / 1.2)
    const cx = dimensions.width / 2
    const cy = dimensions.height / 2
    const scaleRatio = nextZoom / zoom
    setPan({
      x: cx - (cx - pan.x) * scaleRatio,
      y: cy - (cy - pan.y) * scaleRatio
    })
    setZoom(nextZoom)
  }

  const handleResetZoom = (e: React.MouseEvent) => {
    e.stopPropagation()
    setZoom(1)
    setPan({ x: 0, y: 0 })
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
        <svg
          width={dimensions.width}
          height={dimensions.height}
          className="w-full h-full"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUpOrLeave}
          onMouseLeave={handleMouseUpOrLeave}
          onWheel={handleWheel}
        >
          {/* Grid lines */}
          <defs>
            <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#ffffff" strokeWidth="0.5" opacity="0.02" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>

          {/* Background Concentric Rings (Autopoietic Coordinate Guides) */}
          <g opacity="0.25">
            {[0.2, 0.4, 0.6, 0.8, 1.0].map((level, idx) => (
              <circle
                key={`bg-ring-${idx}`}
                cx={dimensions.width / 2}
                cy={dimensions.height / 2}
                r={level * Math.min(dimensions.width, dimensions.height) * 0.45}
                fill="none"
                stroke="#1e293b"
                strokeWidth="0.5"
                strokeDasharray="2,3"
              />
            ))}
            {/* Background Spokes */}
            {Array.from({ length: 8 }).map((_, idx) => {
              const angle = (idx * Math.PI) / 4;
              const maxR = Math.min(dimensions.width, dimensions.height) * 0.45;
              const x2 = dimensions.width / 2 + maxR * Math.cos(angle);
              const y2 = dimensions.height / 2 + maxR * Math.sin(angle);
              const x1 = dimensions.width / 2 - maxR * Math.cos(angle);
              const y1 = dimensions.height / 2 - maxR * Math.sin(angle);
              return (
                <line
                  key={`bg-spoke-${idx}`}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke="#1e293b"
                  strokeWidth="0.5"
                  strokeDasharray="1,4"
                />
              );
            })}
          </g>

          {/* Links */}
          {simLinks.map((link, idx) => {
            const srcNode = simNodes.find((n) => n.id === link.source)
            const tgtNode = simNodes.find((n) => n.id === link.target)
            if (!srcNode || !tgtNode) return null

            const isActive = isLinkActive(link)
            const isResonance = link.type === "resonance"
            const isProposed = srcNode.isProposed || tgtNode.isProposed
            const isProposedResonance = isResonance && link.status === "proposed"

            // Determine if this is a link to an alternate branch splitting off from the active path
            const srcId = parseInt(link.source)
            const tgtId = parseInt(link.target)
            const isFuture = !isNaN(srcId) && !isNaN(tgtId) && activePathIds.has(srcId) && !activePathIds.has(tgtId) && link.type === "parent"
            const futureColor = tgtNode.speaker === "apparatus" ? "#a892ee" : "#6bc28c"

            let strokeColor = "#1e293b" // Dark grey slate for standard inactive links
            let strokeWidth = "0.4"
            let strokeDash = ""
            let opacity = 0.4

            if (isActive) {
              strokeColor = "#6bc28c" // Cohesive green for active path
              strokeWidth = "0.8"
              opacity = 0.85
            } else if (isFuture) {
              strokeColor = futureColor // Color of the child branch speaker
              strokeDash = "2,2" // Dotted line
              strokeWidth = "0.8"
              opacity = 0.8
            } else if (isProposed) {
              strokeColor = "#e09b67" // Peach proposed branches
              strokeDash = "2,2"
              strokeWidth = "0.5"
              opacity = 0.35
            } else if (isResonance) {
              if (isProposedResonance) {
                strokeColor = "#e09b67" // Peach proposed resonance link
                strokeDash = "1,3"
                strokeWidth = "0.7"
                opacity = 0.7
              } else {
                strokeColor = "#94a3b8" // Slate blue for active resonance cross-links
                strokeDash = "3,3"
                strokeWidth = "0.5"
                opacity = 0.45
              }
            }

            return (
              <g key={`link-${idx}`}>
                {isResonance && (
                  <line
                    x1={srcNode.x}
                    y1={srcNode.y}
                    x2={tgtNode.x}
                    y2={tgtNode.y}
                    stroke="transparent"
                    strokeWidth="6"
                    className="cursor-pointer"
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedLink(link)
                      setSelectedLinkPos({
                        x: (srcNode.x + tgtNode.x) / 2,
                        y: (srcNode.y + tgtNode.y) / 2,
                      })
                    }}
                  />
                )}
                <line
                  x1={srcNode.x}
                  y1={srcNode.y}
                  x2={tgtNode.x}
                  y2={tgtNode.y}
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  strokeDasharray={strokeDash}
                  opacity={opacity}
                  className={`transition-all duration-300 ${isProposedResonance ? "animate-pulse" : ""}`}
                />
              </g>
            )
          })}

          {/* Nodes */}
          {simNodes.map((node) => {
            const isActive = node.dbId ? activePathIds.has(node.dbId) : false
            const isLeaf = activeMessageId === node.dbId
            const isFuture = node.parentMsgId !== null && node.parentMsgId !== undefined && activePathIds.has(node.parentMsgId) && !isActive && !node.isProposed
            const isHovered = hoveredNode?.id === node.id
            const nodeNotes = notes.filter((n) => n.message_id === node.dbId)

            let fill = "#0a0a0c"
            let stroke = "#3f3f4e"
            let strokeWidth = "0.6"
            let radius = "2.0"
            let strokeDash = ""
            let nodeClass = "transition-all duration-200 cursor-pointer"

            if (node.isProposed) {
              fill = "#0a0a0c"
              stroke = "#e09b67" // Peach proposed branch
              strokeWidth = "0.8"
              radius = "3.2"
              nodeClass += " animate-pulse stroke-dasharray-[2,2]"
            } else if (node.speaker === "human") {
              if (isActive) {
                fill = isLeaf ? "#152a1d" : "#0a0a0c" // subtle dark green fill for active leaf
                stroke = "#6bc28c" // Green for active user msg
                strokeWidth = isLeaf ? "1.5" : "1.0"
                radius = isLeaf ? "4.5" : "3.2"
              } else if (isFuture) {
                fill = "#0a0a0c"
                stroke = "#6bc28c" // Green for future option
                strokeWidth = "1.0"
                radius = "3.2"
                strokeDash = "2,1.5" // Dashed circle outline
              } else {
                fill = "#0a0a0c"
                stroke = "#6bc28c" // Clean green border
                strokeWidth = "0.7"
                radius = "2.2"
              }
            } else if (node.speaker === "apparatus") {
              if (isActive) {
                fill = isLeaf ? "#211a36" : "#0a0a0c" // subtle dark purple fill for active leaf
                stroke = "#a892ee" // Purple for active apparatus msg
                strokeWidth = isLeaf ? "1.5" : "1.0"
                radius = isLeaf ? "4.5" : "3.2"
              } else if (isFuture) {
                fill = "#0a0a0c"
                stroke = "#a892ee" // Purple for future option
                strokeWidth = "1.0"
                radius = "3.2"
                strokeDash = "2,1.5" // Dashed circle outline
              } else {
                fill = "#0a0a0c"
                stroke = "#a892ee" // Clean purple border
                strokeWidth = "0.7"
                radius = "2.2"
              }
            } else {
              // System
              fill = "#0a0a0c"
              stroke = "#94a3b8" // Slate blue
              radius = "1.8"
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
                    r="9"
                    fill="none"
                    stroke={node.speaker === "human" ? "#6bc28c" : "#a892ee"}
                    strokeWidth="0.5"
                    opacity="0.35"
                    className="animate-ping"
                  />
                )}
                {/* Main Circle */}
                <circle
                  r={isHovered ? String(parseFloat(radius) + 1.0) : radius}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                  strokeDasharray={strokeDash}
                  opacity={isActive || isLeaf || isHovered ? 1 : isFuture ? 0.8 : node.isProposed ? 0.75 : 0.45}
                  className="transition-all duration-150"
                />
                
                {/* Note Indicator Dots */}
                {nodeNotes.map((note, idx) => {
                  const isShared = note.visibility === "shared"
                  const dotColor = isShared ? "#a892ee" : "#facc15" // Purple for shared, yellow/gold for personal
                  
                  // Position around the node boundary (using trigonometry)
                  // Place up to 4 dots at top-right, top-left, bottom-right, bottom-left
                  const angle = -Math.PI / 4 - (idx * Math.PI) / 2
                  const dist = parseFloat(radius) + 2.2
                  const dx = dist * Math.cos(angle)
                  const dy = dist * Math.sin(angle)

                  return (
                    <circle
                      key={`note-dot-${note.id}`}
                      cx={dx}
                      cy={dy}
                      r="1.1"
                      fill={dotColor}
                      stroke="#0a0a0c"
                      strokeWidth="0.3"
                      opacity={isActive || isLeaf || isHovered ? 1.0 : 0.6}
                    />
                  )
                })}
                
                {/* Proposed Title Label */}
                {node.isProposed && (
                  <text
                    y="-9"
                    textAnchor="middle"
                    className="text-[9px] font-mono fill-[#e09b67] select-none font-bold"
                    opacity="0.8"
                  >
                    🚀 {node.title || "Flight"}
                  </text>
                )}
              </g>
            )
          })}
          </g>
        </svg>

        {/* Zoom and Pan Controls Overlay */}
        <div className="absolute bottom-3 right-3 flex flex-col gap-1 z-10 select-none">
          <button
            onClick={handleZoomIn}
            className="w-6 h-6 rounded bg-[#0d0d12]/90 border border-[#1b1b22] text-[#a1a1b5] hover:text-[#00e5ff] hover:border-[#00e5ff] transition-all flex items-center justify-center font-mono text-xs cursor-pointer shadow-lg"
            title="Zoom In"
          >
            +
          </button>
          <button
            onClick={handleZoomOut}
            className="w-6 h-6 rounded bg-[#0d0d12]/90 border border-[#1b1b22] text-[#a1a1b5] hover:text-[#00e5ff] hover:border-[#00e5ff] transition-all flex items-center justify-center font-mono text-xs cursor-pointer shadow-lg"
            title="Zoom Out"
          >
            −
          </button>
          <button
            onClick={handleResetZoom}
            className="w-6 h-6 rounded bg-[#0d0d12]/90 border border-[#1b1b22] text-[#a1a1b5] hover:text-[#00e5ff] hover:border-[#00e5ff] transition-all flex items-center justify-center font-mono text-[9px] cursor-pointer shadow-lg"
            title="Reset View"
          >
            ⟲
          </button>
        </div>

        {/* Hover Tooltip Overlay */}
        {hoveredNode && (
          <div
            className="absolute z-10 px-2 py-1.5 bg-[#0d0d12] border border-[#1b1b22] rounded shadow-xl text-[10px] font-mono max-w-[200px] pointer-events-none select-none"
            style={{
              left: `${Math.min(dimensions.width - 210, Math.max(10, (hoveredNode.x * zoom + pan.x) - 100))}px`,
              top: `${Math.min(dimensions.height - 70, Math.max(10, (hoveredNode.y * zoom + pan.y) - 65))}px`,
            }}
          >
            <div className="flex justify-between border-b border-[#1b1b22] pb-0.5 mb-1">
              <span className={`font-bold capitalize ${
                hoveredNode.speaker === "human" ? "text-[#6bc28c]" : 
                hoveredNode.speaker === "proposed" ? "text-[#e09b67]" : "text-[#a892ee]"
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

        {/* Resonance Link Details Overlay */}
        {selectedLink && selectedLinkPos && (
          <div
            className="absolute z-20 p-2.5 bg-[#0d0d12]/95 border border-[#1b1b22] rounded-lg shadow-2xl text-[10px] font-mono w-[220px]"
            style={{
              left: `${Math.min(dimensions.width - 230, Math.max(10, (selectedLinkPos.x * zoom + pan.x) - 110))}px`,
              top: `${Math.min(dimensions.height - 110, Math.max(10, (selectedLinkPos.y * zoom + pan.y) - 95))}px`,
            }}
          >
            <div className="flex justify-between border-b border-[#1b1b22] pb-1 mb-1">
              <span className={`font-bold ${selectedLink.status === "proposed" ? "text-[#e09b67]" : "text-[#94a3b8]"}`}>
                {selectedLink.status === "proposed" ? "Proposed Resonance" : "Resonance Link"}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setSelectedLink(null)
                  setSelectedLinkPos(null)
                }}
                className="text-[#4b4b5c] hover:text-[#a1a1b5] cursor-pointer"
              >
                ✕
              </button>
            </div>
            
            {selectedLink.justification && (
              <div className="text-[#a1a1b5] mb-2 italic bg-[#07070a] p-1.5 rounded border border-[#14141a]">
                "{selectedLink.justification}"
              </div>
            )}
            
            <div className="flex gap-2">
              {selectedLink.status === "proposed" ? (
                <>
                  <button
                    onClick={async (e) => {
                      e.stopPropagation()
                      if (selectedLink.id && conversationId) {
                        try {
                          await confirmResonanceLink(conversationId, selectedLink.id)
                          refreshTree()
                        } catch (err) {
                          console.error("Failed to confirm link", err)
                        }
                      }
                      setSelectedLink(null)
                      setSelectedLinkPos(null)
                    }}
                    className="flex-1 py-1 rounded bg-[#6bc28c] hover:bg-[#5bb27c] text-black font-bold font-mono text-[9px] cursor-pointer text-center"
                  >
                    Confirm
                  </button>
                  <button
                    onClick={async (e) => {
                      e.stopPropagation()
                      if (selectedLink.id && conversationId) {
                        try {
                          await deleteResonanceLink(conversationId, selectedLink.id)
                          refreshTree()
                        } catch (err) {
                          console.error("Failed to delete link", err)
                        }
                      }
                      setSelectedLink(null)
                      setSelectedLinkPos(null)
                    }}
                    className="flex-1 py-1 rounded bg-[#ef4444] hover:bg-[#dc2626] text-white font-bold font-mono text-[9px] cursor-pointer text-center"
                  >
                    Dismiss
                  </button>
                </>
              ) : (
                <button
                  onClick={async (e) => {
                    e.stopPropagation()
                    if (selectedLink.id && conversationId) {
                      try {
                        await deleteResonanceLink(conversationId, selectedLink.id)
                        refreshTree()
                      } catch (err) {
                        console.error("Failed to delete link", err)
                      }
                    }
                    setSelectedLink(null)
                    setSelectedLinkPos(null)
                  }}
                  className="w-full py-1 rounded bg-[#ef4444] hover:bg-[#dc2626] text-white font-bold font-mono text-[9px] cursor-pointer text-center"
                >
                  Remove Link
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
