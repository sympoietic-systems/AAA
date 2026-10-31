import { expect, it } from "vitest"
import { assignRadialTargets } from "./connectionCloudLayout"
import type { SimNode } from "./ConnectionCloudSimulation"

function nodes(parents: Array<number | null>): SimNode[] {
  return parents.map((parentMsgId, i) => ({ id: String(i + 1), parentMsgId, speaker: "human", content: "",
    isProposed: false, x: 0, y: 0, vx: 0, vy: 0 }))
}

it("lays out a 20,000-message chain without overflowing the call stack", () => {
  const chain = nodes(Array.from({ length: 20000 }, (_, i) => i === 0 ? null : i))
  assignRadialTargets(chain, 400, 300)
  for (const node of chain) {
    expect(Number.isFinite(node.targetX)).toBe(true)
    expect(Number.isFinite(node.targetY)).toBe(true)
    expect(Math.hypot(node.targetX! - 200, node.targetY! - 150)).toBeLessThanOrEqual(135.000001)
  }
  expect(Math.hypot(chain.at(-1)!.targetX! - 200, chain.at(-1)!.targetY! - 150)).toBeCloseTo(135)
})

it("preserves the previous recursive layout's coordinates for branches and multiple roots", () => {
  const forest = nodes([null, 1, 1, 2, null])
  assignRadialTargets(forest, 400, 300)
  // Frozen from the deployed recursive implementation before replacing its traversal.
  const expected = [[200, 150], [187.47625203837282, 226.48140778642636],
    [140.0270319205714, 199.0865877785759], [206.08629518440026, 284.86273395911985], [200, 150]]
  forest.forEach((node, i) => {
    expect(node.targetX).toBeCloseTo(expected[i][0], 10)
    expect(node.targetY).toBeCloseTo(expected[i][1], 10)
  })
})

it("handles empty trees and missing parents", () => {
  expect(() => assignRadialTargets([], 400, 300)).not.toThrow()
  const orphan = nodes([999])
  assignRadialTargets(orphan, 400, 300)
  expect([orphan[0].targetX, orphan[0].targetY]).toEqual([200, 150])
})
