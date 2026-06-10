import React, { useState } from 'react';
import { SECTION_STYLES } from './types';
import { parseContextSent } from './parsers';
import { HistorySectionViewer } from './HistorySectionViewer';
import { SedimentSectionViewer } from './SedimentSectionViewer';
import { FileSectionViewer } from './FileSectionViewer';
import { SystemPromptViewer } from './SystemPromptViewer';
import { DiffractiveZoneViewer } from './DiffractiveZoneViewer';

export const ContextViewer: React.FC<{ contextText: string }> = ({ contextText }) => {
  const sections = parseContextSent(contextText);
  const [openSections, setOpenSections] = useState<Record<number, boolean>>(() => {
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
            className="border border-[#222] rounded transition-all duration-200 overflow-hidden"
            style={{
              borderLeft: `2px solid ${style.accent}`,
              backgroundColor: isOpen ? '#090909' : 'transparent',
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
                <span className="font-bold tracking-wide uppercase text-[9px] text-[#aaa]">
                  {section.title}
                </span>
              </div>
              <span
                className="text-[8px] uppercase tracking-wider px-1.5 py-0.5 rounded border font-bold"
                style={{
                  color: style.accent,
                  backgroundColor: '#141414',
                  borderColor: `${style.accent}33`,
                }}
              >
                {section.type}
              </span>
            </button>

            {/* Content Accordion */}
            {isOpen && (
              <div className="p-3 pt-1.5 border-t border-[#1a1a1a] text-[11px] text-[#c0caf5] leading-relaxed bg-[#050507]/90 font-mono overflow-x-auto select-text">
                {section.type === 'history' ? (
                  <HistorySectionViewer content={section.content} style={style} />
                ) : section.type === 'sediment' ? (
                  <SedimentSectionViewer content={section.content} />
                ) : section.type === 'file' ? (
                  <FileSectionViewer content={section.content} />
                ) : section.type === 'system_prompt' ? (
                  <SystemPromptViewer content={section.content} />
                ) : section.type === 'diffractive' ? (
                  <DiffractiveZoneViewer content={section.content} />
                ) : (
                  <div className="whitespace-pre-wrap">{section.content}</div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
