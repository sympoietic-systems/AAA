import { useRef, useState, useCallback, type ChangeEvent, type DragEvent, type FormEvent, type KeyboardEvent } from "react"

const ACCEPTED_EXTENSIONS = ".pdf,.txt,.md,.docx,.py,.json,.yaml,.yml,.csv,.xml,.html,.css,.js,.ts,.tsx,.jsx,.rs,.go,.java,.c,.h,.cpp,.hpp,.sh,.bat,.ps1,.toml,.ini,.cfg,.env,.log"

interface Props {
  onSend: (text: string) => void
  onUploadFiles: (files: File[]) => void
  disabled?: boolean
  isIndexing?: boolean
}

export function InputBar({ onSend, onUploadFiles, disabled, isIndexing }: Props) {
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [inputExpanded, setInputExpanded] = useState(false)

  const processFiles = useCallback((fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return
    onUploadFiles(Array.from(fileList))
  }, [onUploadFiles])

  const handleInput = () => {
    const el = inputRef.current
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
        inputRef.current.style.height = "auto"
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
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`flex items-center border-t border-[#222] bg-[#0f0f0f] px-4 py-3 transition-colors ${
          dragOver ? "border-[#4ade80] bg-[#111]" : isIndexing ? "border-[#eab308]/40 bg-[#0f0f0c]" : ""
        }`}
      >
        <span className={`mr-2 select-none text-sm font-mono ${
          isIndexing ? "text-[#eab308] animate-pulse" : "text-[#4ade80]"
        }`}>
          {isIndexing ? "•" : ">"}
        </span>
        <textarea
          ref={inputRef}
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
        <button
          type="button"
          onClick={() => {
            setInputExpanded(!inputExpanded)
            if (inputExpanded && inputRef.current) {
              inputRef.current.style.height = "auto"
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
        <button
          type="submit"
          disabled={!canSubmit}
          className={`ml-2 text-xs uppercase px-2 py-1 rounded transition-colors ${
            canSubmit
              ? "text-[#4ade80] hover:bg-[#1f2937]"
              : "text-[#333] cursor-not-allowed"
          }`}
          title="Send message"
        >
          Send
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

