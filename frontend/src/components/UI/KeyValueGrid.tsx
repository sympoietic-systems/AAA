import { memo } from "react"

interface KVItem {
  key: string
  value: string | number
  valueColor?: string
}

interface KeyValueGridProps {
  items: KVItem[]
  className?: string
}

function KeyValueGridComponent({ items, className = "" }: KeyValueGridProps) {
  if (items.length === 0) return null

  return (
    <div className={`flex flex-wrap gap-x-4 gap-y-0.5 text-[10px] font-mono text-[#888] ${className}`}>
      {items.map((item, i) => (
        <span key={i}>
          <span className="text-[#555]">{item.key}:</span>{" "}
          <span
            className={item.valueColor ? "" : "text-[#94a3b8]"}
            style={item.valueColor ? { color: item.valueColor } : undefined}
          >
            {item.value}
          </span>
        </span>
      ))}
    </div>
  )
}

export const KeyValueGrid = memo(KeyValueGridComponent)
