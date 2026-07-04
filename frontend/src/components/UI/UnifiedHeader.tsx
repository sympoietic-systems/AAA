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
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void
  href?: string
  children: React.ReactNode
  className?: string
  title?: string
  disabled?: boolean
}

export const HeaderActionButton = memo(function HeaderActionButton({
  onClick,
  href,
  children,
  className = "",
  title,
  disabled,
}: HeaderActionButtonProps) {
  const sharedClass = `text-[11px] text-action-dim hover:text-action-hover disabled:opacity-50 disabled:pointer-events-none transition-colors cursor-pointer select-none ${className}`
  if (href) {
    return (
      <a href={href} title={title} className={sharedClass} style={{ textDecoration: "none", color: "inherit" }}>
        [{children}]
      </a>
    )
  }
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={sharedClass}
    >
      [{children}]
    </button>
  )
})

// Standardized symbia logo button/label
interface HeaderLogoProps {
  onClick?: () => void
  href?: string
  children?: React.ReactNode
  className?: string
  title?: string
}

export const HeaderLogo = memo(function HeaderLogo({
  onClick,
  href,
  children = "symbia",
  className = "",
  title = "Home",
}: HeaderLogoProps) {
  const sharedClass = `text-[11px] text-semantic-header hover:text-[#eee] tracking-widest uppercase transition-colors ${className}`
  if (href) {
    return (
      <a href={href} title={title} className={sharedClass} style={{ textDecoration: "none", color: "inherit" }}>
        {children}
      </a>
    )
  }
  if (onClick) {
    return (
      <button onClick={onClick} title={title} className={`cursor-pointer ${sharedClass}`}>
        {children}
      </button>
    )
  }
  return (
    <span className={`text-[11px] text-semantic-header tracking-widest uppercase ${className}`}>
      {children}
    </span>
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
