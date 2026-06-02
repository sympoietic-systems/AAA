import React, { useState } from 'react';

interface ContextSection {
  title: string;
  type: 'system_prompt' | 'history' | 'sediment' | 'file' | 'web' | 'diffractive' | 'query' | 'other';
  content: string;
}

export function parseContextSent(contextText: string): ContextSection[] {
  if (!contextText) return [];

  const lines = contextText.split('\n');
  const messages: { index: number; role: string; contentLines: string[] }[] = [];
  let currentMsg: typeof messages[number] | null = null;
  const msgStartRegex = /^\[(\d+)\] (system|user|assistant|unknown|apparatus):(.*)$/;

  for (const line of lines) {
    const match = line.match(msgStartRegex);
    if (match) {
      if (currentMsg) {
        messages.push(currentMsg);
      }
      currentMsg = {
        index: parseInt(match[1], 10),
        role: match[2],
        contentLines: [match[3].trim()]
      };
    } else {
      if (currentMsg) {
        currentMsg.contentLines.push(line);
      }
    }
  }
  if (currentMsg) {
    messages.push(currentMsg);
  }

  const sections: ContextSection[] = [];
  let currentSectionType: ContextSection['type'] = 'system_prompt';
  let currentSectionContent: string[] = [];

  const getTitle = (type: ContextSection['type']) => {
    switch (type) {
      case 'system_prompt': return 'System Prompt & Identity';
      case 'history': return 'Conversation History';
      case 'sediment': return 'Cross-Conversation Resonance (Sediment)';
      case 'file': return 'File Sediment (File Context)';
      case 'web': return 'Exogenous Web Context';
      case 'diffractive': return 'Diffractive Interference Zone';
      case 'query': return 'Current User Query';
      default: return 'Context Data';
    }
  };

  const flushSection = () => {
    if (currentSectionContent.length > 0) {
      const text = currentSectionContent.join('\n').trim();
      if (text) {
        sections.push({
          title: getTitle(currentSectionType),
          type: currentSectionType,
          content: text
        });
      }
      currentSectionContent = [];
    }
  };

  for (const msg of messages) {
    const rawContent = msg.contentLines.join('\n').trim();
    
    if (rawContent.includes('--- BEGIN CONVERSATION HISTORY ---')) {
      flushSection();
      currentSectionType = 'history';
      continue;
    }
    if (rawContent.includes('--- END CONVERSATION HISTORY ---')) {
      flushSection();
      currentSectionType = 'other';
      continue;
    }
    
    if (rawContent.includes('--- BEGIN CROSS-CONVERSATION RESONANCE ---')) {
      flushSection();
      currentSectionType = 'sediment';
      continue;
    }
    if (rawContent.includes('--- END CROSS-CONVERSATION RESONANCE ---')) {
      flushSection();
      currentSectionType = 'other';
      continue;
    }

    if (rawContent.includes('--- BEGIN FILE SEDIMENT ---')) {
      flushSection();
      currentSectionType = 'file';
      continue;
    }
    if (rawContent.includes('--- END FILE SEDIMENT ---')) {
      flushSection();
      currentSectionType = 'other';
      continue;
    }

    if (rawContent.includes('--- BEGIN EXOGENOUS WEB CONTEXT ---')) {
      flushSection();
      currentSectionType = 'web';
      continue;
    }
    if (rawContent.includes('--- END EXOGENOUS WEB CONTEXT ---')) {
      flushSection();
      currentSectionType = 'other';
      continue;
    }

    if (rawContent.includes('<diffractive_interference_zone>')) {
      flushSection();
      currentSectionType = 'diffractive';
      const cleanContent = rawContent.replace('<diffractive_interference_zone>', '').trim();
      if (cleanContent) {
        currentSectionContent.push(`[${msg.role}]: ${cleanContent}`);
      }
      continue;
    }
    if (rawContent.includes('</diffractive_interference_zone>')) {
      const cleanContent = rawContent.replace('</diffractive_interference_zone>', '').trim();
      if (cleanContent) {
        currentSectionContent.push(`[${msg.role}]: ${cleanContent}`);
      }
      flushSection();
      currentSectionType = 'other';
      continue;
    }

    if (currentSectionType === 'system_prompt' && msg.role === 'system') {
      currentSectionContent.push(rawContent);
    } else {
      currentSectionContent.push(`[${msg.role}]: ${rawContent}`);
    }
  }
  flushSection();

  if (sections.length > 0) {
    const lastSec = sections[sections.length - 1];
    if (lastSec.type === 'other') {
      lastSec.type = 'query';
      lastSec.title = getTitle('query');
    }
  }

  return sections.filter(s => s.content.trim() !== '');
}

interface SectionColors {
  border: string;
  bg: string;
  text: string;
  badgeBg: string;
}

const SECTION_STYLES: Record<ContextSection['type'], SectionColors> = {
  system_prompt: { border: '#475569', bg: '#1e293b10', text: '#94a3b8', badgeBg: '#47556920' },
  history: { border: '#2563eb', bg: '#1d4ed808', text: '#60a5fa', badgeBg: '#2563eb20' },
  sediment: { border: '#2563eb', bg: '#1d4ed808', text: '#60a5fa', badgeBg: '#2563eb20' },
  file: { border: '#059669', bg: '#04785708', text: '#4ade80', badgeBg: '#05966920' },
  web: { border: '#7c3aed', bg: '#6d28d908', text: '#c084fc', badgeBg: '#7c3aed20' },
  diffractive: { border: '#db2777', bg: '#be185d08', text: '#f43f5e', badgeBg: '#db277720' },
  query: { border: '#d97706', bg: '#b4530908', text: '#facc15', badgeBg: '#d9770620' },
  other: { border: '#4b5563', bg: '#37415108', text: '#9ca3af', badgeBg: '#4b556320' },
};

export const ContextViewer: React.FC<{ contextText: string }> = ({ contextText }) => {
  const sections = parseContextSent(contextText);
  const [openSections, setOpenSections] = useState<Record<number, boolean>>(() => {
    // By default, expand current query if present (type === 'query')
    const initial: Record<number, boolean> = {};
    sections.forEach((s, idx) => {
      if (s.type === 'query') {
        initial[idx] = true;
      }
    });
    return initial;
  });

  const toggleSection = (idx: number) => {
    setOpenSections(prev => ({
      ...prev,
      [idx]: !prev[idx]
    }));
  };

  if (sections.length === 0) {
    return (
      <div className="pl-3 border-l border-[#2a2a2a] text-xs text-[#555] font-mono py-1">
        Empty context data.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 w-full font-mono text-[10px]">
      {sections.map((section, idx) => {
        const isOpen = !!openSections[idx];
        const style = SECTION_STYLES[section.type] || SECTION_STYLES.other;

        return (
          <div
            key={idx}
            className="border rounded transition-all duration-200"
            style={{
              borderColor: `${style.border}30`,
              backgroundColor: isOpen ? style.bg : 'transparent',
            }}
          >
            {/* Header */}
            <button
              onClick={() => toggleSection(idx)}
              className="w-full flex items-center justify-between p-2 py-1.5 hover:bg-[#1a1a24]/40 transition-colors text-left"
            >
              <div className="flex items-center gap-2">
                <span className="text-[8px] opacity-60">
                  {isOpen ? '▼' : '▶'}
                </span>
                <span
                  className="font-bold tracking-wide uppercase text-[9px]"
                  style={{ color: style.text }}
                >
                  {section.title}
                </span>
              </div>
              <span
                className="text-[8px] uppercase tracking-wider px-1.5 py-0.5 rounded border"
                style={{
                  color: style.text,
                  backgroundColor: style.badgeBg,
                  borderColor: `${style.border}45`,
                }}
              >
                {section.type}
              </span>
            </button>

            {/* Content Accordion */}
            {isOpen && (
              <div
                className="p-3 pt-1.5 border-t text-[11px] text-[#c0caf5] leading-relaxed whitespace-pre-wrap bg-[#050507]/90 font-mono overflow-x-auto select-text"
                style={{
                  borderColor: `${style.border}20`,
                }}
              >
                {section.content}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
