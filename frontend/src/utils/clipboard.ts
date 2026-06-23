/**
 * Copy text to clipboard using the modern Clipboard API if available,
 * falling back to document.execCommand('copy') for non-secure (HTTP) environments.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch (err) {
      console.warn("navigator.clipboard.writeText failed, trying fallback...", err)
    }
  }

  // Fallback method for non-secure contexts (HTTP)
  try {
    const textarea = document.createElement("textarea")
    textarea.value = text
    // Prevent scrolling and keep it hidden
    textarea.style.position = "fixed"
    textarea.style.top = "0"
    textarea.style.left = "0"
    textarea.style.opacity = "0"
    textarea.style.pointerEvents = "none"
    
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    
    const successful = document.execCommand("copy")
    document.body.removeChild(textarea)
    return successful
  } catch (err) {
    console.error("Fallback clipboard copy failed:", err)
    return false
  }
}
