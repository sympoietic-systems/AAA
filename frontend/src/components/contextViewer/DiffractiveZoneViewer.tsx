import React, { useEffect, useState } from 'react';

interface ParsedDiffractiveFragment {
  sourceType: string;
  title: string;
  similarity: number;
  content: string;
}

interface ParsedDiffractiveZone {
  fragments: ParsedDiffractiveFragment[];
  directive: string;
}

function parseDiffractiveZone(content: string): ParsedDiffractiveZone {
  // Remove [system]: prefixes and closing XML tag
  let text = content
    .replace(/^\[system\]:\s*/gm, '')
    .replace('</diffractive_interference_zone>', '')
    .trim();

  const fragments: ParsedDiffractiveFragment[] = [];
  let directive = '';

  // Pattern: [Source: Type Fragment (title) | Similarity δ: 0.xxx]\n"""\nbody\n"""
  // Source type can be one or more word-ish tokens (e.g. "Nomadic", "Semantic_knot")
  const fragmentRegex = /\[Source:\s*([\w\s]+?)\s+Fragment\s*\(([^)]*)\)\s*\|\s*Similarity\s*[δd]\s*:\s*([\d.]+)\]\s*\n"""(?:\s*\n)?([\s\S]*?)\n?"""/g;
  let match;
  while ((match = fragmentRegex.exec(text)) !== null) {
    fragments.push({
      sourceType: match[1].trim(),
      title: match[2].trim(),
      similarity: parseFloat(match[3]),
      content: match[4].trim(),
    });
  }

  // Directive: [URGENT ATTENTION DIRECTIVE]\n... rest (strip trailing closing tag if any)
  const dirMatch = text.match(/\[URGENT ATTENTION DIRECTIVE\]\s*\n([\s\S]*)$/);
  if (dirMatch) {
    directive = dirMatch[1].replace('</diffractive_interference_zone>', '').trim();
  }

  return { fragments, directive };
}

export const DiffractiveZoneViewer: React.FC<{ content: string }> = ({ content }) => {
  const parsed = parseDiffractiveZone(content);

  const tabs: { id: string; label: string; count?: number }[] = [];
  if (parsed.fragments.length > 0) {
    tabs.push({ id: 'fragments', label: 'Fragments', count: parsed.fragments.length });
  }
  if (parsed.directive) {
    tabs.push({ id: 'directive', label: 'Directive' });
  }
  tabs.push({ id: 'raw', label: 'Raw' });

  const [activeTab, setActiveTab] = useState<string>(tabs[0]?.id || 'raw');

  // Sync activeTab if it becomes invalid (e.g., no fragments + no directive)
  useEffect(() => {
    if (!tabs.find(t => t.id === activeTab) && tabs.length > 0) {
      setActiveTab(tabs[0].id);
    }
  }, [tabs, activeTab]);

  return (
    <div className="flex flex-col gap-2.5">
      {/* Tab bar */}
      <div className="flex border-b border-[#2d2d3d] pb-1 gap-1.5 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-2 py-0.5 text-[8.5px] rounded font-bold tracking-wide uppercase transition-all duration-200 border whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-[#1e1518] text-[#f43f5e] border-[#f43f5e]/30'
                : 'text-[#94a3b8]/50 border-transparent hover:text-[#94a3b8] hover:bg-[#1a1a24]/30'
            }`}
          >
            {tab.label}{tab.count != null ? ` (${tab.count})` : ''}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex flex-col gap-2 max-h-[350px] overflow-y-auto pr-1">
        {activeTab === 'fragments' && (
          <div className="flex flex-col gap-2.5">
            {parsed.fragments.map((frag, i) => (
              <div
                key={i}
                className="flex flex-col gap-1.5 p-2 rounded border border-[#f43f5e]/15 bg-[#1a0a0e]/40 hover:border-[#f43f5e]/30 transition-colors"
              >
                <div className="flex flex-wrap items-center justify-between gap-1.5 text-[8px] border-b border-[#f43f5e]/10 pb-1">
                  <div className="flex items-center gap-1.5">
                    <span className="px-1 py-0.5 rounded text-[7px] font-bold uppercase tracking-wider bg-[#f43f5e]/10 text-[#f43f5e] border border-[#f43f5e]/20">
                      {frag.sourceType}
                    </span>
                    <span className="font-bold text-[#fb7185] truncate max-w-[180px]" title={frag.title}>
                      {frag.title}
                    </span>
                  </div>
                  <span className="text-[#f43f5e]/70 font-mono text-[7.5px]">
                    δ={frag.similarity.toFixed(3)}
                  </span>
                </div>
                <div className="text-[9.5px] leading-relaxed whitespace-pre-wrap text-[#c0caf5] px-1.5 py-1 bg-[#050507]/60 rounded border border-[#f43f5e]/5 select-text">
                  {frag.content}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'directive' && parsed.directive && (
          <div className="flex flex-col gap-1.5 p-2 rounded border border-[#f43f5e]/15 bg-[#1a0a0e]/40">
            <span className="text-[8px] uppercase tracking-wider font-bold text-[#f43f5e]/70 border-b border-[#f43f5e]/10 pb-1">
              SEC-4 Diffractive Protocol
            </span>
            <div className="text-[10px] leading-relaxed whitespace-pre-wrap text-[#fca5a5]">
              {parsed.directive}
            </div>
          </div>
        )}

        {activeTab === 'raw' && (
          <div className="whitespace-pre-wrap text-[10px] leading-relaxed select-text text-[#c0caf5]">
            {content}
          </div>
        )}
      </div>
    </div>
  );
};
