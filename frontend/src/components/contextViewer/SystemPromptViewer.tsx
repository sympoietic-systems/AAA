import React, { useEffect, useState } from 'react';

interface ParsedSystemPrompt {
  identity: string;
  skills: { label: string; items: string[] }[];
  beliefs: { label: string; items: string[] }[];
  directives: { label: string; content: string }[];
}

function parseSystemPrompt(content: string): ParsedSystemPrompt {
  // Strip the leading [system]: prefix that ContextViewer prepends
  let text = content.replace(/^\[system\]:\s*/, '');

  const result: ParsedSystemPrompt = {
    identity: '',
    skills: [],
    beliefs: [],
    directives: [],
  };

  // Match all --- BEGIN TYPE (SUBTYPE) --- ... --- END TYPE (SUBTYPE) --- blocks
  const blockRegex = /--- BEGIN (\w+) \(([^)]+)\) ---\n([\s\S]*?)--- END \1 \(\2\) ---/g;

  const blocks: { index: number; type: string; subtype: string; body: string }[] = [];
  let match: RegExpExecArray | null;
  while ((match = blockRegex.exec(text)) !== null) {
    blocks.push({
      index: match.index,
      type: match[1].toLowerCase(),
      subtype: match[2],
      body: match[3].trim(),
    });
  }
  blocks.sort((a, b) => a.index - b.index);

  // Identity is everything before the first block
  if (blocks.length > 0) {
    result.identity = text.slice(0, blocks[0].index).trim();
  } else {
    result.identity = text.trim();
    return result;
  }

  for (const block of blocks) {
    const lines = block.body.split('\n').map(l => l.trim()).filter(Boolean);
    // First line is usually a description/header line, skip it
    const bodyLines = lines.length > 0 && !lines[0].startsWith('- ') ? lines.slice(1) : lines;
    const items = bodyLines.filter(l => l.startsWith('- ') || l.startsWith('Call ')).map(l => l.replace(/^-\s*/, ''));

    if (block.type === 'skills') {
      if (items.length > 0) {
        result.skills.push({ label: block.subtype, items });
      }
    } else if (block.type === 'beliefs') {
      if (items.length > 0) {
        result.beliefs.push({ label: block.subtype, items });
      }
    } else if (block.type === 'directive') {
      if (block.body) {
        result.directives.push({ label: block.subtype, content: block.body });
      }
    }
  }

  // Also parse SKILL ECOLOGY NOTES (legacy format still used for ecology notes)
  const ecologyMatch = text.match(/--- BEGIN SKILL ECOLOGY NOTES ---\n([\s\S]*?)--- END SKILL ECOLOGY NOTES ---/);
  if (ecologyMatch) {
    const ecoLines = ecologyMatch[1].trim().split('\n').map(l => l.trim()).filter(Boolean);
    if (ecoLines.length > 0) {
      result.skills.push({ label: 'Ecology Notes', items: ecoLines });
    }
  }

  return result;
}

export const SystemPromptViewer: React.FC<{ content: string }> = ({ content }) => {
  const parsed = parseSystemPrompt(content);

  const tabs: { id: string; label: string; count?: number }[] = [];
  if (parsed.identity) tabs.push({ id: 'identity', label: 'Identity' });
  if (parsed.skills.length > 0) {
    const totalSkills = parsed.skills.reduce((sum, s) => sum + s.items.length, 0);
    tabs.push({ id: 'skills', label: 'Skills', count: totalSkills });
  }
  if (parsed.beliefs.length > 0) {
    const totalBeliefs = parsed.beliefs.reduce((sum, b) => sum + b.items.length, 0);
    tabs.push({ id: 'beliefs', label: 'Beliefs', count: totalBeliefs });
  }
  if (parsed.directives.length > 0) tabs.push({ id: 'directives', label: 'Directives', count: parsed.directives.length });
  tabs.push({ id: 'raw', label: 'Raw' });

  const [activeTab, setActiveTab] = useState<string>(tabs[0]?.id || 'raw');

  // Sync activeTab if it becomes invalid (e.g., when no identity tab exists)
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
                ? 'bg-[#1e1e2e] text-[#94a3b8] border-[#475569]/40'
                : 'text-[#94a3b8]/50 border-transparent hover:text-[#94a3b8] hover:bg-[#1a1a24]/30'
            }`}
          >
            {tab.label}{tab.count != null ? ` (${tab.count})` : ''}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex flex-col gap-2 max-h-[350px] overflow-y-auto pr-1">
        {activeTab === 'identity' && parsed.identity && (
          <div className="whitespace-pre-wrap text-[10px] leading-relaxed select-text text-[#c0caf5]">
            {parsed.identity}
          </div>
        )}

        {activeTab === 'skills' && (
          <div className="flex flex-col gap-3">
            {parsed.skills.map((section, si) => (
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
                      ) : (
                        item
                      )}
                    </span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'beliefs' && (
          <div className="flex flex-col gap-3">
            {parsed.beliefs.map((section, si) => {
              const isCollapsed = section.label.toLowerCase().includes('collapsed');
              return (
                <div key={si} className="flex flex-col gap-1.5">
                  <span className={`text-[8px] uppercase tracking-wider font-bold pb-1 border-b ${
                    isCollapsed ? 'text-[#ef4444]/70 border-[#ef4444]/10' : 'text-[#60a5fa]/70 border-[#60a5fa]/10'
                  }`}>
                    {section.label}
                  </span>
                  {section.items.map((item, ii) => {
                    // Parse belief format: "Slot N: [confidence] statement (Ontological Mass: M)" or "[confidence] statement"
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

        {activeTab === 'directives' && (
          <div className="flex flex-col gap-3">
            {parsed.directives.map((d, i) => (
              <div
                key={i}
                className="flex flex-col gap-1.5 p-2 rounded border border-[#f59e0b]/10 bg-[#1a1508]/40"
              >
                <span className="text-[8px] uppercase tracking-wider font-bold text-[#f59e0b]/70 border-b border-[#f59e0b]/10 pb-1">
                  {d.label}
                </span>
                <div className="text-[9.5px] leading-relaxed whitespace-pre-wrap text-[#c0caf5]">
                  {d.content}
                </div>
              </div>
            ))}
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
