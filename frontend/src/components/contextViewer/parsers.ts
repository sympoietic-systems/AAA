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

  // Normalize line endings: convert \r\n → \n, strip stray \r for robust parsing
  const normalized = contextText.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const lines = normalized.split('\n');
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

    // Handle diffractive interference zone — opening and closing tags may be in the same message
    const hasOpening = rawContent.includes('<diffractive_interference_zone>');
    const hasClosing = rawContent.includes('</diffractive_interference_zone>');

    if (hasOpening) {
      flushSection();
      currentSectionType = 'diffractive';
      // Strip both tags from the content
      let cleanContent = rawContent
        .replace('<diffractive_interference_zone>', '')
        .replace('</diffractive_interference_zone>', '')
        .trim();
      if (cleanContent) {
        currentSectionContent.push(cleanContent);
      }
      // If closing tag was in the same message, flush immediately
      if (hasClosing) {
        flushSection();
        currentSectionType = 'other';
      }
      continue;
    }

    // Handle closing tag in a separate message (legacy path)
    if (hasClosing) {
      const cleanContent = rawContent.replace('</diffractive_interference_zone>', '').trim();
      if (cleanContent) {
        currentSectionContent.push(cleanContent);
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

  // ── Post-processing: reclassify sections that contain mismatched content ──

  // If a 'diffractive' section contains system-prompt block markers, it was misclassified
  for (const sec of sections) {
    if (sec.type === 'diffractive' || sec.type === 'other') {
      const hasSystemBlocks =
        sec.content.includes('--- BEGIN SKILLS') ||
        sec.content.includes('--- BEGIN BELIEFS') ||
        sec.content.includes('--- BEGIN DIRECTIVE') ||
        sec.content.includes('--- BEGIN PROCEDURAL SEDIMENT ---');
      const hasDiffractiveMarkers =
        sec.content.includes('[Source:') ||
        sec.content.includes('[URGENT ATTENTION DIRECTIVE]') ||
        sec.content.includes('<diffractive_interference_zone>');

      if (hasSystemBlocks && !hasDiffractiveMarkers) {
        // This is system prompt content, misclassified
        sec.type = 'system_prompt';
        sec.title = getTitle('system_prompt');
      }
    }
  }

  if (sections.length > 0) {
    const lastSec = sections[sections.length - 1];
    if (lastSec.type === 'other') {
      lastSec.type = 'query';
      lastSec.title = getTitle('query');
    }
  }

  const filtered = sections.filter(s => s.content.trim() !== '');

  // Debug: log section breakdown to help diagnose classification issues
  if (process.env.NODE_ENV !== 'production') {
    console.debug(
      '[ContextViewer] Parsed sections:',
      filtered.map(s => ({
        type: s.type,
        title: s.title,
        contentLen: s.content.length,
        preview: s.content.slice(0, 120),
        hasSkills: s.content.includes('--- BEGIN SKILLS'),
        hasBeliefs: s.content.includes('--- BEGIN BELIEFS'),
        hasDiffractive: s.content.includes('[Source:') || s.content.includes('<diffractive'),
      }))
    );
  }

  return filtered;
}
