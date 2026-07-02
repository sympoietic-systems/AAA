import { memo } from "react"
import type { ResultRendererProps } from "./types"

export const SearchResult = memo(function SearchResult({
  selected, selectedResults, inputEntries,
}: ResultRendererProps) {
  const searchQueries = inputEntries
    ?.filter(e => e.event_type === "orchestrator_search")
    .map(e => ({
      query: (e.event_data as any)?.query || "",
      resultsCount: (e.event_data as any)?.results_count ?? 0,
    })) ?? []

  const directEntry = inputEntries?.find(e =>
    e.event_type === "orchestrator_search" &&
    (e.event_data as any)?.query === "direct_urls"
  )
  const directUrls: string[] = directEntry ? ((directEntry.event_data as any)?.urls ?? []) : []
  const isDirectGroup = directUrls.length > 0 || selected.query_text?.startsWith("Direct:")

  if (isDirectGroup) {
    return (
      <div className="border-t border-ui-border pt-2 space-y-2">
        <div className="flex items-center gap-1.5">
          <span className="text-semantic-purple text-[8px] font-mono">⤷ direct fetch</span>
          <span className="text-ui-dim text-[8px]">bypass search engine</span>
        </div>
        <div>
          <div className="text-ui-dim text-[8px] uppercase mb-1">urls to fetch directly ({directUrls.length || selectedResults.length})</div>
          <div className="space-y-0.5">
            {(directUrls.length > 0 ? directUrls : selectedResults.map(r => r.source_url)).map((u, i) => (
              <div key={i} className="pl-2 py-0.5 border-l border-ui-border">
                <a href={u || "#"} target="_blank" rel="noopener noreferrer"
                  className="text-action-dim hover:text-action-hover underline break-all text-[9px] transition-colors">
                  {u || "—"}
                </a>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="border-t border-ui-border pt-2 space-y-2">
      {searchQueries.length > 0 ? (
        <>
          <div className="text-ui-dim text-[8px] uppercase">search queries ({searchQueries.length})</div>
          {searchQueries.map((sq, qi) => (
            <div key={qi} className="pl-2 border-l border-ui-border">
              <div className="text-ui-secondary text-[9px] leading-relaxed">"{sq.query}"</div>
              <div className="text-ui-dim text-[8px]">{sq.resultsCount} results</div>
            </div>
          ))}
        </>
      ) : selected.query_text ? (
        <div className="pl-2 border-l border-ui-border">
          <div className="text-ui-dim text-[8px] uppercase">search query</div>
          <div className="text-ui-secondary text-[9px] leading-relaxed font-mono">"{selected.query_text}"</div>
        </div>
      ) : null}

      {selectedResults.length > 0 ? (
        <div className="pt-1">
          <div className="text-ui-dim text-[8px] mb-1 uppercase">urls to parse at next step ({selectedResults.length})</div>
          {selectedResults.map(r => (
            <div key={r.id} className="pl-2 py-0.5">
              <a href={r.source_url || "#"} target="_blank" rel="noopener noreferrer"
                className="text-action-dim hover:text-action-hover underline break-all text-[9px] transition-colors">
                {r.source_title || r.source_url?.slice(0, 100) || "—"}
              </a>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-ui-dim italic text-[9px] pl-2">
          {searchQueries.some(sq => sq.resultsCount > 0)
            ? `${searchQueries.reduce((sum, sq) => sum + sq.resultsCount, 0)} links found — fetch + analysis in parse/digest steps`
            : "no urls found"}
        </div>
      )}
    </div>
  )
})
