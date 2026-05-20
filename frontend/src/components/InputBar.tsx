import { useRef, useState, useCallback, type ChangeEvent, type DragEvent, type FormEvent, type KeyboardEvent } from "react"

interface FileInfo {
  file: File
  name: string
  type: string
  preview?: string
  tokenCount?: number
}

function estimateTokens(text: string): number {
  if (!text) return 0
  return Math.max(1, Math.floor(text.length / 4))
}

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return `${n}`
}

function getFileIcon(fileType: string): string {
  switch (fileType) {
    case "pdf": return "\uD83D\uDCC4"
    case "docx": return "\uD83D\uDCC3"
    case "md": return "\uD83D\uDCDD"
    case "image": return "\uD83D\uDDBC"
    default: return "\uD83D\uDCC4"
  }
}

const ACCEPTED_EXTENSIONS = ".pdf,.txt,.md,.docx,.py,.json,.yaml,.yml,.csv,.xml,.html,.css,.js,.ts,.tsx,.jsx,.rs,.go,.java,.c,.h,.cpp,.hpp,.sh,.bat,.ps1,.toml,.ini,.cfg,.env,.log"

interface Props {
  onSend: (text: string, files?: File[]) => void
  disabled?: boolean
}

export function InputBar({ onSend, disabled }: Props) {
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<FileInfo[]>([])
  const [dragOver, setDragOver] = useState(false)

  const processFiles = useCallback((fileList: FileList | null) => {
    if (!fileList) return
    const newFiles: FileInfo[] = []
    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i]
      const ext = file.name.split(".").pop()?.toLowerCase() || "txt"
      let fileType = "txt"
      if (ext === "pdf") fileType = "pdf"
      else if (ext === "docx") fileType = "docx"
      else if (ext === "md") fileType = "md"
      else if (["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"].includes(ext)) fileType = "image"

      const info: FileInfo = { file, name: file.name, type: fileType }

      if (fileType === "image") {
        const url = URL.createObjectURL(file)
        info.preview = url
      } else if (fileType === "txt" || fileType === "md") {
        const reader = new FileReader()
        reader.onload = () => {
          const text = reader.result as string
          setFiles((prev) =>
            prev.map((f) =>
              f.name === file.name ? { ...f, tokenCount: estimateTokens(text) } : f
            )
          )
        }
        reader.readAsText(file)
      }

      newFiles.push(info)
    }
    setFiles((prev) => [...prev, ...newFiles])
  }, [])

  const removeFile = useCallback((name: string) => {
    setFiles((prev) => {
      const file = prev.find((f) => f.name === name)
      if (file?.preview) URL.revokeObjectURL(file.preview)
      return prev.filter((f) => f.name !== name)
    })
  }, [])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const text = inputRef.current?.value.trim()
    if (text) {
      onSend(text, files.map((f) => f.file))
      if (inputRef.current) inputRef.current.value = ""
      files.forEach((f) => { if (f.preview) URL.revokeObjectURL(f.preview) })
      setFiles([])
    }
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
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

  return (
    <div>
      {files.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-4 pt-2 pb-1">
          {files.map((f) => (
            <div
              key={f.name}
              className="flex items-center gap-1.5 bg-[#1a1a1a] border border-[#333] rounded px-2 py-1 text-xs group"
            >
              {f.preview ? (
                <img
                  src={f.preview}
                  alt={f.name}
                  className="w-5 h-5 rounded object-cover"
                />
              ) : (
                <span className="text-sm">{getFileIcon(f.type)}</span>
              )}
              <span className="text-[#aaa] max-w-32 truncate">{f.name}</span>
              {f.tokenCount != null && (
                <span className="text-[#666] text-[10px]">
                  ~{formatTokens(f.tokenCount)} tok
                </span>
              )}
              <button
                type="button"
                onClick={() => removeFile(f.name)}
                className="text-[#555] hover:text-[#ef4444] ml-0.5"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
      <form
        onSubmit={handleSubmit}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`flex items-center border-t border-[#222] bg-[#0f0f0f] px-4 py-3 transition-colors ${dragOver ? "border-[#4ade80] bg-[#111]" : ""}`}
      >
        <span className="text-[#4ade80] mr-2 select-none text-sm">&gt;</span>
        <textarea
          ref={inputRef}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          placeholder={dragOver ? "drop files here..." : "type a message..."}
          className="flex-1 resize-none bg-transparent text-[#ddd] text-sm outline-none
                     placeholder:text-[#444] disabled:opacity-30"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="ml-2 text-[#555] hover:text-[#4ade80] text-lg leading-none disabled:opacity-30 transition-colors"
          title="Attach files"
        >
          +
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
