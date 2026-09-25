import type { NoteInfo } from "../api/client"

export function wrapSelectedTextInMarks(markdown: string, notes: NoteInfo[]): string {
  if (!notes.length) return markdown


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

  const ranges: { start: number; end: number; noteId: string; comment: string; visibility: string }[] = []

  for (const note of sorted) {
    const searchText = note.selected_text
      .replace(/[\n\r]+/g, ' ')
      .replace(/\s+/g, ' ')

    const searchLen = searchText.length
    let idx = 0
    while ((idx = plainText.indexOf(searchText, idx)) !== -1) {
      const rStart = mapping[idx]
      const rEnd = mapping[Math.min(idx + searchLen - 1, plainText.length - 1)] + 1
      ranges.push({ start: rStart, end: rEnd, noteId: note.id, comment: note.comment, visibility: note.visibility || "personal" })
      idx++
    }
  }

  ranges.sort((a, b) => a.start - b.start || b.end - a.end)

  const openTags: { pos: number; tag: string }[] = []
  const closeTags: { pos: number; tag: string }[] = []

  for (const r of ranges) {
    openTags.push({ pos: r.start, tag: `<mark id="note-highlight-${escapeHtml(r.noteId)}" data-note-id="${escapeHtml(r.noteId)}" data-note-comment="${escapeHtml(r.comment)}" data-note-visibility="${escapeHtml(r.visibility)}" class="note-highlight note-${["personal", "shared", "agent"].includes(r.visibility) ? r.visibility : "personal"}">` })
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
