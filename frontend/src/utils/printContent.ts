import type { NoteInfo } from "../api/types"

/** Print sanitized rendered content; user text never enters an HTML string sink. */
export function printContent(content: HTMLElement | null, title: string, notes: NoteInfo[] = []): void {
  if (!content) return
  const frame = document.createElement("iframe")
  frame.setAttribute("sandbox", "allow-same-origin allow-modals")
  frame.setAttribute("aria-hidden", "true")
  frame.style.cssText = "position:fixed;width:0;height:0;border:0;bottom:0;right:0"
  document.body.appendChild(frame)
  const target = frame.contentDocument
  if (!target) { frame.remove(); return }
  target.title = title
  const style = target.createElement("style")
  style.textContent = "body{font:13px/1.7 system-ui;color:#222;padding:2rem;max-width:800px;margin:auto}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:6px}pre{white-space:pre-wrap}img{max-width:100%}blockquote{border-left:3px solid #ccc;padding-left:1em}"
  target.head.appendChild(style)
  target.body.appendChild(content.cloneNode(true))
  if (notes.length) {
    const heading = target.createElement("h2")
    heading.textContent = "Notes"
    target.body.appendChild(heading)
    for (const note of notes) {
      const selected = target.createElement("p")
      selected.textContent = note.selected_text
      const comment = target.createElement("blockquote")
      comment.textContent = note.comment
      target.body.append(selected, comment)
    }
  }
  const cleanup = () => frame.remove()
  frame.contentWindow?.addEventListener("afterprint", cleanup, { once: true })
  // Some browsers omit afterprint for embedded documents.
  const timeout = setTimeout(cleanup, 60000)
  frame.contentWindow?.addEventListener("afterprint", () => clearTimeout(timeout), { once: true })
  requestAnimationFrame(() => {
    if (!frame.isConnected) return
    frame.contentWindow?.focus()
    frame.contentWindow?.print()
  })
}
