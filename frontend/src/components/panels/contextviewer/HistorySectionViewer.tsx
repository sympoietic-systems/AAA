import React, { useState, memo } from 'react';
import type { SectionColors } from './types';

interface ParsedHistoryMessage {
  role: string;
  isConsolidated: boolean;
  isCompressed: boolean;
  content: string;
}

function parseHistoryContent(content: string): ParsedHistoryMessage[] {
  const msgRegex = /^\[(system|user|assistant|unknown|apparatus)\]:\s*([\s\S]*?)(?=(?:^\[(?:system|user|assistant|unknown|apparatus)\]:)|(?![\s\S]))/gm;
  const matches = [...content.matchAll(msgRegex)];
  
  return matches.map(match => {
    const role = match[1];
    let msgContent = match[2].trim();
    
    let isConsolidated = false;
    let isCompressed = false;
    
    if (role === 'system' && msgContent.startsWith('[Consolidated memory:')) {
      isConsolidated = true;
      msgContent = msgContent.replace(/^\[Consolidated memory:\s*([\s\S]*?)\]$/, '$1').trim();
    } else if (msgContent.startsWith('[U]:') || msgContent.startsWith('[A]:') || msgContent.startsWith('[S]:')) {
      isCompressed = true;
      msgContent = msgContent.substring(4).trim();
    }
    
    return {
      role,
      isConsolidated,
      isCompressed,
      content: msgContent
    };
  });
}

export const HistorySectionViewer: React.FC<{ content: string; style: SectionColors }> = memo(({ content }) => {
  const parsed = parseHistoryContent(content);
  const consolidated = parsed.filter(m => m.isConsolidated);
  const compressed = parsed.filter(m => m.isCompressed);
  const raw = parsed.filter(m => !m.isConsolidated && !m.isCompressed);

  const tabs: { id: string; label: string; count: number; messages: ParsedHistoryMessage[] }[] = [];
  if (consolidated.length > 0) {
    tabs.push({ id: 'consolidated', label: 'Consolidated', count: consolidated.length, messages: consolidated });
  }
  if (compressed.length > 0) {
    tabs.push({ id: 'compressed', label: 'Compressed', count: compressed.length, messages: compressed });
  }
  if (raw.length > 0) {
    tabs.push({ id: 'raw', label: 'Raw (Floating)', count: raw.length, messages: raw });
  }

  const [activeTab, setActiveTab] = useState(tabs[0]?.id || 'raw');

  if (tabs.length === 0) {
    return <div className="whitespace-pre-wrap select-text">{content}</div>;
  }

  const activeTabData = tabs.find(t => t.id === activeTab) || tabs[0];

  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex border-b border-[#2d2d3d] pb-1 gap-1.5 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-2 py-0.5 text-[8.5px] rounded font-bold tracking-wide uppercase transition-all duration-200 border whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-[#1e1e2e] text-[#60a5fa] border-[#60a5fa]/30'
                : 'text-[#94a3b8]/60 border-transparent hover:text-[#94a3b8] hover:bg-[#1a1a24]/30'
            }`}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-2 max-h-[350px] overflow-y-auto pr-1">
        {activeTabData.messages.map((msg, i) => (
          <div
            key={i}
            className="flex flex-col gap-1 p-2 rounded border border-[#1c1c1c] bg-[#09090e]/60 hover:bg-[#0e0e16]/80 transition-colors"
          >
            <div className="flex items-center gap-1.5 text-[7.5px] uppercase font-bold text-[#94a3b8] opacity-75">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  msg.role === 'user' ? 'bg-[#d97706]' : msg.role === 'system' ? 'bg-[#64748b]' : 'bg-[#2563eb]'
                }`}
              />
              <span>{msg.role}</span>
              {msg.isCompressed && <span className="text-[6.5px] text-[#60a5fa] bg-[#2563eb]/10 px-1 rounded border border-[#2563eb]/20 font-semibold uppercase tracking-wider">compressed</span>}
              {msg.isConsolidated && <span className="text-[6.5px] text-[#c084fc] bg-[#7c3aed]/10 px-1 rounded border border-[#7c3aed]/20 font-semibold uppercase tracking-wider">consolidated</span>}
            </div>
            <div className="text-[10px] leading-relaxed whitespace-pre-wrap select-text text-[#c0caf5]">
              {msg.content}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});
