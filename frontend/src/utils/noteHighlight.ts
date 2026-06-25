import type { NoteInfo } from "../api/client"

const VISIBILITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  personal: {
    bg: "rgba(133, 77, 14, 0.4)",
    text: "#fef3c7",
    border: "rgba(234, 179, 8, 0.5)",
  },
  shared: {
    bg: "rgba(91, 33, 182, 0.35)",
    text: "#e9d5ff",
    border: "rgba(168, 85, 247, 0.5)",
  },
  agent: {
    bg: "rgba(14, 116, 144, 0.4)",
    text: "#a5f3fc",
    border: "rgba(34, 211, 238, 0.6)",
  },
}

const MARK_CSS = `
.note-highlight {
  padding: 0 1px;
  border-bottom: 1.5px solid var(--nh-border);
  cursor: pointer;
  transition: all 0.15s;
}
.note-highlight:hover {
  filter: brightness(1.3);
  border-bottom-width: 2px;
}
`.replace(/\n/g, "")

let styleInjected = false

function injectStyles() {
  if (styleInjected) return
  const el = document.createElement("style")
  el.textContent = MARK_CSS
  document.head.appendChild(el)
  styleInjected = true
}

export function wrapSelectedTextInMarks(markdown: string, notes: NoteInfo[]): string {
  if (!notes.length) return markdown

  injectStyles()

  const plainChars: string[] = []
  const mapping: number[] = []
  let i = 0
  const n = markdown.length

  while (i < n) {
    const ch = markdown[i]
    if (ch === '*' || ch === '_' || ch === '`' || ch === '~') {
      i += 1
      continue
    }
    if (ch === '\n' || ch === '\r') {
      let j = i
      while (j < n && (markdown[j] === '\n' || markdown[j] === '\r')) j++
      if (plainChars.length === 0 || plainChars[plainChars.length - 1] !== ' ') {
        plainChars.push(' ')
        mapping.push(i)
      }
      i = j
      continue
    }
    if (ch === ' ' || ch === '\t') {
      if (plainChars.length === 0 || plainChars[plainChars.length - 1] !== ' ') {
        plainChars.push(' ')
        mapping.push(i)
      }
      i += 1
      continue
    }
    plainChars.push(ch)
    mapping.push(i)
    i += 1
  }

  const plainText = plainChars.join('')

  const sorted = [...notes]
    .filter(n => n.selected_text)
    .sort((a, b) => b.selected_text.length - a.selected_text.length)

  const ranges: { start: number; end: number; noteId: string; colors: typeof VISIBILITY_COLORS.personal; comment: string }[] = []

  for (const note of sorted) {
    const searchText = note.selected_text
      .replace(/[\n\r]+/g, ' ')
      .replace(/\s+/g, ' ')

    const searchLen = searchText.length
    let idx = 0
    while ((idx = plainText.indexOf(searchText, idx)) !== -1) {
      const rStart = mapping[idx]
      const rEnd = mapping[Math.min(idx + searchLen - 1, plainText.length - 1)] + 1
      const colors = VISIBILITY_COLORS[note.visibility] || VISIBILITY_COLORS.personal
      ranges.push({ start: rStart, end: rEnd, noteId: note.id, colors, comment: note.comment })
      idx++
    }
  }

  ranges.sort((a, b) => a.start - b.start || b.end - a.end)

  const openTags: { pos: number; tag: string }[] = []
  const closeTags: { pos: number; tag: string }[] = []

  for (const r of ranges) {
    openTags.push({ pos: r.start, tag: `<mark data-note-id="${r.noteId}" data-note-comment="${escapeHtml(r.comment)}" style="background:${r.colors.bg};color:${r.colors.text};--nh-border:${r.colors.border}" class="note-highlight">` })
    closeTags.push({ pos: r.end, tag: '</mark>' })
  }

  openTags.sort((a, b) => a.pos - b.pos)
  closeTags.sort((a, b) => a.pos - b.pos)

  if (openTags.length === 0) return markdown

  let result = ''
  let cursor = 0
  let oi = 0
  let ci = 0

  while (cursor < markdown.length || oi < openTags.length) {
    const nextOpen = oi < openTags.length ? openTags[oi].pos : Infinity
    const nextClose = ci < closeTags.length ? closeTags[ci].pos : Infinity

    if (nextOpen <= nextClose) {
      result += markdown.slice(cursor, nextOpen)
      if (oi < openTags.length) result += openTags[oi].tag
      cursor = nextOpen
      if (oi < openTags.length) oi++
    } else {
      result += markdown.slice(cursor, nextClose)
      if (ci < closeTags.length) result += closeTags[ci].tag
      cursor = nextClose
      if (ci < closeTags.length) ci++
    }
  }

  return result
}

export function scrollToNoteHighlight(noteId: string, containerSelector?: string): boolean {
  const container = containerSelector
    ? document.querySelector(containerSelector)
    : document

  if (!container) return false

  const el = container.querySelector(`[data-note-id="${noteId}"]`)
  if (!el) return false

  el.scrollIntoView({ behavior: "auto", block: "center" })
  return true
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
}
