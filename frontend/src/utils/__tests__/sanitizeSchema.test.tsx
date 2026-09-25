import { render } from "@testing-library/react"
import { expect, it } from "vitest"
import ReactMarkdown from "react-markdown"
import rehypeRaw from "rehype-raw"
import rehypeSanitize from "rehype-sanitize"
import { aaaSanitizeSchema } from "../sanitizeSchema"

it("V38 strips hostile HTML, URLs, CSS and classes while retaining annotations", () => {
  const { container } = render(<ReactMarkdown rehypePlugins={[rehypeRaw, [rehypeSanitize, aaaSanitizeSchema]]}>
    {'<script>alert(1)</script><iframe src="https://evil.test"></iframe><mark style="position:fixed;inset:0" class="fixed note-highlight note-shared" data-note-id="n1" onclick="alert(1)">note</mark><a href="javascript:alert(1)">bad</a>'}
  </ReactMarkdown>)
  expect(container.querySelector("script,iframe,[style],[onclick]")).toBeNull()
  expect(container.querySelector("mark")?.className).toBe("note-highlight note-shared")
  expect(container.querySelector("mark")?.getAttribute("data-note-id")).toBe("n1")
  expect(container.querySelector("a")?.getAttribute("href")).toBeNull()
})
