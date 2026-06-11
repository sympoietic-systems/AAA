import React, { useEffect, useState, useMemo } from 'react';

interface ParsedDiffractiveFragment {
  sourceType: string;
  title: string;
  similarity: number;
  content: string;
  messageId?: number;
  conversationId?: string;
}

interface ParsedDiffractiveZone {
  fragments: ParsedDiffractiveFragment[];
  directive: string;
}

function parseDiffractiveZone(content: string): ParsedDiffractiveZone {
  // Content now arrives pre-cleaned by the parser (tags and [system]: prefixes already stripped).
  // Still normalize any leftover formatting as a safety net.
  let text = content
    .replace(/^\[system\]:\s*/gm, '')
    .replace('</diffractive_interference_zone>', '')
    .replace('<diffractive_interference_zone>', '')
    .trim();

  const fragments: ParsedDiffractiveFragment[] = [];
  let directive = '';

  // Pattern: [Source: Type Fragment (title) | Similarity δ: 0.xxx | msg: msg_id | conv: conv_id]\n"""\nbody\n"""
  // Source type can be one or more word-ish tokens (e.g. "Nomadic", "Semantic_knot")
  const fragmentRegex = /\[Source:\s*([\w\s]+?)\s+Fragment\s*\(([^)]*)\)\s*\|\s*Similarity\s*[δd]\s*:\s*([\d.]+?)(?:\s*\|\s*msg:\s*(\d+))?(?:\s*\|\s*conv:\s*([^\]|]+))?\]\s*\n"""(?:\s*\n)?([\s\S]*?)\n?"""/g;
  let match;
  while ((match = fragmentRegex.exec(text)) !== null) {
    fragments.push({
      sourceType: match[1].trim(),
      title: match[2].trim(),
      similarity: parseFloat(match[3]),
      messageId: match[4] ? parseInt(match[4], 10) : undefined,
      conversationId: match[5] ? match[5].trim() : undefined,
      content: match[6].trim(),
    });
  }

  // Directive: [URGENT ATTENTION DIRECTIVE]\n... rest
  const dirMatch = text.match(/\[URGENT ATTENTION DIRECTIVE\]\s*\n([\s\S]*)$/);
  if (dirMatch) {
    // Clean up trailing [user]: or [system]: prefixes that may have leaked in
    directive = dirMatch[1]
      .replace(/\n\[user\]:[\s\S]*$/, '')   // Strip trailing user query if stuck to directive
      .trim();
  }

  return { fragments, directive };
}

// Fallback: extract system-prompt-style blocks from content that leaked into diffractive zone
function extractSystemBlocks(content: string): { skills: { label: string; items: string[] }[]; beliefs: { label: string; items: string[] }[] } {
  const skills: { label: string; items: string[] }[] = [];
  const beliefs: { label: string; items: string[] }[] = [];
  const blockRegex = /--- BEGIN (SKILLS|BELIEFS) \(([^)]+)\) ---\r?\n([\s\S]*?)--- END \1 \(\2\) ---/g;
  let m: RegExpExecArray | null;
  while ((m = blockRegex.exec(content)) !== null) {
    const blockType = m[1].toLowerCase() as 'skills' | 'beliefs';
    const subtype = m[2];
    const body = m[3].trim();
    const lines = body.split('\n').map(l => l.trim()).filter(Boolean);
    const bodyLines = lines.length > 0 && !lines[0].startsWith('- ') ? lines.slice(1) : lines;
    const items = bodyLines.filter(l => l.startsWith('- ') || l.startsWith('Call ')).map(l => l.replace(/^-\s*/, ''));
    if (items.length > 0) {
      if (blockType === 'skills') skills.push({ label: subtype, items });
      else beliefs.push({ label: subtype, items });
    }
  }
  return { skills, beliefs };
}

export const DiffractiveZoneViewer: React.FC<{ content: string }> = ({ content }) => {
  const parsed = useMemo(() => parseDiffractiveZone(content), [content]);

  // Fallback: if no fragments/directive found but content has system prompt blocks, extract them
  const systemBlocks = useMemo(() => {
    if (parsed.fragments.length === 0 && !parsed.directive) {
      return extractSystemBlocks(content);
    }
    return { skills: [] as { label: string; items: string[] }[], beliefs: [] as { label: string; items: string[] }[] };
  }, [content, parsed]);

  const hasSystemBlocks = systemBlocks.skills.length > 0 || systemBlocks.beliefs.length > 0;

  const tabs: { id: string; label: string; count?: number }[] = [];
  if (parsed.fragments.length > 0) {
    tabs.push({ id: 'fragments', label: 'Fragments', count: parsed.fragments.length });
  }
  if (parsed.directive) {
    tabs.push({ id: 'directive', label: 'Directive' });
  }
  if (hasSystemBlocks) {
    if (systemBlocks.skills.length > 0) {
      const count = systemBlocks.skills.reduce((s, g) => s + g.items.length, 0);
      tabs.push({ id: 'skills', label: 'Skills', count });
    }
    if (systemBlocks.beliefs.length > 0) {
      const count = systemBlocks.beliefs.reduce((s, g) => s + g.items.length, 0);
      tabs.push({ id: 'beliefs', label: 'Beliefs', count });
    }
  }
  tabs.push({ id: 'raw', label: 'Raw' });

  const [activeTab, setActiveTab] = useState<string>(tabs[0]?.id || 'raw');

  // Sync activeTab if it becomes invalid
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
                    {frag.conversationId ? (
                      <a
                        href={`/?c=${encodeURIComponent(frag.conversationId)}${frag.messageId ? `&m=${frag.messageId}` : ""}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-bold text-[#fb7185] hover:text-[#fb923c] transition-colors truncate max-w-[180px] hover:underline"
                        title={`Sediment Fold: Open conversation in new tab`}
                      >
                        {frag.title}
                      </a>
                    ) : (
                      <span className="font-bold text-[#fb7185] truncate max-w-[180px]" title={frag.title}>
                        {frag.title}
                      </span>
                    )}
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

        {activeTab === 'skills' && hasSystemBlocks && (
          <div className="flex flex-col gap-3">
            {systemBlocks.skills.map((section, si) => (
              <div key={si} className="flex flex-col gap-1.5">
                <span className="text-[8px] uppercase tracking-wider font-bold text-[#4ade80]/70 border-b border-[#4ade80]/10 pb-1">
                  {section.label}
                </span>
                {section.items.map((item, ii) => (
                  <div
                    key={ii}
                    className="flex items-start gap-2 p-1.5 rounded border border-[#4ade80]/10 bg-[#0a1a10]/40 hover:bg-[#0a1a10]/70 transition-colors"
                  >
                    <span className="text-[#4ade80] text-[9px] mt-0.5 shrink-0">◆</span>
                    <span className="text-[9.5px] leading-relaxed text-[#c0caf5]">
                      {item.includes(': ') ? (
                        <>
                          <span className="text-[#4ade80] font-semibold">{item.split(': ')[0]}</span>
                          <span className="text-[#94a3b8]">: {item.split(': ').slice(1).join(': ')}</span>
                        </>
                      ) : item}
                    </span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'beliefs' && hasSystemBlocks && (
          <div className="flex flex-col gap-3">
            {systemBlocks.beliefs.map((section, si) => {
              const isCollapsed = section.label.toLowerCase().includes('collapsed');
              return (
                <div key={si} className="flex flex-col gap-1.5">
                  <span className={`text-[8px] uppercase tracking-wider font-bold pb-1 border-b ${
                    isCollapsed ? 'text-[#ef4444]/70 border-[#ef4444]/10' : 'text-[#60a5fa]/70 border-[#60a5fa]/10'
                  }`}>
                    {section.label}
                  </span>
                  {section.items.map((item, ii) => {
                    const slotMatch = item.match(/^Slot\s+(\d+):\s+\[([\d.]+)\]\s+(.+?)\s+\(Ontological Mass:\s+([\d.]+)\)(.*)$/);
                    const simpleMatch = item.match(/^\[([\d.]+)\]\s+(.+)$/);
                    return (
                      <div
                        key={ii}
                        className={`flex items-start gap-2 p-1.5 rounded border transition-colors ${
                          isCollapsed
                            ? 'border-[#ef4444]/10 bg-[#1a0a0a]/30 hover:bg-[#1a0a0a]/50'
                            : 'border-[#60a5fa]/10 bg-[#0a1220]/40 hover:bg-[#0a1220]/70'
                        }`}
                      >
                        <span className={`text-[9px] mt-0.5 shrink-0 ${isCollapsed ? 'text-[#ef4444]' : 'text-[#60a5fa]'}`}>
                          {isCollapsed ? '◈' : '●'}
                        </span>
                        <div className="flex flex-col gap-0.5 text-[9.5px] leading-relaxed">
                          {slotMatch ? (
                            <>
                              <span className="text-[#c0caf5]">
                                <span className="text-[#94a3b8] text-[8px]">Slot {slotMatch[1]}: </span>
                                {slotMatch[3]}
                              </span>
                              <div className="flex gap-2 text-[8px]">
                                <span className="text-[#60a5fa]">conf: {slotMatch[2]}</span>
                                <span className="text-[#a78bfa]">mass: {slotMatch[4]}</span>
                                {slotMatch[5] && <span className="text-[#94a3b8]/60">{slotMatch[5].trim()}</span>}
                              </div>
                            </>
                          ) : simpleMatch ? (
                            <>
                              <span className={isCollapsed ? 'text-[#94a3b8]/60 line-through' : 'text-[#c0caf5]'}>
                                {simpleMatch[2]}
                              </span>
                              <span className={`text-[8px] ${isCollapsed ? 'text-[#ef4444]/50' : 'text-[#60a5fa]/70'}`}>
                                conf: {simpleMatch[1]}
                              </span>
                            </>
                          ) : (
                            <span className={isCollapsed ? 'text-[#94a3b8]/60 line-through' : 'text-[#c0caf5]'}>
                              {item}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })}
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
