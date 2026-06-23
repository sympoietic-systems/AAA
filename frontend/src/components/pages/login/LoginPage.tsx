import React, { memo, useState, useEffect, useRef } from "react"
import { UnifiedFooter } from "../../UI"

interface Props {
  onPasswordSubmit: (password: string) => void
  authError: string | null
  onClearError: () => void
}

export const LoginPage = memo(function LoginPage({
  onPasswordSubmit,
  authError,
  onClearError,
}: Props) {
  const [password, setPassword] = useState("")
  const [unlocking, setUnlocking] = useState(false)
  const [keystrokes, setKeystrokes] = useState("")
  const passwordRef = useRef<HTMLInputElement>(null)

  const handlePasswordKey = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setPassword(val)
    setKeystrokes(val.length > 0 ? "·".repeat(Math.min(val.length, 3)) : "")
    if (authError) onClearError()
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!password.trim() || unlocking) return
    setUnlocking(true)
    onPasswordSubmit(password.trim())
    // Keep unlocking status matching the verify API lifetime
    setTimeout(() => setUnlocking(false), 1500)
  }

  const handleTearClick = () => {
    passwordRef.current?.focus()
  }

  return (
    <div className="flex flex-col items-center justify-between h-screen w-screen bg-[#0c0c0c] font-mono select-none overflow-hidden text-[#666]">
      <div className="flex flex-col items-center justify-center w-[50%] min-w-[320px] max-w-[800px] px-8 flex-1">
        <div className="w-full">
          {/* ── The Tear ── */}
          <div className="relative">
            <div
              className="h-px w-full bg-[#1a1a1a] cursor-text shadow-[0_0_6px_rgba(100,100,100,0.15)]"
              onClick={handleTearClick}
            />
            <input
              ref={passwordRef}
              type="password"
              value={password}
              onChange={handlePasswordKey}
              className="absolute inset-0 opacity-0 cursor-text pointer-events-auto w-full h-full"
              autoFocus
            />
          </div>

          <div className="text-[#555] text-[12px] font-mono text-center mt-3 min-h-[1.2rem] select-none transition-opacity duration-1000">
            {keystrokes}
          </div>

          {authError && (
            <div
              className="text-[#ef4444] text-[9px] text-center mt-1 cursor-pointer select-none"
              onClick={onClearError}
            >
              {authError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="text-center mt-2">
            <button
              type="submit"
              disabled={!password.trim() || unlocking}
              className="text-[10px] text-[#666] font-mono cursor-pointer transition-colors hover:text-[#4ade80] disabled:text-[#333] disabled:cursor-not-allowed"
            >
              [{unlocking ? "…" : "unlock"}]
            </button>
          </form>
        </div>
      </div>
      <UnifiedFooter className="w-full" />
    </div>
  )
})
