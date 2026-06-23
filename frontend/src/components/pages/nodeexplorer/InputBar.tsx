import { useRef, useState, useCallback, useEffect, memo, type ChangeEvent, type DragEvent, type FormEvent, type KeyboardEvent } from "react"

const ACCEPTED_EXTENSIONS = ".pdf,.txt,.md,.docx,.epub,.mobi,.py,.json,.yaml,.yml,.csv,.xml,.html,.css,.js,.ts,.tsx,.jsx,.rs,.go,.java,.c,.h,.cpp,.hpp,.sh,.bat,.ps1,.toml,.ini,.cfg,.env,.log"

interface Props {
  onSend: (text: string) => void
  onUploadFiles: (files: File[]) => void
  disabled?: boolean
  isIndexing?: boolean
  isPassword?: boolean
  conversationId?: string
}

export const InputBar = memo(function InputBar({ onSend, onUploadFiles, disabled, isIndexing, isPassword, conversationId }: Props) {
  const inputRef = useRef<HTMLTextAreaElement | HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [inputExpanded, setInputExpanded] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    if (!menuOpen) return
    const handleOutsideClick = () => {
      setMenuOpen(false)
    }
    document.addEventListener("click", handleOutsideClick)
    return () => document.removeEventListener("click", handleOutsideClick)
  }, [menuOpen])

  const processFiles = useCallback((fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return
    onUploadFiles(Array.from(fileList))
  }, [onUploadFiles])

  const handleInput = () => {
    if (isPassword) return
    const el = inputRef.current as HTMLTextAreaElement
    if (!el || inputExpanded) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 128)}px`
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (isIndexing || disabled) return
    const text = inputRef.current?.value.trim()
    if (text) {
      onSend(text)
      if (inputRef.current) {
        inputRef.current.value = ""
        if (!isPassword) {
          const el = inputRef.current as HTMLTextAreaElement
          if (inputExpanded) {
            el.style.height = "240px"
          } else {
            el.style.height = "auto"
          }
        }
      }
    }
  }

  const handleResearchSubmit = async (options: { isAgonistic: boolean }) => {
    if (isIndexing || disabled) return
    const text = inputRef.current?.value.trim()
    if (!text) return

    try {
      const { dispatchResearch } = await import("../../../api/research")
      await dispatchResearch({
        objective: text,
        conversation_id: conversationId,
        is_agonistic: options.isAgonistic,
      })
      if (inputRef.current) {
        inputRef.current.value = ""
        if (!isPassword) {
          const el = inputRef.current as HTMLTextAreaElement
          el.style.height = "auto"
        }
      }
    } catch (err) {
      console.error("Failed to dispatch research from InputBar:", err)
    }
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      if (!isIndexing && !disabled) {
        handleSubmit(e)
      }
    }
  }

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    processFiles(e.target.files)
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    processFiles(e.dataTransfer.files)
  }

  const canSubmit = !isIndexing && !disabled

  return (
    <div>
      <form
        onSubmit={handleSubmit}
        onDragOver={isPassword ? undefined : handleDragOver}
        onDragLeave={isPassword ? undefined : handleDragLeave}
        onDrop={isPassword ? undefined : handleDrop}
        className={`flex items-end border-t border-[#222]/40 px-4 py-3 transition-colors ${
          !isPassword && dragOver ? "border-[#4ade80]/60" : isIndexing ? "border-[#eab308]/40" : ""
        }`}
      >
        <span className={`mr-2 select-none text-sm font-mono self-start mt-0.5 ${
          isIndexing ? "text-[#eab308] animate-pulse" : "text-[#4ade80]"
        }`}>
          {isIndexing ? "•" : ">"}
        </span>
        {isPassword ? (
          <input
            type="password"
            ref={inputRef as any}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="enter password to unlock..."
            className="flex-1 bg-transparent text-[#ddd] text-sm outline-none placeholder:text-[#444] disabled:opacity-30 py-0 leading-5 h-5"
            autoFocus
          />
        ) : (
          <textarea
            ref={inputRef as any}
            rows={1}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            disabled={disabled}
            placeholder={
              dragOver
                ? "drop files here..."
                : isIndexing
                ? "Indexing files in background..."
                : "type a message..."
            }
            className={`flex-1 bg-transparent text-[#ddd] text-sm outline-none placeholder:text-[#444] disabled:opacity-30 h-[20px] p-0 border-0 leading-5 transition-all duration-150 ${
              inputExpanded ? "resize-y overflow-y-auto" : "resize-none overflow-y-hidden"
            }`}
          />
        )}
        {!isPassword ? (
          <div className="flex items-center gap-3 self-end h-[20px] font-mono select-none ml-2">
            <button
              type="button"
              onClick={() => {
                const nextExpanded = !inputExpanded
                setInputExpanded(nextExpanded)
                if (inputRef.current) {
                  const el = inputRef.current as HTMLTextAreaElement
                  if (nextExpanded) {
                    el.style.height = "240px"
                  } else {
                    el.style.height = "auto"
                    el.style.height = `${Math.min(el.scrollHeight, 128)}px`
                  }
                }
              }}
              disabled={disabled}
              className="text-[#555] hover:text-[#4ade80] text-xs leading-none disabled:opacity-30 transition-colors cursor-pointer"
              title={inputExpanded ? "collapse input" : "expand input"}
            >
              {inputExpanded ? "—" : "↕"}
            </button>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled || isIndexing}
              className="text-[#555] hover:text-[#4ade80] text-sm leading-none disabled:opacity-30 transition-colors cursor-pointer"
              title="Attach files"
            >
              +
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className={`text-[10px] uppercase tracking-wider transition-colors cursor-pointer select-none leading-none ${
                canSubmit
                  ? "text-[#4ade80] hover:text-[#6ee7a0]"
                  : "text-[#333] cursor-not-allowed"
              }`}
              title="Send message"
            >
              [send]
            </button>
            <div className="relative flex items-center">
              <button
                type="button"
                disabled={!canSubmit}
                onClick={(e) => {
                  e.stopPropagation()
                  setMenuOpen(!menuOpen)
                }}
                className={`text-[10px] uppercase tracking-wider transition-colors cursor-pointer select-none leading-none ${
                  canSubmit
                    ? "text-[#8b5cf6] hover:text-[#a78bfa]"
                    : "text-[#333] cursor-not-allowed"
                }`}
                title="Research options"
              >
                [research ▼]
              </button>
              
              {menuOpen && (
                <div className="absolute bottom-full right-0 mb-1 z-50 min-w-[160px] flex flex-col bg-[#0c0c0e]/95 backdrop-blur-md font-mono text-[9px] select-none">
                  <button
                    type="button"
                    onClick={() => {
                      handleResearchSubmit({ isAgonistic: false })
                      setMenuOpen(false)
                    }}
                    className="w-full text-left px-3 py-1.5 hover:bg-[#16161a]/60 text-[#aaa] hover:text-white transition-colors flex items-center gap-2 whitespace-nowrap cursor-pointer"
                  >
                    <span className="w-3 h-3 flex items-center justify-center leading-none shrink-0 text-[#6c6c8a]">⊙</span> Standard Research
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      handleResearchSubmit({ isAgonistic: true })
                      setMenuOpen(false)
                    }}
                    className="w-full text-left px-3 py-1.5 hover:bg-[#16161a]/60 text-[#aaa] hover:text-white transition-colors flex items-center gap-2 whitespace-nowrap cursor-pointer"
                  >
                    <span className="w-3 h-3 flex items-center justify-center leading-none shrink-0 text-[#6c6c8a]">⋈</span> Agonistic Research
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const text = inputRef.current?.value.trim()
                      window.open(`/research?id=new${text ? `&objective=${encodeURIComponent(text)}` : ""}`, "_blank")
                      setMenuOpen(false)
                    }}
                    className="w-full text-left px-3 py-1.5 hover:bg-[#16161a]/60 text-[#aaa] hover:text-white transition-colors flex items-center gap-2 whitespace-nowrap border-t border-[#222]/30 cursor-pointer"
                  >
                    <span className="w-3 h-3 flex items-center justify-center leading-none shrink-0 text-[#6c6c8a]">⚙</span> Configure Research...
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <button
            type="submit"
            disabled={!canSubmit}
            className={`ml-2 text-[10px] uppercase font-mono tracking-wider transition-colors self-end cursor-pointer select-none leading-none ${
              canSubmit
                ? "text-[#4ade80] hover:text-[#6ee7a0]"
                : "text-[#333] cursor-not-allowed"
            }`}
            title="Unlock application"
          >
            [unlock]
          </button>
        )}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_EXTENSIONS}
          onChange={handleFileChange}
          className="hidden"
        />
      </form>
    </div>
  )
})

