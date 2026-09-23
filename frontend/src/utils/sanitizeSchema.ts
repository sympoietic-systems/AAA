import { defaultSchema } from "rehype-sanitize"

/**
 * Strict sanitization schema extending GitHub markdown defaults.
 * Permits custom AAA tags (e.g. <mark>, <aaa-note>, <research-proposal>)
 * with specific safe attributes, while strictly stripping <script>, <iframe>,
 * and all inline event handlers (onerror, onload, onclick, etc.).
 */
export const aaaSanitizeSchema = {
  ...defaultSchema,
  tagNames: [
    ...(defaultSchema.tagNames || []),
    "mark",
    "aaa-note",
    "note-entanglement",
    "note_entanglement",
    "scar-fold",
    "scar_fold",
    "research-proposal",
  ],
  attributes: {
    ...defaultSchema.attributes,
    "*": [
      ...((defaultSchema.attributes && defaultSchema.attributes["*"]) || []),
      "className",
      "style",
      "dataNoteId",
      "data-note-id",
    ],
    mark: ["dataNoteId", "data-note-id", "className", "style"],
    "aaa-note": ["dataNoteId", "data-note-id", "className", "style"],
    "note-entanglement": ["dataNoteId", "data-note-id", "className", "style"],
    "note_entanglement": ["dataNoteId", "data-note-id", "className", "style"],
    "research-proposal": [
      "proposalId",
      "proposal-id",
      "title",
      "description",
      "objective",
      "status",
      "className",
    ],
    a: [
      ...((defaultSchema.attributes && defaultSchema.attributes["a"]) || []),
      "target",
      "rel",
    ],
  },
}
