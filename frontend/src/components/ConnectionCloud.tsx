import { useEffect, useRef, useState, memo } from "react"
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

function areMessagesEqual(a: ChatMessage[], b: ChatMessage[]): boolean {
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    const ma = a[i]
    const mb = b[i]
    if (ma.id !== mb.id) return false
    if (ma.speaker !== mb.speaker) return false
    if (ma.content !== mb.content) return false
    if (ma.parent_message_id !== mb.parent_message_id) return false
    
    const aBranches = ma.proposed_branches || []
    const bBranches = mb.proposed_branches || []
    if (aBranches.length !== bBranches.length) return false
    for (let j = 0; j < aBranches.length; j++) {
      if (aBranches[j].content !== bBranches[j].content) return false
      if (aBranches[j].title !== bBranches[j].title) return false
    }
  }
  return true
}

function areLinksEqual(a: any[], b: any[]): boolean {
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    const la = a[i]
    const lb = b[i]
    if (la.id !== lb.id) return false
    if (String(la.source_id) !== String(lb.source_id)) return false
    if (String(la.target_id) !== String(lb.target_id)) return false
    if (la.status !== lb.status) return false
    if (la.justification !== lb.justification) return false
  }
  return true
}

function computeSettledLayout(
  initialNodes: SimNode[],
  links: SimLink[],
  width: number,
  height: number
): SimNode[] {
  const nodes = initialNodes.map((n) => ({ ...n }))
  const nodeMap = new Map<string, SimNode>()
  nodes.forEach((n) => nodeMap.set(n.id, n))

  let alpha = 1.0
  const decay = 0.965
  const friction = 0.78
  const repulseStrength = 180
  const springLength = 32
  const springStrength = 0.08
  const anchorStrength = 0.12
  const cx = width / 2
  const cy = height / 2

  while (alpha >= 0.015) {
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

    for (const link of links) {
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

    for (const n of nodes) {
      const tx = n.targetX !== undefined ? n.targetX : cx
      const ty = n.targetY !== undefined ? n.targetY : cy
      n.vx += (tx - n.x) * anchorStrength * alpha
      n.vy += (ty - n.y) * anchorStrength * alpha

      n.x += n.vx
      n.y += n.vy

      n.x = Math.max(15, Math.min(width - 15, n.x))
      n.y = Math.max(15, Math.min(height - 15, n.y))

      n.vx *= friction
      n.vy *= friction
    }

    alpha *= decay
  }

  return nodes
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

  // Store previous inputs to prevent infinite loops from parent reference updates
  const prevMessagesRef = useRef<ChatMessage[]>([])
  const prevLinksRef = useRef<any[]>([])
  const prevDimensionsRef = useRef({ width: 0, height: 0 })
  const [simulateSettling, setSimulateSettling] = useState<boolean>(() => {
    try {
      return localStorage.getItem("aaa_simulate_settling") === "true"
    } catch {
      return false
    }
  })
  const prevSimulateSettlingRef = useRef<boolean>(simulateSettling)

  // Zoom and pan state
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const panStartRef = useRef({ x: 0, y: 0 })

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

  // Build nodes and links from messages, db links, and inline proposals
  useEffect(() => {
    // 1. Core comparison check to prevent layout thrashes and infinite compute loops
    const messagesChanged = !areMessagesEqual(messages, prevMessagesRef.current)
    const linksChanged = !areLinksEqual(links, prevLinksRef.current)
    const dimensionsChanged =
      dimensions.width !== prevDimensionsRef.current.width ||
      dimensions.height !== prevDimensionsRef.current.height
    const simulateSettlingChanged = simulateSettling !== prevSimulateSettlingRef.current

    if (
      !messagesChanged &&
      !linksChanged &&
      !dimensionsChanged &&
      !simulateSettlingChanged &&
      simNodes.length > 0
    ) {
      return
    }

    // Update trace refs
    prevMessagesRef.current = messages
    prevLinksRef.current = links
    prevDimensionsRef.current = dimensions
    prevSimulateSettlingRef.current = simulateSettling

    const newNodes: SimNode[] = []
    const newLinks: SimLink[] = []

    const sorted = [...messages].sort((a, b) => a.id - b.id)

    // 2. Add all message nodes
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
            type: "parent",
          })
        })
      }
    }

    // 3. Calculate spiral target coordinates for sequential nodes
    const totalNodes = newNodes.length
    const cx = dimensions.width / 2
    const cy = dimensions.height / 2
    const maxTargetRadius = Math.min(dimensions.width, dimensions.height) * 0.42

    const radiusStep = totalNodes > 10 ? (maxTargetRadius - 20) / totalNodes : 12
    const angleStep = 0.55

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

    // 4. Add database retroactive links (resonance links)
    for (const l of links) {
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
      const settledNodes = computeSettledLayout(newNodes, newLinks, dimensions.width, dimensions.height)
      settledNodes.forEach((n) => {
        nodePositionsRef.current[n.id] = { x: n.x, y: n.y }
      })
      startLayoutTransition(settledNodes)
    } else {
      setSimNodes(newNodes)
    }
    setSimLinks(newLinks)
  }, [messages, links, dimensions.width, dimensions.height, simulateSettling])

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

      let strokeColor = "#1e293b"
      let strokeWidth = 0.4
      let strokeDash: number[] = []
      let opacity = 0.4

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
      ctx.lineTo(tgtNode.x, tgtNode.y)
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
        <div className="flex items-center gap-3">
          <button
            onClick={toggleSimulateSettling}
            className={`text-[9px] font-mono px-2 py-0.5 rounded border transition-all cursor-pointer select-none ${
              simulateSettling
                ? "bg-[#ec4899]/10 border-[#ec4899]/30 text-[#ec4899] hover:bg-[#ec4899]/20"
                : "bg-[#1b1b22] border-[#2e2e38] text-[#79798c] hover:bg-[#2e2e38]"
            }`}
            title={
              simulateSettling
                ? "Simulating settling in real-time (high GPU/CPU usage)"
                : "Instant static layout (energy efficient, low GPU/CPU)"
            }
          >
            {simulateSettling ? "⚡ Settling: Live" : "🍃 Settling: Static"}
          </button>
          <span className="text-[10px] font-mono text-[#4b4b5c]">
            {simNodes.filter((n) => !n.isProposed).length} nodes | {links.length} cross-links
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
        />

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
              <span className={`font-bold capitalize ${hoveredNode.speaker === "human" ? "text-[#6bc28c]" :
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

const MemoizedConnectionCloud = memo(ConnectionCloud)
export default MemoizedConnectionCloud

