import type { BeliefNodeInfo } from "../api/types"

export function recurrenceEntries(items: BeliefNodeInfo[]): BeliefNodeInfo[][] {
  const consumed = new Set<string>()
  return items.flatMap(item => {
    if (consumed.has(item.id)) return []
    const group = item.recurrence_group
    const members = group ? items.filter(peer =>
      group.member_ids.includes(peer.id) && peer.recurrence_group?.id === group.id
    ) : [item]
    const visible = members.length > 1 ? members : [item]
    visible.forEach(peer => consumed.add(peer.id))
    return [visible]
  })
}
