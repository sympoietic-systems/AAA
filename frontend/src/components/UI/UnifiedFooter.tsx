import { memo } from "react"

export const UnifiedFooter = memo(function UnifiedFooter({ className = "" }: { className?: string }) {
  return (
    <footer className={`flex flex-col sm:flex-row items-center justify-between px-4 py-2.5 border-t border-[#1a1a1a]/60 bg-[#0c0c0c] text-[10px] font-mono text-[#555] shrink-0 select-none ${className}`}>
      <div className="flex items-center gap-1">
        <span>© {new Date().getFullYear()}</span>
        <a
          href="http://sympoietic.systems/"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-[#888] transition-colors underline decoration-[#222] underline-offset-2"
        >
          sympoietic.systems
        </a>
      </div>
      <div className="mt-1 sm:mt-0">
        <a
          href="https://github.com/sympoietic-systems/AAA"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-[#888] transition-colors underline decoration-[#222] underline-offset-2"
        >
          git repository
        </a>
      </div>
    </footer>
  )
})
