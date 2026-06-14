import { BASE } from "./http"
import type { SkillInfo, SkillsResponse, DbSkillInfo, DbSkillsResponse, WorkshopResponse, SkillEventInfo } from "./types"

export { type SkillInfo, type SkillsResponse, type DbSkillInfo, type DbSkillsResponse, type WorkshopResponse, type SkillEventInfo }

export async function getSkills(): Promise<SkillsResponse> {
  const res = await fetch(`${BASE}/skills`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getPipeline(): Promise<{ pipeline: SkillInfo[] }> {
  const res = await fetch(`${BASE}/agent/pipeline`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getDbSkills(): Promise<DbSkillsResponse> {
  const res = await fetch(`${BASE}/skills/db`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getSkillContent(skillName: string): Promise<WorkshopResponse> {
  const res = await fetch(`${BASE}/skills/workshop/load`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: skillName }) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function updateSkill(skillId: string, data: { description?: string; content?: string; trigger_keywords?: string[] }): Promise<DbSkillInfo> {
  const res = await fetch(`${BASE}/skills/${skillId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Failed to update skill" })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function createSkill(data: { name: string; description: string; content?: string; always_active: boolean; trigger_keywords: string[] }): Promise<DbSkillInfo> {
  const res = await fetch(`${BASE}/skills`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Failed to create skill" })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function deleteSkill(skillId: string): Promise<void> {
  const res = await fetch(`${BASE}/skills/${skillId}`, { method: "DELETE" })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Failed to delete skill" })); throw new Error(err.detail || `HTTP ${res.status}`) }
}

export async function getSkillEvents(limit = 50): Promise<SkillEventInfo[]> {
  const res = await fetch(`${BASE}/skills/events?limit=${limit}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
