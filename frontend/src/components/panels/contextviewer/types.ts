export interface ContextSection {
  title: string;
  type: 'system_prompt' | 'history' | 'sediment' | 'file' | 'web' | 'diffractive' | 'query' | 'other';
  content: string;
}

export interface SectionColors {
  accent: string;
}

export const SECTION_STYLES: Record<ContextSection['type'], SectionColors> = {
  system_prompt: { accent: '#475569' },
  history: { accent: '#60a5fa' },
  sediment: { accent: '#60a5fa' },
  file: { accent: '#4ade80' },
  web: { accent: '#c084fc' },
  diffractive: { accent: '#f43f5e' },
  query: { accent: '#facc15' },
  other: { accent: '#4b5563' },
};
