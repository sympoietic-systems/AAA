/** Pure result-parsing helpers shared across the per-step-type result renderers. */

/** Repair a JSON string that has been truncated by balancing braces, brackets, and quotes. */
export function repairTruncatedJson(str: string): string {
  let cleaned = str.trim()
  if (!cleaned) return ""

  let inString = false
  let escaped = false
  const stack: ("{" | "[")[] = []

  for (let i = 0; i < cleaned.length; i++) {
    const char = cleaned[i]
    if (escaped) {
      escaped = false
      continue
    }
    if (char === "\\") {
      escaped = true
      continue
    }
    if (char === '"') {
      inString = !inString
      continue
    }
    if (inString) {
      continue
    }
    if (char === "{") {
      stack.push("{")
    } else if (char === "[") {
      stack.push("[")
    } else if (char === "}") {
      if (stack[stack.length - 1] === "{") {
        stack.pop()
      }
    } else if (char === "]") {
      if (stack[stack.length - 1] === "[") {
        stack.pop()
      }
    }
  }

  let repaired = cleaned
  if (inString) {
    repaired += '"'
  }
  for (let i = stack.length - 1; i >= 0; i--) {
    const openChar = stack[i]
    if (openChar === "{") {
      repaired += "}"
    } else if (openChar === "[") {
      repaired += "]"
    }
  }

  return repaired
}

/** Classify a parse result by its raw_content. */
export function parseStatus(content: string | null | undefined): { icon: string; label: string; color: string } {
  if (!content || content.trim().length === 0) return { icon: "✗", label: "empty", color: "var(--color-semantic-red)" }
  const c = content.trim()
  if (c.length < 200) return { icon: "○", label: "too short", color: "var(--color-semantic-gold)" }
  const junkPatterns = ["security check required", "cloudflare", "enable javascript", "please complete the security check"]
  if (junkPatterns.some(p => c.slice(0, 1000).toLowerCase().includes(p))) return { icon: "⚠", label: "blocked", color: "var(--color-semantic-sand)" }
  if (/^(skip|close|open navigation|sign in|sign up)/i.test(c.slice(0, 100).trim())) return { icon: "⛔", label: "paywall", color: "var(--color-semantic-sand)" }
  return { icon: "✓", label: "ok", color: "var(--color-semantic-green)" }
}

/** Human-readable status label + color for a single digested source. */
export function sourceStatusLabel(analysis: any): { label: string; color: string } {
  if (!analysis) return { label: "no analysis", color: "var(--color-ui-dim)" }
  if (analysis.learnings?.length > 0) return { label: `${analysis.learnings.length} learnings`, color: "var(--color-semantic-green)" }

  const gaps = analysis.gaps || []
  for (const gap of gaps) {
    if (typeof gap === "string") {
      const g = gap.toLowerCase()
      if (g.includes("blocked by anti-bot") || g.includes("cloudflare") || g.includes("captcha")) {
        return { label: "blocked (anti-bot)", color: "var(--color-semantic-red)" }
      }
      if (g.includes("content too short") || g.includes("too short")) {
        return { label: "too short", color: "var(--color-semantic-gold)" }
      }
      if (g.includes("fetch failed")) {
        return { label: "fetch failed", color: "var(--color-semantic-red)" }
      }
    }
  }

  if (gaps.length > 0) return { label: `${gaps.length} gaps`, color: "var(--color-semantic-gold)" }
  return { label: "no learnings", color: "var(--color-semantic-sand)" }
}
