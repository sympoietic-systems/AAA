import type { Options } from "react-markdown"
import rehypeRaw from "rehype-raw"
import rehypeSanitize from "rehype-sanitize"
import rehypeKatex from "rehype-katex"
import { aaaSanitizeSchema } from "./sanitizeSchema"

// KaTeX is trusted transformation after the untrusted HTML boundary; trust stays disabled.
export const safeHtmlPlugins: NonNullable<Options["rehypePlugins"]> = [rehypeRaw, [rehypeSanitize, aaaSanitizeSchema]]
export const safeMathPlugins: NonNullable<Options["rehypePlugins"]> = [...safeHtmlPlugins, [rehypeKatex, { trust: false }]]
