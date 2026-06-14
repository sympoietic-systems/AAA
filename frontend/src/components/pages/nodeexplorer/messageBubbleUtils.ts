import type { NoteInfo } from "../../../api/client"

export const DIMENSION_NAMES = [
  "Homeostatic", "Amplifying", "Cyclic", "Bifurcated",
  "Decentralized", "Rhizomatic/Networked", "Boundary Permeability",
  "Recursion Depth", "Variety Filtering", "Negentropic Complexity",
  "Temporal Latency", "Attractor Depth", "Symbiotic", "Nomadic",
  "Conversational Co-Orientation", "Substrate Materiality"
]

export function areNumberArraysEqual(a?: number[] | null, b?: number[] | null) {
  if (a === b) return true
  if (!a || !b) return false
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false
  }
  return true
}

export function areStringArraysEqual(a?: string[] | null | undefined, b?: string[] | null | undefined) {
  if (a === b) return true
  if (!a || !b) return false
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false
  }
  return true
}

export function areNotesEqual(a?: NoteInfo[] | null, b?: NoteInfo[] | null) {
  if (a === b) return true
  if (!a || !b) return false
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    if (a[i].id !== b[i].id ||
        a[i].comment !== b[i].comment ||
        a[i].visibility !== b[i].visibility ||
        a[i].selected_text !== b[i].selected_text) {
      return false
    }
  }
  return true
}

export function getSelectionCharacterOffsetWithin(element: HTMLElement) {
  let start = 0
  let end = 0
  const doc = element.ownerDocument || document
  const win = doc.defaultView || window
  const sel = win.getSelection()
  if (sel && sel.rangeCount > 0) {
    const range = sel.getRangeAt(0)
    const preCORSectRange = range.cloneRange()
    preCORSectRange.selectNodeContents(element)
    preCORSectRange.setEnd(range.startContainer, range.startOffset)
    start = preCORSectRange.toString().length
    end = start + range.toString().length
  }
  return { start, end }
}
