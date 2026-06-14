import { useEffect, useRef, useState, memo, useCallback } from "react"
import type { ChatMessage, NoteInfo, ConversationTreeNode, ConversationTreeLink } from "../../../api/client"
import { confirmResonanceLink, deleteResonanceLink, getConversationTree } from "../../../api/client"

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
  targetR?: number
}

interface SimLink {
  id?: string
  source: string
  target: string
  type: "parent" | "resonance"
  status?: "active" | "proposed"
  justification?: string
}



function computeSettledLayout(
  initialNodes: SimNode[],
  width: number,
  height: number
): SimNode[] {
  const cx = width / 2
  const cy = height / 2
  return initialNodes.map((n) => ({
    ...n,
    x: n.targetX !== undefined ? n.targetX : cx,
    y: n.targetY !== undefined ? n.targetY : cy,
    vx: 0,
    vy: 0,
  }))
}

function getDistanceToSegment(x: number, y: number, x1: number, y1: number, x2: number, y2: number): number {
  const A = x - x1
  const B = y - y1
  const C = x2 - x1
  const D = y2 - y1

  const dot = A * C + B * D
  const lenSq = C * C + D * D
  let param = -1
  if (lenSq !== 0) {
    param = dot / lenSq
  }

  let xx, yy
  if (param < 0) {
    xx = x1
    yy = y1
  } else if (param > 1) {
    xx = x2
    yy = y2
  } else {
    xx = x1 + param * C
    yy = y1 + param * D
  }

  const dx = x - xx
  const dy = y - yy
  return Math.sqrt(dx * dx + dy * dy)
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
}: ConnectionCloudProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const transitionTimerRef = useRef<number | null>(null)

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

  const [simulateSettling, setSimulateSettling] = useState<boolean>(() => {
    try {
      return localStorage.getItem("aaa_simulate_settling") === "true"
    } catch {
      return false
    }
  })

  // Zoom and pan state
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })

  // Right-click context menu for message deletion
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; node: SimNode } | null>(null)
  const [isPanning, setIsPanning] = useState(false)
  const panStartRef = useRef({ x: 0, y: 0 })

  const [treeNodes, setTreeNodes] = useState<ConversationTreeNode[]>([])
  const [treeLinks, setTreeLinks] = useState<ConversationTreeLink[]>([])

  const fetchTree = useCallback(async () => {
    if (!conversationId) return
    try {
      const data = await getConversationTree(conversationId)
      setTreeNodes(data.nodes)
      setTreeLinks(data.links)
    } catch (err) {
      console.error("Failed to fetch tree:", err)
    }
  }, [conversationId])

  useEffect(() => {
    fetchTree()
  }, [conversationId, activeLoadedMessages.length, fetchTree])

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

  // Helper to check if a link is part of the active path
  const isLinkActive = (link: SimLink) => {
    const srcId = parseInt(link.source)
    const tgtId = parseInt(link.target)
    if (isNaN(srcId) || isNaN(tgtId)) return false
    return activePathIds.has(srcId) && activePathIds.has(tgtId)
  }

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
      startLayoutTransition(settledNodes)
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

        const cx = dimensions.width / 2
        const cy = dimensions.height / 2

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
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = dimensions.width * dpr
    canvas.height = dimensions.height * dpr
    canvas.style.width = `${dimensions.width}px`
    canvas.style.height = `${dimensions.height}px`

    ctx.clearRect(0, 0, dimensions.width, dimensions.height)
    ctx.scale(dpr, dpr)

    // Save state for panning/zooming
    ctx.save()
    ctx.translate(pan.x, pan.y)
    ctx.scale(zoom, zoom)

    // 1. Draw Infinite Grid inside coordinate system
    ctx.strokeStyle = "rgba(255, 255, 255, 0.025)"
    ctx.lineWidth = 0.5
    ctx.setLineDash([])
    
    const gridSize = 20
    const startX = Math.floor((-pan.x / zoom) / gridSize) * gridSize
    const endX = Math.ceil(((dimensions.width - pan.x) / zoom) / gridSize) * gridSize
    const startY = Math.floor((-pan.y / zoom) / gridSize) * gridSize
    const endY = Math.ceil(((dimensions.height - pan.y) / zoom) / gridSize) * gridSize

    for (let x = startX; x <= endX; x += gridSize) {
      ctx.beginPath()
      ctx.moveTo(x, startY)
      ctx.lineTo(x, endY)
      ctx.stroke()
    }
    for (let y = startY; y <= endY; y += gridSize) {
      ctx.beginPath()
      ctx.moveTo(startX, y)
      ctx.lineTo(endX, y)
      ctx.stroke()
    }

    // 2. Draw Concentric Rings (Autopoietic Coordinate Guides)
    ctx.strokeStyle = "#4a576d"
    ctx.lineWidth = 0.5
    ctx.globalAlpha = 0.2
    ctx.setLineDash([2, 3])
    
    const cx = dimensions.width / 2
    const cy = dimensions.height / 2
    const baseRadius = Math.min(dimensions.width, dimensions.height) * 0.45
    const ringLevels = [0.2, 0.4, 0.6, 0.8, 1.0]
    
    ringLevels.forEach((level) => {
      ctx.beginPath()
      ctx.arc(cx, cy, level * baseRadius, 0, 2 * Math.PI)
      ctx.stroke()
    })

    // 3. Draw Spokes
    ctx.setLineDash([1, 4])
    for (let idx = 0; idx < 8; idx++) {
      const angle = (idx * Math.PI) / 4
      const maxR = baseRadius
      const x2 = cx + maxR * Math.cos(angle)
      const y2 = cy + maxR * Math.sin(angle)
      const x1 = cx - maxR * Math.cos(angle)
      const y1 = cy - maxR * Math.sin(angle)

      ctx.beginPath()
      ctx.moveTo(x1, y1)
      ctx.lineTo(x2, y2)
      ctx.stroke()
    }

    ctx.setLineDash([])
    ctx.globalAlpha = 1.0

    // PRE-CREATE MAPS FOR O(1) LOOKUPS
    const nodeMap = new Map<string, SimNode>()
    simNodes.forEach((n) => nodeMap.set(n.id, n))

    const notesMap = new Map<number, NoteInfo[]>()
    notes.forEach((note) => {
      if (note.message_id !== undefined && note.message_id !== null) {
        if (!notesMap.has(note.message_id)) {
          notesMap.set(note.message_id, [])
        }
        notesMap.get(note.message_id)!.push(note)
      }
    })

    // 4. Draw Links
    simLinks.forEach((link) => {
      const srcNode = nodeMap.get(link.source)
      const tgtNode = nodeMap.get(link.target)
      if (!srcNode || !tgtNode) return

      const isActive = isLinkActive(link)
      const isResonance = link.type === "resonance"
      const isProposed = srcNode.isProposed || tgtNode.isProposed
      const isProposedResonance = isResonance && link.status === "proposed"

      const srcId = parseInt(link.source)
      const tgtId = parseInt(link.target)
      const isFuture = !isNaN(srcId) && !isNaN(tgtId) && activePathIds.has(srcId) && !activePathIds.has(tgtId) && link.type === "parent"
      const futureColor = tgtNode.speaker === "apparatus" ? "#a892ee" : "#6bc28c"

      let strokeColor = tgtNode.speaker === "apparatus" ? "#a892ee" : "#6bc28c"
      let strokeWidth = 0.4
      let strokeDash: number[] = []
      let opacity = 0.25

      if (isActive) {
        strokeColor = "#6bc28c"
        strokeWidth = 0.8
        opacity = 0.85
      } else if (isFuture) {
        strokeColor = futureColor
        strokeDash = [2, 2]
        strokeWidth = 0.8
        opacity = 0.8
      } else if (isProposed) {
        strokeColor = "#e09b67"
        strokeDash = [2, 2]
        strokeWidth = 0.5
        opacity = 0.35
      } else if (isResonance) {
        if (isProposedResonance) {
          strokeColor = "#e09b67"
          strokeDash = [1, 3]
          strokeWidth = 0.7
          opacity = 0.7
        } else {
          strokeColor = "#94a3b8"
          strokeDash = [3, 3]
          strokeWidth = 0.5
          opacity = 0.45
        }
      }

      ctx.strokeStyle = strokeColor
      ctx.lineWidth = strokeWidth
      ctx.globalAlpha = opacity
      if (strokeDash.length > 0) {
        ctx.setLineDash(strokeDash)
      } else {
        ctx.setLineDash([])
      }

      ctx.beginPath()
      ctx.moveTo(srcNode.x, srcNode.y)
      if (isResonance) {
        // Draw curved arc for resonance links to distinguish them from the main tree structure
        const dx = tgtNode.x - srcNode.x
        const dy = tgtNode.y - srcNode.y
        const dist = Math.sqrt(dx * dx + dy * dy) + 1e-4
        const mx = (srcNode.x + tgtNode.x) / 2
        const my = (srcNode.y + tgtNode.y) / 2
        // Normal vector pointing outwards to offset control point
        const nx = -dy / dist
        const ny = dx / dist
        const offset = dist * 0.15 // 15% curvature
        const ctrlX = mx + nx * offset
        const ctrlY = my + ny * offset
        ctx.quadraticCurveTo(ctrlX, ctrlY, tgtNode.x, tgtNode.y)
      } else {
        ctx.lineTo(tgtNode.x, tgtNode.y)
      }
      ctx.stroke()
    })

    ctx.setLineDash([])
    ctx.globalAlpha = 1.0

    // 5. Draw Nodes
    simNodes.forEach((node) => {
      const isActive = node.dbId ? activePathIds.has(node.dbId) : false
      const isLeaf = activeMessageId === node.dbId
      const isFuture = node.parentMsgId !== null && node.parentMsgId !== undefined && activePathIds.has(node.parentMsgId) && !isActive && !node.isProposed
      const isHovered = hoveredNode?.id === node.id
      const nodeNotes = notesMap.get(node.dbId || -1) || []

      let fill = "#0a0a0c"
      let stroke = "#3f3f4e"
      let strokeWidth = 0.6
      let radius = 2.0
      let strokeDash: number[] = []

      if (node.isProposed) {
        fill = "#0a0a0c"
        stroke = "#e09b67"
        strokeWidth = 0.8
        radius = 3.2
        strokeDash = [2, 2]
      } else if (node.speaker === "human") {
        if (isActive) {
          fill = isLeaf ? "#152a1d" : "#0a0a0c"
          stroke = "#6bc28c"
          strokeWidth = isLeaf ? 1.5 : 1.0
          radius = isLeaf ? 4.5 : 3.2
        } else if (isFuture) {
          fill = "#0a0a0c"
          stroke = "#6bc28c"
          strokeWidth = 1.0
          radius = 3.2
          strokeDash = [2, 1.5]
        } else {
          fill = "#0a0a0c"
          stroke = "#6bc28c"
          strokeWidth = 0.7
          radius = 2.2
        }
      } else if (node.speaker === "apparatus") {
        if (isActive) {
          fill = isLeaf ? "#211a36" : "#0a0a0c"
          stroke = "#a892ee"
          strokeWidth = isLeaf ? 1.5 : 1.0
          radius = isLeaf ? 4.5 : 3.2
        } else if (isFuture) {
          fill = "#0a0a0c"
          stroke = "#a892ee"
          strokeWidth = 1.0
          radius = 3.2
          strokeDash = [2, 1.5]
        } else {
          fill = "#0a0a0c"
          stroke = "#a892ee"
          strokeWidth = 0.7
          radius = 2.2
        }
      } else {
        fill = "#0a0a0c"
        stroke = "#94a3b8"
        radius = 1.8
      }

      const drawRadius = isHovered ? radius + 1.0 : radius
      const drawOpacity = isActive || isLeaf || isHovered ? 1.0 : isFuture ? 0.8 : node.isProposed ? 0.75 : 0.45

      ctx.globalAlpha = drawOpacity

      // Static premium glowing concentric rings for active leaf node
      if (isLeaf) {
        ctx.beginPath()
        ctx.arc(node.x, node.y, radius + 4.5, 0, 2 * Math.PI)
        ctx.strokeStyle = node.speaker === "human" ? "#6bc28c" : "#a892ee"
        ctx.lineWidth = 0.8
        ctx.globalAlpha = 0.3
        ctx.stroke()

        ctx.beginPath()
        ctx.arc(node.x, node.y, radius + 2.0, 0, 2 * Math.PI)
        ctx.strokeStyle = node.speaker === "human" ? "#6bc28c" : "#a892ee"
        ctx.lineWidth = 0.5
        ctx.globalAlpha = 0.5
        ctx.stroke()

        ctx.globalAlpha = drawOpacity
      }

      // Draw node circle
      ctx.beginPath()
      ctx.arc(node.x, node.y, drawRadius, 0, 2 * Math.PI)
      ctx.fillStyle = fill
      ctx.fill()
      
      ctx.strokeStyle = stroke
      ctx.lineWidth = strokeWidth
      if (strokeDash.length > 0) {
        ctx.setLineDash(strokeDash)
      } else {
        ctx.setLineDash([])
      }
      ctx.stroke()
      ctx.setLineDash([])

      // Note Indicator Dots
      nodeNotes.forEach((note, idx) => {
        const isAgent = note.visibility === "agent"
        const isShared = note.visibility === "shared"
        const dotColor = isAgent ? "#22d3ee" : isShared ? "#a892ee" : "#facc15"

        const angle = -Math.PI / 4 - (idx * Math.PI) / 2
        const dist = drawRadius + 2.2
        const dx = node.x + dist * Math.cos(angle)
        const dy = node.y + dist * Math.sin(angle)

        ctx.beginPath()
        ctx.arc(dx, dy, 1.1, 0, 2 * Math.PI)
        ctx.fillStyle = dotColor
        ctx.fill()
        
        ctx.strokeStyle = "#0a0a0c"
        ctx.lineWidth = 0.3
        ctx.stroke()
      })

      // Proposed Title Label
      if (node.isProposed) {
        ctx.font = "bold 9px monospace"
        ctx.fillStyle = "#e09b67"
        ctx.textAlign = "center"
        ctx.textBaseline = "bottom"
        ctx.globalAlpha = 0.8
        ctx.fillText(`🚀 ${node.title || "Flight"}`, node.x, node.y - drawRadius - 4)
      }
    })

    ctx.restore()
  }, [simNodes, simLinks, zoom, pan, hoveredNode, activeMessageId, activePathIds, notes, dimensions])

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
    panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }
    setSelectedLink(null)
    setSelectedLinkPos(null)
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mouseX = (e.clientX - rect.left - pan.x) / zoom
    const mouseY = (e.clientY - rect.top - pan.y) / zoom

    if (isPanning) {
      setPan({
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y
      })
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

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault()
    const zoomFactor = 1.08
    const nextZoom = Math.max(0.2, Math.min(4.0, e.deltaY < 0 ? zoom * zoomFactor : zoom / zoomFactor))

    const cx = dimensions.width / 2
    const cy = dimensions.height / 2
    const scaleRatio = nextZoom / zoom

    setPan({
      x: cx - (cx - pan.x) * scaleRatio,
      y: cy - (cy - pan.y) * scaleRatio
    })
    setZoom(nextZoom)
  }

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    // Dismiss context menu on any click
    setContextMenu(null)
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mouseX = (e.clientX - rect.left - pan.x) / zoom
    const mouseY = (e.clientY - rect.top - pan.y) / zoom

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
    const mouseX = (e.clientX - rect.left - pan.x) / zoom
    const mouseY = (e.clientY - rect.top - pan.y) / zoom

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
      className="relative w-full h-full flex flex-col"
    >
      {/* Header — terminal style */}
      <div className="px-3 py-2 flex justify-between items-center select-none">
        <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#6c6c8a]">
          Connection Cloud
        </span>
        <div className="flex items-center gap-3">
          <button
            onClick={toggleSimulateSettling}
            className={`text-[9px] font-mono cursor-pointer select-none transition-colors ${
              simulateSettling
                ? "text-[#ec4899]"
                : "text-[#666] hover:text-[#888]"
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
          onWheel={handleWheel}
          onClick={handleCanvasClick}
          onContextMenu={handleCanvasContextMenu}
        />

        {/* Right-click context menu — terminal style */}
        {contextMenu && (
          <div
            className="absolute z-20 bg-[#0d0d12]/95 py-1 px-0"
            style={{ left: contextMenu.x, top: contextMenu.y }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={handleDeleteNode}
              className="text-left px-3 py-1 text-[10px] font-mono text-[#ef4444] hover:text-[#f87171] transition-colors cursor-pointer select-none"
            >
              [delete node]
            </button>
          </div>
        )}

        {/* Zoom Controls — terminal style */}
        <div className="absolute bottom-3 right-3 flex flex-col gap-1 z-10 select-none">
          <button onClick={handleZoomIn} className="font-mono text-xs text-[#666] hover:text-[#00e5ff] cursor-pointer transition-colors"
            title="Zoom In">[ + ]</button>
          <button onClick={handleZoomOut} className="font-mono text-xs text-[#666] hover:text-[#00e5ff] cursor-pointer transition-colors"
            title="Zoom Out">[ − ]</button>
          <button onClick={handleResetZoom} className="font-mono text-[9px] text-[#666] hover:text-[#00e5ff] cursor-pointer transition-colors"
            title="Reset View">[ ⟲ ]</button>
        </div>

        {/* Hover Tooltip — minimal */}
        {hoveredNode && (
          <div
            className="absolute z-10 px-2 py-1.5 bg-[#0d0d12]/95 text-[10px] font-mono max-w-[200px] pointer-events-none select-none"
            style={{
              left: `${Math.min(dimensions.width - 210, Math.max(10, (hoveredNode.x * zoom + pan.x) - 100))}px`,
              top: `${Math.min(dimensions.height - 70, Math.max(10, (hoveredNode.y * zoom + pan.y) - 65))}px`,
            }}
          >
            <div className="flex justify-between pb-0.5 mb-1">
              <span className={`font-bold capitalize ${hoveredNode.speaker === "human" ? "text-[#6bc28c]" :
                hoveredNode.speaker === "proposed" ? "text-[#e09b67]" : "text-[#a892ee]"
                }`}>
                {hoveredNode.speaker === "proposed" ? `Agential Proposal: ${hoveredNode.title}` : hoveredNode.speaker}
              </span>
              <span className="text-[#555] ml-2">
                {hoveredNode.isProposed ? "Consent Required" : `ID: ${hoveredNode.dbId}`}
              </span>
            </div>
            <div className="text-[#94a3b8] line-clamp-2">
              {hoveredNode.content}
            </div>
          </div>
        )}

        {/* Branch Commit Modal — minimal */}
        {committingNode && (
          <div className="absolute inset-0 bg-[#09090b]/80 flex flex-col justify-end p-3 z-20">
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-center">
                <span className="text-[10px] font-mono font-bold text-[#ec4899] uppercase tracking-wider">
                  [ Commit Line of Flight ]
                </span>
                <button onClick={() => setCommittingNode(null)}
                  className="text-[10px] font-mono text-[#666] hover:text-[#88] cursor-pointer select-none">[cancel]</button>
              </div>
              <div className="text-[10px] font-mono text-[#94a3b8]">
                Topic: <span className="text-[#ccc]">{committingNode.title}</span>
              </div>
              <textarea
                value={commitContent}
                onChange={(e) => setCommitContent(e.target.value)}
                rows={4}
                className="w-full bg-[#08080c] border border-[#1b1b21] p-2 text-xs font-mono text-[#e4e4e7] focus:outline-none focus:border-[#ec4899] resize-none"
              />
              <button
                onClick={handleCommitSubmit}
                disabled={isCommitLoading || !commitContent.trim()}
                className="text-[10px] font-mono text-[#ec4899] hover:text-[#f472b6] disabled:text-[#555] disabled:cursor-not-allowed cursor-pointer select-none self-start"
              >
                {isCommitLoading ? "[committing...]" : "[commit branch to DAG]"}
              </button>
            </div>
          </div>
        )}

        {/* Resonance Link Details — minimal */}
        {selectedLink && selectedLinkPos && (
          <div
            className="absolute z-20 p-2.5 bg-[#0d0d12]/95 text-[10px] font-mono w-[220px]"
            style={{
              left: `${Math.min(dimensions.width - 230, Math.max(10, (selectedLinkPos.x * zoom + pan.x) - 110))}px`,
              top: `${Math.min(dimensions.height - 110, Math.max(10, (selectedLinkPos.y * zoom + pan.y) - 95))}px`,
            }}
          >
            <div className="flex justify-between pb-1 mb-1">
              <span className={`font-bold ${selectedLink.status === "proposed" ? "text-[#e09b67]" : "text-[#94a3b8]"}`}>
                {selectedLink.status === "proposed" ? "Proposed Resonance" : "Resonance Link"}
              </span>
              <button
                onClick={(e) => { e.stopPropagation(); setSelectedLink(null); setSelectedLinkPos(null) }}
                className="text-[#666] hover:text-[#888] cursor-pointer select-none">[close]</button>
            </div>

            {selectedLink.justification && (
              <div className="text-[#94a3b8] mb-2 italic">
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
                        try { await confirmResonanceLink(conversationId, selectedLink.id); refreshTree() }
                        catch (err) { console.error("Failed to confirm link", err) }
                      }
                      setSelectedLink(null); setSelectedLinkPos(null)
                    }}
                    className="text-[9px] text-[#4ade80] hover:text-[#6ee7a0] font-mono cursor-pointer select-none"
                  >[confirm]</button>
                  <button
                    onClick={async (e) => {
                      e.stopPropagation()
                      if (selectedLink.id && conversationId) {
                        try { await deleteResonanceLink(conversationId, selectedLink.id); refreshTree() }
                        catch (err) { console.error("Failed to delete link", err) }
                      }
                      setSelectedLink(null); setSelectedLinkPos(null)
                    }}
                    className="text-[9px] text-[#ef4444] hover:text-[#f87171] font-mono cursor-pointer select-none"
                  >[dismiss]</button>
                </>
              ) : (
                <button
                  onClick={async (e) => {
                    e.stopPropagation()
                    if (selectedLink.id && conversationId) {
                      try { await deleteResonanceLink(conversationId, selectedLink.id); refreshTree() }
                      catch (err) { console.error("Failed to delete link", err) }
                    }
                    setSelectedLink(null); setSelectedLinkPos(null)
                  }}
                  className="text-[9px] text-[#ef4444] hover:text-[#f87171] font-mono cursor-pointer select-none"
                >[remove link]</button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const MemoizedConnectionCloud = memo(ConnectionCloud)
export default MemoizedConnectionCloud

