import { useRef } from "react"
import type { FormEvent, KeyboardEvent } from "react"

interface Props {
  onSend: (text: string) => void
  disabled?: boolean
}

export function InputBar({ onSend, disabled }: Props) {
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const text = inputRef.current?.value.trim()
    if (text) {
      onSend(text)
      if (inputRef.current) inputRef.current.value = ""
    }
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center border-t border-[#222] bg-[#0f0f0f] px-4 py-3"
    >
      <span className="text-[#4ade80] mr-2 select-none text-sm">&gt;</span>
      <textarea
        ref={inputRef}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        rows={1}
        placeholder="type a message..."
        className="flex-1 resize-none bg-transparent text-[#ddd] text-sm outline-none
                   placeholder:text-[#444] disabled:opacity-30"
      />
    </form>
  )
}
