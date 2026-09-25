import type { NoteInfo } from "../../../api/types"
import type { SimNode, SimLink } from "./ConnectionCloudSimulation"
import { buildNotesMap, EMPTY_NOTE_ARRAY } from "../../../utils/noteHelpers"
import { COLOR_PALETTE } from "../../../config/colors"

const CANVAS_COLORS = {
  bg: COLOR_PALETTE.uiBg,
  guideRings: COLOR_PALETTE.uiGuideRings,
  linkDefault: COLOR_PALETTE.uiGuideRings,
  linkResonance: COLOR_PALETTE.uiLinkResonance,
  human: COLOR_PALETTE.semanticGreen,
  apparatus: COLOR_PALETTE.semanticPurple,
  active: COLOR_PALETTE.semanticGreen,
  proposed: COLOR_PALETTE.semanticGold,
  ghost: COLOR_PALETTE.semanticSlate,
  humanBg: COLOR_PALETTE.humanBg,
  apparatusBg: COLOR_PALETTE.apparatusBg,
  noteAgent: COLOR_PALETTE.semanticBlue,
  noteShared: COLOR_PALETTE.semanticPurple,
  noteProposed: COLOR_PALETTE.semanticGold,
}
interface Scene {
  dimensions: { width: number; height: number }
  simNodes: SimNode[]
  simLinks: SimLink[]
  hoveredNode: SimNode | null
  activeMessageId: number | null
  activePathIds: Set<number>
  notes: NoteInfo[]
  zoom: number
  pan: { x: number; y: number }
}

/** Canvas-only rendering: no React state, network, or interaction ownership. */
export function drawConnectionCloud(canvas: HTMLCanvasElement, { dimensions, simNodes, simLinks, hoveredNode, activeMessageId, activePathIds, notes, zoom, pan }: Scene) {
  // Helper to check if a link is part of the active path
  const isLinkActive = (link: SimLink) => {
    const srcId = parseInt(link.source)
    const tgtId = parseInt(link.target)
    if (isNaN(srcId) || isNaN(tgtId)) return false
    return activePathIds.has(srcId) && activePathIds.has(tgtId)
  }

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
    ctx.strokeStyle = CANVAS_COLORS.guideRings
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

    const notesMap = buildNotesMap(notes)

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
      const futureColor = tgtNode.speaker === "apparatus" ? CANVAS_COLORS.apparatus : CANVAS_COLORS.human

      let strokeColor: string = tgtNode.speaker === "apparatus" ? CANVAS_COLORS.apparatus : CANVAS_COLORS.human
      let strokeWidth = 0.4
      let strokeDash: number[] = []
      let opacity = 0.25

      if (isActive) {
        strokeColor = CANVAS_COLORS.active
        strokeWidth = 0.8
        opacity = 0.85
      } else if (isFuture) {
        strokeColor = futureColor
        strokeDash = [2, 2]
        strokeWidth = 0.8
        opacity = 0.8
      } else if (isProposed) {
        strokeColor = CANVAS_COLORS.proposed
        strokeDash = [2, 2]
        strokeWidth = 0.5
        opacity = 0.35
      } else if (isResonance) {
        if (isProposedResonance) {
          strokeColor = CANVAS_COLORS.proposed
          strokeDash = [1, 3]
          strokeWidth = 0.7
          opacity = 0.7
        } else {
          strokeColor = CANVAS_COLORS.ghost
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
      const nodeNotes = notesMap.get(node.dbId ?? -1) ?? EMPTY_NOTE_ARRAY

      let fill: string
      let stroke: string
      let strokeWidth = 0.6
      let radius: number
      let strokeDash: number[] = []

      if (node.isProposed) {
        fill = CANVAS_COLORS.bg
        stroke = CANVAS_COLORS.proposed
        strokeWidth = 0.8
        radius = 3.2
        strokeDash = [2, 2]
      } else if (node.speaker === "human") {
        if (isActive) {
          fill = isLeaf ? CANVAS_COLORS.humanBg : CANVAS_COLORS.bg
          stroke = CANVAS_COLORS.human
          strokeWidth = isLeaf ? 1.5 : 1.0
          radius = isLeaf ? 4.5 : 3.2
        } else if (isFuture) {
          fill = CANVAS_COLORS.bg
          stroke = CANVAS_COLORS.human
          strokeWidth = 1.0
          radius = 3.2
          strokeDash = [2, 1.5]
        } else {
          fill = CANVAS_COLORS.bg
          stroke = CANVAS_COLORS.human
          strokeWidth = 0.7
          radius = 2.2
        }
      } else if (node.speaker === "apparatus") {
        if (isActive) {
          fill = isLeaf ? CANVAS_COLORS.apparatusBg : CANVAS_COLORS.bg
          stroke = CANVAS_COLORS.apparatus
          strokeWidth = isLeaf ? 1.5 : 1.0
          radius = isLeaf ? 4.5 : 3.2
        } else if (isFuture) {
          fill = CANVAS_COLORS.bg
          stroke = CANVAS_COLORS.apparatus
          strokeWidth = 1.0
          radius = 3.2
          strokeDash = [2, 1.5]
        } else {
          fill = CANVAS_COLORS.bg
          stroke = CANVAS_COLORS.apparatus
          strokeWidth = 0.7
          radius = 2.2
        }
      } else {
        fill = CANVAS_COLORS.bg
        stroke = CANVAS_COLORS.ghost
        radius = 1.8
      }

      const drawRadius = isHovered ? radius + 1.0 : radius
      const drawOpacity = isActive || isLeaf || isHovered ? 1.0 : isFuture ? 0.8 : node.isProposed ? 0.75 : 0.45

      ctx.globalAlpha = drawOpacity

      // Static premium glowing concentric rings for active leaf node
      if (isLeaf) {
        ctx.beginPath()
        ctx.arc(node.x, node.y, radius + 4.5, 0, 2 * Math.PI)
        ctx.strokeStyle = node.speaker === "human" ? CANVAS_COLORS.human : CANVAS_COLORS.apparatus
        ctx.lineWidth = 0.8
        ctx.globalAlpha = 0.3
        ctx.stroke()

        ctx.beginPath()
        ctx.arc(node.x, node.y, radius + 2.0, 0, 2 * Math.PI)
        ctx.strokeStyle = node.speaker === "human" ? CANVAS_COLORS.human : CANVAS_COLORS.apparatus
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
        const dotColor = isAgent ? CANVAS_COLORS.noteAgent : isShared ? CANVAS_COLORS.noteShared : CANVAS_COLORS.noteProposed

        const angle = -Math.PI / 4 - (idx * Math.PI) / 2
        const dist = drawRadius + 2.2
        const dx = node.x + dist * Math.cos(angle)
        const dy = node.y + dist * Math.sin(angle)

        ctx.beginPath()
        ctx.arc(dx, dy, 1.1, 0, 2 * Math.PI)
        ctx.fillStyle = dotColor
        ctx.fill()

        ctx.strokeStyle = CANVAS_COLORS.bg
        ctx.lineWidth = 0.3
        ctx.stroke()
      })

      // Proposed Title Label
      if (node.isProposed) {
        ctx.font = "bold 9px monospace"
        ctx.fillStyle = CANVAS_COLORS.proposed
        ctx.textAlign = "center"
        ctx.textBaseline = "bottom"
        ctx.globalAlpha = 0.8
        ctx.fillText(`🚀 ${node.title || "Flight"}`, node.x, node.y - drawRadius - 4)
      }
    })

    ctx.restore()
}
