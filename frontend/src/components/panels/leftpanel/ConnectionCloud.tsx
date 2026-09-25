import { useEffect, useEffectEvent, useRef, useState, memo } from "react"

import { drawConnectionCloud } from "./ConnectionCloudRenderer"


import type { ChatMessage, NoteInfo, ConversationTreeNode, ConversationTreeLink } from "../../../api/client"
import type { SimNode, SimLink } from "./ConnectionCloudSimulation"
import { computeSettledLayout, getDistanceToSegment } from "./ConnectionCloudSimulation"
import { ConnectionCloudOverlays } from "./ConnectionCloudOverlays"

interface ConnectionCloudProps {
  activeLoadedMessages: ChatMessage[]
  notes: NoteInfo[]
  activeMessageId: number | null
  activePathIds: Set<number>
  setActiveMessageId: (id: number | null) => void
  commitProposedBranch: (parentMsgId: number, content: string) => Promise<any>
  refreshTree: () => void
  conversationId: string
  onNavigateToMessage?: (messageId: number) => void
  agentFlux?: boolean
  onDeleteMessage?: (messageId: number) => void
  treeNodes: ConversationTreeNode[]
  treeLinks: ConversationTreeLink[]
}

function ConnectionCloud({
  activeLoadedMessages,
  notes,
  activeMessageId,
  activePathIds,
  setActiveMessageId,
  commitProposedBranch,
  refreshTree,
  conversationId,
  onNavigateToMessage,
  agentFlux,
  onDeleteMessage,
  treeNodes,
  treeLinks,
}: ConnectionCloudProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const transitionTimerRef = useRef<number | null>(null)

  const [dimensions, setDimensions] = useState({ width: 300, height: 300 })
  const dimensionsRef = useRef(dimensions)
  useEffect(() => { dimensionsRef.current = dimensions }, [dimensions])
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

  const [simulateSettling, setSimulateSettling] = useState<boolean>(() => {
    try {
      return localStorage.getItem("aaa_simulate_settling") === "true"
    } catch {
      return false
    }
  })

  // Zoom and pan — stored in refs for smooth interaction without re-renders
  const zoomRef = useRef(1)
  const panRef = useRef({ x: 0, y: 0 })
  const [redrawTick, setRedrawTick] = useState(0)

  const [viewport, setViewport] = useState({ zoom: 1, pan: { x: 0, y: 0 } })
  const requestRedraw = () => {
    setRedrawTick((t) => t + 1)
    setViewport({ zoom: zoomRef.current, pan: { ...panRef.current } })
  }

  // Right-click context menu for message deletion
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; node: SimNode } | null>(null)
  const [isPanning, setIsPanning] = useState(false)
  const panStartRef = useRef({ x: 0, y: 0 })

  // Build nodes and links from props treeNodes, treeLinks, and inline proposals
  const toggleSimulateSettling = () => {
    setSimulateSettling((prev) => {
      const next = !prev
      try {
        localStorage.setItem("aaa_simulate_settling", String(next))
      } catch (err) {
        console.error("Failed to write to localStorage:", err)
      }
      return next
    })
  }

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

  useEffect(() => () => {
    if (transitionTimerRef.current !== null) cancelAnimationFrame(transitionTimerRef.current)
  }, [])

  // Animates transition between layouts in static mode
  const startLayoutTransition = (targetNodes: SimNode[]) => {
    if (transitionTimerRef.current) {
      cancelAnimationFrame(transitionTimerRef.current)
    }

    if (simNodes.length === 0) {
      setSimNodes(targetNodes)
      return
    }

    const startTime = performance.now()
    const duration = 400 // 400ms transition time

    const startPositions: Record<string, { x: number; y: number }> = {}
    simNodes.forEach((node) => {
      startPositions[node.id] = { x: node.x, y: node.y }
    })

    const animateTransition = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(1, elapsed / duration)
      const ease = 1 - Math.pow(1 - progress, 3) // ease-out cubic

      setSimNodes(() => {
        return targetNodes.map((target) => {
          const start = startPositions[target.id]
          if (!start) {
            const parentPos = target.parentMsgId ? startPositions[String(target.parentMsgId)] : null
            const startX = parentPos ? parentPos.x : target.targetX || target.x
            const startY = parentPos ? parentPos.y : target.targetY || target.y
            return {
              ...target,
              x: startX + (target.x - startX) * ease,
              y: startY + (target.y - startY) * ease,
            }
          }
          return {
            ...target,
            x: start.x + (target.x - start.x) * ease,
            y: start.y + (target.y - start.y) * ease,
          }
        })
      })

      if (progress < 1) {
        transitionTimerRef.current = requestAnimationFrame(animateTransition)
      } else {
        transitionTimerRef.current = null
      }
    }

    transitionTimerRef.current = requestAnimationFrame(animateTransition)
  }

  const transitionLayout = useEffectEvent(startLayoutTransition)

  // Build nodes and links from local treeNodes, treeLinks, and inline proposals
  useEffect(() => {
    if (treeNodes.length === 0) {
      setSimNodes([])
      setSimLinks([])
      return
    }

    const newNodes: SimNode[] = []
    const newLinks: SimLink[] = []

    // 1. Add all fetched tree nodes
    for (let i = 0; i < treeNodes.length; i++) {
      const node = treeNodes[i]
      const idStr = String(node.id)

      newNodes.push({
        id: idStr,
        dbId: node.id,
        speaker: node.speaker,
        content: node.content,
        isProposed: false,
        parentMsgId: node.parent_message_id,
        x: 0,
        y: 0,
        vx: 0,
        vy: 0,
      })

      // Add parent links from tree nodes parent_message_id
      if (node.parent_message_id !== null && node.parent_message_id !== undefined) {
        newLinks.push({
          source: String(node.parent_message_id),
          target: idStr,
          type: "parent",
        })
      }
    }

    // 2. Extract and merge proposed branches from activeLoadedMessages in frontend memory
    activeLoadedMessages.forEach((m) => {
      const idStr = String(m.id)
      if (m.proposed_branches && m.proposed_branches.length > 0) {
        m.proposed_branches.forEach((b, idx) => {
          const propIdStr = `proposed_${m.id}_${idx}`

          // Only add if not already in nodes
          if (!newNodes.some((n) => n.id === propIdStr)) {
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
              type: "parent",
            })
          }
        })
      }
    })

    // 3. Calculate concentric target coordinates for radial tree layout
    const totalNodes = newNodes.length
    const cx = dimensions.width / 2
    const cy = dimensions.height / 2
    const baseRadius = Math.min(dimensions.width, dimensions.height) * 0.45

    // Build parent-child mapping for structure
    const nodeMap = new Map<string, SimNode>()
    newNodes.forEach((n) => nodeMap.set(n.id, n))

    const childrenMap = new Map<string, string[]>()
    const childToParent = new Map<string, string>()

    newNodes.forEach((n) => {
      if (n.parentMsgId !== null && n.parentMsgId !== undefined) {
        const parentId = String(n.parentMsgId)
        if (nodeMap.has(parentId)) {
          childToParent.set(n.id, parentId)
          if (!childrenMap.has(parentId)) {
            childrenMap.set(parentId, [])
          }
          childrenMap.get(parentId)!.push(n.id)
        }
      }
    })

    // Identify roots
    const roots = newNodes.filter((n) => !childToParent.has(n.id)).map((n) => n.id)

    // Calculate subtree weights (count of leaf descendants)
    const subtreeWeights = new Map<string, number>()
    const calculateWeight = (id: string): number => {
      const children = childrenMap.get(id) || []
      if (children.length === 0) {
        subtreeWeights.set(id, 1)
        return 1
      }
      let weight = 0
      children.forEach((childId) => {
        weight += calculateWeight(childId)
      })
      subtreeWeights.set(id, weight)
      return weight
    }
    roots.forEach((rootId) => calculateWeight(rootId))

    // Calculate depths
    const nodeDepths = new Map<string, number>()
    const calculateDepths = (id: string, depth: number) => {
      nodeDepths.set(id, depth)
      const children = childrenMap.get(id) || []
      children.forEach((childId) => calculateDepths(childId, depth + 1))
    }
    roots.forEach((rootId) => calculateDepths(rootId, 0))

    let maxDepth = 0
    nodeDepths.forEach((d) => {
      if (d > maxDepth) maxDepth = d
    })

    // Assign positions recursively with spiral/zigzag layout to prevent overlaps
    const assignPositions = (
      id: string,
      minAngle: number,
      maxAngle: number,
      parentAngle: number,
      direction: 1 | -1
    ) => {
      const node = nodeMap.get(id)
      if (!node) return

      const depth = nodeDepths.get(id) || 0
      const radius = depth > 0 ? 20 + (depth / (maxDepth || 1)) * (baseRadius - 20) : 0

      let angle = parentAngle
      let nextDirection = direction
      const isFullCircle = (maxAngle - minAngle) >= 2 * Math.PI - 0.01

      if (depth > 0) {
        const targetSpacing = 28
        const step = radius > 0 ? Math.min(0.6, targetSpacing / radius) : 0.6

        if (isFullCircle) {
          angle = parentAngle + step
        } else {
          angle = parentAngle + direction * step
          if (angle > maxAngle) {
            angle = maxAngle - (angle - maxAngle)
            nextDirection = -1
          } else if (angle < minAngle) {
            angle = minAngle + (minAngle - angle)
            nextDirection = 1
          }
        }
      }

      const clampedAngle = isFullCircle ? angle : Math.max(minAngle, Math.min(maxAngle, angle))

      node.targetX = cx + radius * Math.cos(clampedAngle)
      node.targetY = cy + radius * Math.sin(clampedAngle)

      const children = childrenMap.get(id) || []
      if (children.length > 0) {
        const totalWeight = subtreeWeights.get(id) || 1
        const angleSpan = maxAngle - minAngle
        let currentAngle = minAngle

        children.forEach((childId) => {
          const childWeight = subtreeWeights.get(childId) || 1
          const childSpan = (childWeight / totalWeight) * angleSpan
          const nextAngle = currentAngle + childSpan
          assignPositions(childId, currentAngle, nextAngle, clampedAngle, nextDirection)
          currentAngle = nextAngle
        })
      }
    }

    // Distribute roots around 360 degrees
    if (roots.length > 0) {
      let totalRootWeight = 0
      roots.forEach((r) => {
        totalRootWeight += subtreeWeights.get(r) || 1
      })

      let currentAngle = 0
      roots.forEach((rootId) => {
        const rootWeight = subtreeWeights.get(rootId) || 1
        const rootSpan = (rootWeight / totalRootWeight) * 2 * Math.PI
        const centerAngle = currentAngle + rootSpan / 2
        assignPositions(rootId, currentAngle, currentAngle + rootSpan, centerAngle, 1)
        currentAngle += rootSpan
      })
    }

    // Apply target positions to nodes and recover previous positions to prevent jumpiness
    for (let i = 0; i < totalNodes; i++) {
      const node = newNodes[i]
      const prevPos = nodePositionsRef.current[node.id]
      node.x = prevPos ? prevPos.x : (node.targetX || cx)
      node.y = prevPos ? prevPos.y : (node.targetY || cy)
    }

    // 4. Add database retroactive links (resonance links)
    for (const l of treeLinks) {
      const srcStr = String(l.source_id)
      const tgtStr = String(l.target_id)

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

    if (!simulateSettling && newNodes.length > 0) {
      const settledNodes = computeSettledLayout(newNodes, dimensions.width, dimensions.height)
      settledNodes.forEach((n) => {
        nodePositionsRef.current[n.id] = { x: n.x, y: n.y }
      })
      transitionLayout(settledNodes)
    } else {
      setSimNodes(newNodes)
    }
    setSimLinks(newLinks)
  }, [treeNodes, treeLinks, activeLoadedMessages, dimensions.width, dimensions.height, simulateSettling])

  // Run the force simulation loop (Live Mode only)
  useEffect(() => {
    if (!simulateSettling || simNodes.length === 0) return

    let animationFrameId: number
    let alpha = 1.0 // Simulation temperature
    const decay = 0.965 // Cooling rate
    const friction = 0.78
    const repulseStrength = 180
    const springLength = 32
    const springStrength = 0.08

    const runSimulation = () => {
      if (alpha < 0.015) {
        return
      }

      setSimNodes((currentNodes) => {
        const nodes = currentNodes.map((n) => ({ ...n }))
        const nodeMap = new Map<string, SimNode>()
        nodes.forEach((n) => nodeMap.set(n.id, n))

    const cx = dimensionsRef.current.width / 2
    const cy = dimensionsRef.current.height / 2

        // 1. Repulsion force
        for (let i = 0; i < nodes.length; i++) {
          const a = nodes[i]
          for (let j = i + 1; j < nodes.length; j++) {
            const b = nodes[j]
            const dx = b.x - a.x
            const dy = b.y - a.y
            const distSq = dx * dx + dy * dy + 1e-4
            const dist = Math.sqrt(distSq)

            if (dist < 120) {
              const forceFactor = (repulseStrength * alpha) / (distSq * dist)
              const fx = dx * forceFactor
              const fy = dy * forceFactor

              a.vx -= fx
              a.vy -= fy
              b.vx += fx
              b.vy += fy
            }
          }
        }

        // 2. Attraction spring force
        for (const link of simLinks) {
          const a = nodeMap.get(link.source)
          const b = nodeMap.get(link.target)
          if (!a || !b) continue

          const dx = b.x - a.x
          const dy = b.y - a.y
          const dist = Math.sqrt(dx * dx + dy * dy) + 1e-4

          const displacement = dist - springLength
          const forceFactor = (displacement * springStrength * alpha) / dist
          const fx = dx * forceFactor
          const fy = dy * forceFactor

          a.vx += fx
          a.vy += fy
          b.vx -= fx
          b.vy -= fy
        }

        // 3. Anchor force (Spiral layout target)
        const anchorStrength = 0.12
        for (const n of nodes) {
          const tx = n.targetX !== undefined ? n.targetX : cx
          const ty = n.targetY !== undefined ? n.targetY : cy
          n.vx += (tx - n.x) * anchorStrength * alpha
          n.vy += (ty - n.y) * anchorStrength * alpha

          n.x += n.vx
          n.y += n.vy

          n.x = Math.max(15, Math.min(dimensions.width - 15, n.x))
          n.y = Math.max(15, Math.min(dimensions.height - 15, n.y))

          n.vx *= friction
          n.vy *= friction

          nodePositionsRef.current[n.id] = { x: n.x, y: n.y }
        }

        return nodes
      })

      alpha *= decay
      animationFrameId = requestAnimationFrame(runSimulation)
    }

    animationFrameId = requestAnimationFrame(runSimulation)
    return () => cancelAnimationFrame(animationFrameId)
  }, [simulateSettling, simNodes.length, simLinks, dimensions.width, dimensions.height])

  // Canvas drawing loop
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    drawConnectionCloud(canvas, { dimensions, simNodes, simLinks, hoveredNode, activeMessageId, activePathIds, notes, zoom: zoomRef.current, pan: panRef.current })
  }, [simNodes, simLinks, redrawTick, hoveredNode, activeMessageId, activePathIds, notes, dimensions])

  const handleNodeClick = (node: SimNode) => {
    if (node.isProposed) {
      setCommittingNode(node)
      setCommitContent(node.content)
    } else if (node.dbId) {
      if (onNavigateToMessage) {
        onNavigateToMessage(node.dbId)
      } else {
        setActiveMessageId(node.dbId)
      }
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

  // Zoom and pan event handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsPanning(true)
    panStartRef.current = { x: e.clientX - panRef.current.x, y: e.clientY - panRef.current.y }
    setSelectedLink(null)
    setSelectedLinkPos(null)
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mouseX = (e.clientX - rect.left - panRef.current.x) / zoomRef.current
    const mouseY = (e.clientY - rect.top - panRef.current.y) / zoomRef.current

    if (isPanning) {
      panRef.current = {
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y
      }
      requestRedraw()
    } else {
      let found: SimNode | null = null
      for (const node of simNodes) {
        const dx = node.x - mouseX
        const dy = node.y - mouseY
        const radius = node.dbId === activeMessageId ? 4.5 : 3.2
        if (dx * dx + dy * dy <= (radius + 6) * (radius + 6)) {
          found = node
          break
        }
      }
      setHoveredNode(found)
    }
  }

  const handleMouseUpOrLeave = () => {
    setIsPanning(false)
  }

  const handleWheel = (e: WheelEvent) => {
    e.preventDefault()
    const zoomFactor = 1.08
    const nextZoom = Math.max(0.2, Math.min(4.0, e.deltaY < 0 ? zoomRef.current * zoomFactor : zoomRef.current / zoomFactor))

    const cx = dimensions.width / 2
    const cy = dimensions.height / 2
    const scaleRatio = nextZoom / zoomRef.current

    panRef.current = {
      x: cx - (cx - panRef.current.x) * scaleRatio,
      y: cy - (cy - panRef.current.y) * scaleRatio
    }
    zoomRef.current = nextZoom
    requestRedraw()
  }

  const wheelEvent = useEffectEvent(handleWheel)
  // Attach wheel listener non-passively for zoom
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const onWheel = (event: WheelEvent) => wheelEvent(event)
    canvas.addEventListener("wheel", onWheel, { passive: false })
    return () => canvas.removeEventListener("wheel", onWheel)
  }, [])

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    // Dismiss context menu on any click
    setContextMenu(null)
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mouseX = (e.clientX - rect.left - panRef.current.x) / zoomRef.current
    const mouseY = (e.clientY - rect.top - panRef.current.y) / zoomRef.current

    // 1. Check if clicked a node
    let clickedNode: SimNode | null = null
    for (const node of simNodes) {
      const dx = node.x - mouseX
      const dy = node.y - mouseY
      const radius = node.dbId === activeMessageId ? 4.5 : 3.2
      if (dx * dx + dy * dy <= (radius + 6) * (radius + 6)) {
        clickedNode = node
        break
      }
    }

    if (clickedNode) {
      handleNodeClick(clickedNode)
      return
    }

    // 2. Check if clicked a resonance link
    let clickedLink: SimLink | null = null
    for (const link of simLinks) {
      if (link.type !== "resonance") continue
      const srcNode = simNodes.find((n) => n.id === link.source)
      const tgtNode = simNodes.find((n) => n.id === link.target)
      if (!srcNode || !tgtNode) return

      const dist = getDistanceToSegment(mouseX, mouseY, srcNode.x, srcNode.y, tgtNode.x, tgtNode.y)
      if (dist <= 6) {
        clickedLink = link
        break
      }
    }

    if (clickedLink) {
      const srcNode = simNodes.find((n) => n.id === clickedLink!.source)
      const tgtNode = simNodes.find((n) => n.id === clickedLink!.target)
      if (srcNode && tgtNode) {
        setSelectedLink(clickedLink)
        setSelectedLinkPos({
          x: (srcNode.x + tgtNode.x) / 2,
          y: (srcNode.y + tgtNode.y) / 2,
        })
      }
    } else {
      setSelectedLink(null)
      setSelectedLinkPos(null)
    }
  }

  const handleCanvasContextMenu = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!agentFlux || !onDeleteMessage) return
    e.preventDefault()
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mouseX = (e.clientX - rect.left - panRef.current.x) / zoomRef.current
    const mouseY = (e.clientY - rect.top - panRef.current.y) / zoomRef.current

    // Find node under cursor
    for (const node of simNodes) {
      const dx = node.x - mouseX
      const dy = node.y - mouseY
      const radius = node.dbId === activeMessageId ? 4.5 : 3.2
      if (dx * dx + dy * dy <= (radius + 6) * (radius + 6)) {
        if (node.dbId) {
          setContextMenu({ x: e.clientX - rect.left, y: e.clientY - rect.top, node })
        }
        break
      }
    }
  }

  const handleDeleteNode = () => {
    if (contextMenu?.node.dbId && onDeleteMessage) {
      onDeleteMessage(contextMenu.node.dbId)
    }
    setContextMenu(null)
  }

  const handleZoomIn = (e: React.MouseEvent) => {
    e.stopPropagation()
    const nextZoom = Math.min(4.0, zoomRef.current * 1.2)
    const cx = dimensions.width / 2
    const cy = dimensions.height / 2
    const scaleRatio = nextZoom / zoomRef.current
    panRef.current = {
      x: cx - (cx - panRef.current.x) * scaleRatio,
      y: cy - (cy - panRef.current.y) * scaleRatio
    }
    zoomRef.current = nextZoom
    requestRedraw()
  }

  const handleZoomOut = (e: React.MouseEvent) => {
    e.stopPropagation()
    const nextZoom = Math.max(0.2, zoomRef.current / 1.2)
    const cx = dimensions.width / 2
    const cy = dimensions.height / 2
    const scaleRatio = nextZoom / zoomRef.current
    panRef.current = {
      x: cx - (cx - panRef.current.x) * scaleRatio,
      y: cy - (cy - panRef.current.y) * scaleRatio
    }
    zoomRef.current = nextZoom
    requestRedraw()
  }

  const handleResetZoom = (e: React.MouseEvent) => {
    e.stopPropagation()
    zoomRef.current = 1
    panRef.current = { x: 0, y: 0 }
    requestRedraw()
  }

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full flex flex-col"
    >
      {/* Header — terminal style */}
      <div className="px-3 py-2 flex justify-between items-center select-none">
        <span className="text-xs font-mono font-bold uppercase tracking-wider text-semantic-header">
          Connection Cloud
        </span>
        <div className="flex items-center gap-3">
          <button
            onClick={toggleSimulateSettling}
            className={`text-[9px] font-mono cursor-pointer select-none transition-colors ${
              simulateSettling
                ? "text-action-hover font-bold"
                : "text-action-dim hover:text-action-hover"
            }`}
            title={simulateSettling ? "Simulating settling in real-time" : "Instant static layout"}
          >
            [{simulateSettling ? "live" : "static"}]
          </button>
          <span className="text-[10px] font-mono text-[#555]">
            {simNodes.filter((n) => !n.isProposed).length} nodes | {treeLinks.length} cross-links
          </span>
        </div>
      </div>

      {/* Canvas viewport */}
      <div className="flex-1 relative cursor-grab active:cursor-grabbing">
        <canvas
          ref={canvasRef}
          className="w-full h-full block"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUpOrLeave}
          onMouseLeave={handleMouseUpOrLeave}
          onClick={handleCanvasClick}
          onContextMenu={handleCanvasContextMenu}
        />

        <ConnectionCloudOverlays
          contextMenu={contextMenu}
          handleDeleteNode={handleDeleteNode}
          hoveredNode={hoveredNode}
          dimensions={dimensions}
          zoom={viewport.zoom}
          pan={viewport.pan}
          committingNode={committingNode}
          setCommittingNode={setCommittingNode}
          commitContent={commitContent}
          setCommitContent={setCommitContent}
          handleCommitSubmit={handleCommitSubmit}
          isCommitLoading={isCommitLoading}
          selectedLink={selectedLink}
          selectedLinkPos={selectedLinkPos}
          setSelectedLink={setSelectedLink}
          setSelectedLinkPos={setSelectedLinkPos}
          conversationId={conversationId}
          refreshTree={refreshTree}
          handleZoomIn={handleZoomIn}
          handleZoomOut={handleZoomOut}
          handleResetZoom={handleResetZoom}
        />
      </div>
    </div>
  )
}

const MemoizedConnectionCloud = memo(ConnectionCloud)
export default MemoizedConnectionCloud

