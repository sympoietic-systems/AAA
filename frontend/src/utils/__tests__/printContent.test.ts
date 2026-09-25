import { afterEach, expect, it, vi } from "vitest"
import { printContent } from "../printContent"
import type { NoteInfo } from "../../api/types"

afterEach(() => { vi.useRealTimers(); document.body.replaceChildren() })
it("V38 prints text notes in a sandbox without reparsing them as HTML", () => {
  vi.useFakeTimers()
  const content = document.createElement("div")
  content.textContent = "Report"
  printContent(content, "<script>title</script>", [{ selected_text: '<img src=x onerror="alert(1)">', comment: "<script>alert(1)</script>" } as NoteInfo])
  const frame = document.querySelector("iframe")!
  expect(frame.getAttribute("sandbox")).toBe("allow-same-origin allow-modals")
  expect(frame.contentDocument?.querySelector("script,img")).toBeNull()
  expect(frame.contentDocument?.body.textContent).toContain('<img src=x onerror="alert(1)">')
  frame.contentWindow?.dispatchEvent(new Event("afterprint"))
  expect(document.querySelector("iframe")).toBeNull()
})
