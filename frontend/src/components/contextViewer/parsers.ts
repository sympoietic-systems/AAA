import type { ContextSection } from './types';

function getTitle(type: ContextSection['type']) {
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
