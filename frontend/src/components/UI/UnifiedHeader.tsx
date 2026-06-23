import React, { memo } from "react"

// Outer container for the page header, ensuring consistent padding, height, border, and flex layout.
interface HeaderContainerProps {
  children: React.ReactNode
  className?: string
}

export const HeaderContainer = memo(function HeaderContainer({
  children,
  className = "",
}: HeaderContainerProps) {
  return (
    <div className={`flex items-center justify-between px-6 py-3 border-b border-[#1a1a1a] shrink-0 font-mono select-none ${className}`}>
      {children}
    </div>
  )
})

// Standardized indicator block (■)
interface HeaderIndicatorProps {
  intent?: "green" | "purple" | "gold"
  className?: string
}

export const HeaderIndicator = memo(function HeaderIndicator({
  intent = "green",
  className = "",
}: HeaderIndicatorProps) {
  const colorClass = 
    intent === "purple" ? "text-semantic-purple" : 
    intent === "gold" ? "text-semantic-gold" : 
    "text-semantic-green"
  return (
    <span className={`${colorClass} ${className}`}>■</span>
  )
})

// Standardized bracketed action button, desaturated by default, hot orange on hover
interface HeaderActionButtonProps {
  onClick: (e: React.MouseEvent<HTMLButtonElement>) => void
  children: React.ReactNode
  className?: string
  title?: string
  disabled?: boolean
}

export const HeaderActionButton = memo(function HeaderActionButton({
  onClick,
  children,
  className = "",
  title,
  disabled,
}: HeaderActionButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`text-[11px] text-action-dim hover:text-action-hover disabled:opacity-50 disabled:pointer-events-none transition-colors cursor-pointer select-none ${className}`}
    >
      [{children}]
    </button>
  )
})

// Standardized symbia logo button/label
interface HeaderLogoProps {
  onClick?: () => void
  children?: React.ReactNode
  className?: string
  title?: string
}

export const HeaderLogo = memo(function HeaderLogo({
  onClick,
  children = "symbia",
  className = "",
  title = "Home",
}: HeaderLogoProps) {
  if (!onClick) {
    return (
      <span className={`text-[11px] text-semantic-header tracking-widest uppercase ${className}`}>
        {children}
      </span>
    )
  }
  return (
    <button
      onClick={onClick}
      title={title}
      className={`text-[11px] text-semantic-header hover:text-[#eee] tracking-widest uppercase cursor-pointer transition-colors ${className}`}
    >
      {children}
    </button>
  )
})

// Standardized double slash separator
export const HeaderSeparator = memo(function HeaderSeparator({ className = "" }: { className?: string }) {
  return <span className={`text-[#333] ${className}`}>//</span>
})

// Standardized label / scope text
interface HeaderLabelProps {
  children: React.ReactNode
  className?: string
  intent?: "purple" | "gold" | "green" | "default"
}

export const HeaderLabel = memo(function HeaderLabel({
  children,
  className = "",
  intent = "default",
}: HeaderLabelProps) {
  const colorClass = 
    intent === "purple" ? "text-semantic-purple" : 
    intent === "gold" ? "text-semantic-gold" : 
    intent === "green" ? "text-semantic-green" : 
    "text-semantic-header"
  return (
    <span className={`text-[11px] tracking-widest uppercase ${colorClass} ${className}`}>
      {children}
    </span>
  )
})
