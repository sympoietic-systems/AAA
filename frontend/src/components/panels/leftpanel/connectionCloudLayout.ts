import type { SimNode } from "./ConnectionCloudSimulation"

/** Assign radial tree targets without depending on the browser call-stack depth. */
export function assignRadialTargets(newNodes: SimNode[], width: number, height: number): void {
  const cx = width / 2
  const cy = height / 2
  const baseRadius = Math.min(width, height) * .45
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

  // One explicit traversal supplies depths and a parent-before-child order.
  const nodeDepths = new Map<string, number>()
  const order: string[] = []
  const pending: Array<[string, number]> = roots.map(id => [id, 0])
  let maxDepth = 0
  while (pending.length) {
    const [id, depth] = pending.pop()!
    if (nodeDepths.has(id)) continue
    nodeDepths.set(id, depth)
    order.push(id)
    maxDepth = Math.max(maxDepth, depth)
    for (const child of childrenMap.get(id) || []) pending.push([child, depth + 1])
  }

  // Reverse traversal visits every descendant before its parent.
  const subtreeWeights = new Map<string, number>()
  for (let i = order.length - 1; i >= 0; i--) {
    const id = order[i]
    const children = childrenMap.get(id) || []
    let weight = 0
    for (const child of children) weight += subtreeWeights.get(child) || 1
    subtreeWeights.set(id, weight || 1)
  }

  type Position = { id: string; minAngle: number; maxAngle: number; parentAngle: number; direction: 1 | -1 }
  const positions: Position[] = []
  const totalRootWeight = roots.reduce((sum, id) => sum + (subtreeWeights.get(id) || 1), 0)
  let rootAngle = 0
  for (const id of roots) {
    const span = ((subtreeWeights.get(id) || 1) / totalRootWeight) * 2 * Math.PI
    positions.push({ id, minAngle: rootAngle, maxAngle: rootAngle + span, parentAngle: rootAngle + span / 2, direction: 1 })
    rootAngle += span
  }
  positions.reverse()
  while (positions.length) {
    const { id, minAngle, maxAngle, parentAngle, direction } = positions.pop()!
    const node = nodeMap.get(id)
    if (!node) continue

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

      const nextPositions: Position[] = []
      for (const childId of children) {
        const childWeight = subtreeWeights.get(childId) || 1
        const childSpan = (childWeight / totalWeight) * angleSpan
        const nextAngle = currentAngle + childSpan
        nextPositions.push({ id: childId, minAngle: currentAngle, maxAngle: nextAngle, parentAngle: clampedAngle, direction: nextDirection })
        currentAngle = nextAngle
      }
      for (let i = nextPositions.length - 1; i >= 0; i--) positions.push(nextPositions[i])
    }
  }

}
