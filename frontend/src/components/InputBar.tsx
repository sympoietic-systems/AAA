import { useRef, useState, useCallback, type ChangeEvent, type DragEvent, type FormEvent, type KeyboardEvent } from "react"

const ACCEPTED_EXTENSIONS = ".pdf,.txt,.md,.docx,.py,.json,.yaml,.yml,.csv,.xml,.html,.css,.js,.ts,.tsx,.jsx,.rs,.go,.java,.c,.h,.cpp,.hpp,.sh,.bat,.ps1,.toml,.ini,.cfg,.env,.log"

interface Props {
  onSend: (text: string) => void
  onUploadFiles: (files: File[]) => void
  disabled?: boolean
  isIndexing?: boolean
  isPassword?: boolean
}

export function InputBar({ onSend, onUploadFiles, disabled, isIndexing, isPassword }: Props) {
  const inputRef = useRef<HTMLTextAreaElement | HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [inputExpanded, setInputExpanded] = useState(false)

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
          (inputRef.current as HTMLTextAreaElement).style.height = "auto"
        }
      }
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
        className={`flex items-center border-t border-[#222] bg-[#0f0f0f] px-4 py-3 transition-colors ${
          !isPassword && dragOver ? "border-[#4ade80] bg-[#111]" : isIndexing ? "border-[#eab308]/40 bg-[#0f0f0c]" : ""
        }`}
      >
        <span className={`mr-2 select-none text-sm font-mono ${
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
            className="flex-1 bg-transparent text-[#ddd] text-sm outline-none placeholder:text-[#444] disabled:opacity-30"
            autoFocus
          />
        ) : (
          <textarea
            ref={inputRef as any}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            disabled={disabled}
            rows={inputExpanded ? 10 : 1}
            placeholder={
              dragOver
                ? "drop files here..."
                : isIndexing
                ? "Indexing files in background..."
                : "type a message..."
            }
            className={`flex-1 resize-none bg-transparent text-[#ddd] text-sm outline-none
                       placeholder:text-[#444] disabled:opacity-30 ${
                         inputExpanded ? "overflow-y-auto" : "overflow-y-hidden"
                       }`}
          />
        )}
        {!isPassword && (
          <>
            <button
              type="button"
              onClick={() => {
                setInputExpanded(!inputExpanded)
                if (inputExpanded && inputRef.current) {
                  (inputRef.current as HTMLTextAreaElement).style.height = "auto"
                }
              }}
              disabled={disabled}
              className="ml-2 text-[#555] hover:text-[#4ade80] text-sm leading-none disabled:opacity-30 transition-colors"
              title={inputExpanded ? "collapse input" : "expand input"}
            >
              {inputExpanded ? "—" : "↕"}
            </button>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled || isIndexing}
              className="ml-2 text-[#555] hover:text-[#4ade80] text-lg leading-none disabled:opacity-30 transition-colors"
              title="Attach files"
            >
              +
            </button>
          </>
        )}
        <button
          type="submit"
          disabled={!canSubmit}
          className={`ml-2 text-xs uppercase px-2 py-1 rounded transition-colors ${
            canSubmit
              ? "text-[#4ade80] hover:bg-[#1f2937]"
              : "text-[#333] cursor-not-allowed"
          }`}
          title={isPassword ? "Unlock application" : "Send message"}
        >
          {isPassword ? "Unlock" : "Send"}
        </button>
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
}

