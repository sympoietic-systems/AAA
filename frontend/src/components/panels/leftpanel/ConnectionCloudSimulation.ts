// Pure simulation helpers for the Connection Cloud DAG.
// No React dependencies — just math and data structures.

export interface SimNode {
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

export interface SimLink {
  id?: string
  source: string
  target: string
  type: "parent" | "resonance"
  status?: "active" | "proposed"
  justification?: string
}

export function computeSettledLayout(
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

export function getDistanceToSegment(x: number, y: number, x1: number, y1: number, x2: number, y2: number): number {
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
