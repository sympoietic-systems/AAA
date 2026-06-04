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

interface ParsedSedimentMemory {
  title: string;
  relTime: string;
  speaker: string;
  content: string;
}

function parseSedimentContent(content: string): ParsedSedimentMemory[] {
  const regex = /^\[system\]:\s*\[Memory from "([^"]+)"\s*\|\s*([^|]+)\s*\|\s*Speaker:\s*([^\]]+)\]:\s*[\r\n]+([\s\S]*?)(?=(?:^\[system\]:\s*\[Memory from ")|(?![\s\S]))/gm;
  const matches = [...content.matchAll(regex)];
  
  return matches.map(match => {
    let memoryContent = match[4].trim();
    if (memoryContent.startsWith('"') && memoryContent.endsWith('"')) {
      memoryContent = memoryContent.slice(1, -1);
    }
    return {
      title: match[1],
      relTime: match[2].trim(),
      speaker: match[3].trim(),
      content: memoryContent
    };
  });
}

interface ParsedFileManifest {
  isNew: boolean;
  fileName: string;
  fileType: string;
  tokens: string;
  chunks: string;
  summary: string;
}

interface ParsedFileChunk {
  fileName: string;
  chunkIndex: string;
  similarity: string | undefined;
  content: string;
}

interface ParsedFileSediment {
  manifests: ParsedFileManifest[];
  chunks: ParsedFileChunk[];
}

function parseFileSedimentContent(content: string): ParsedFileSediment {
  const manifests: ParsedFileManifest[] = [];
  const chunks: ParsedFileChunk[] = [];
  
  const manifestMatch = content.match(/\[File Manifest - Co-Participant Sediment\]\s*([\s\S]*?)(?=\[system\]:\s*\[|\n\n\[system\]:\s*\[|$)/);
  if (manifestMatch) {
    const manifestLines = manifestMatch[1].split('\n');
    for (const line of manifestLines) {
      const cleanLine = line.trim();
      if (cleanLine.startsWith('-')) {
        const isNew = cleanLine.includes('[new]');
        const noNew = cleanLine.replace(/-\s*(\[new\])?\s*/, '');
        const fileMatch = noNew.match(/^(.+?)\s*\(([^,]+),\s*([^ ]+)\s*tokens,\s*([^ ]+)\s*chunks\)\s*-\s*Summary:\s*([\s\S]*)$/);
        if (fileMatch) {
          manifests.push({
            isNew,
            fileName: fileMatch[1],
            fileType: fileMatch[2],
            tokens: fileMatch[3],
            chunks: fileMatch[4],
            summary: fileMatch[5].trim()
          });
        }
      }
    }
  }
  
  const chunkRegex = /(?:^|\r?\n)\[system\]:\s*\[([^\r\n\]]+?)\s+chunk\s+#(\d+)(?:\s+sim=([^\]]+))?\]\s*[\r\n]+([\s\S]*?)(?=(?:\r?\n\[system\]:\s*\[[^\r\n\]]+?chunk\s+#\d+)|$)/g;
  const matches = [...content.matchAll(chunkRegex)];
  for (const match of matches) {
    chunks.push({
      fileName: match[1],
      chunkIndex: match[2],
      similarity: match[3],
      content: match[4].trim()
    });
  }
  
  return { manifests, chunks };
}

const HistorySectionViewer: React.FC<{ content: string; style: SectionColors }> = ({ content, style }) => {
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
            className="flex flex-col gap-1 p-2 rounded border bg-[#09090e]/60 hover:bg-[#0e0e16]/80 transition-colors"
            style={{ borderColor: `${style.border}15` }}
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
};

const SedimentSectionViewer: React.FC<{ content: string }> = ({ content }) => {
  const parsed = parseSedimentContent(content);
  const [expandedFile, setExpandedFile] = useState<string | null>(null);
  const [loadedFiles, setLoadedFiles] = useState<Record<string, {
    loading: boolean;
    error?: string;
    summary?: string;
    chunks?: { chunk_index: number; chunk_text: string; token_count: number }[];
  }>>({});

  const dialogues = parsed.filter(item => !item.content.includes("Processed file: **"));
  const fileTraces = parsed.filter(item => item.content.includes("Processed file: **"));

  const [activeTab, setActiveTab] = useState<'dialogue' | 'files'>(
    fileTraces.length > 0 && dialogues.length === 0 ? 'files' : 'dialogue'
  );

  const handleLoadFile = async (fileName: string) => {
    if (loadedFiles[fileName]?.summary || loadedFiles[fileName]?.loading) return;
    setLoadedFiles(prev => ({ ...prev, [fileName]: { loading: true } }));
    try {
      const res = await fetch(`/api/files/by-name?file_name=${encodeURIComponent(fileName)}`);
      if (!res.ok) {
        throw new Error(`Failed to load file: ${res.statusText}`);
      }
      const data = await res.json();
      setLoadedFiles(prev => ({
        ...prev,
        [fileName]: {
          loading: false,
          summary: data.summary || "No summary available in DB.",
          chunks: data.chunks || []
        }
      }));
    } catch (err: any) {
      setLoadedFiles(prev => ({
        ...prev,
        [fileName]: {
          loading: false,
          error: err.message || "Failed to load file metadata."
        }
      }));
    }
  };

  if (parsed.length === 0) {
    return <div className="whitespace-pre-wrap select-text">{content}</div>;
  }

  return (
    <div className="flex flex-col gap-2.5">
      {/* Segmented Tab Controls */}
      <div className="flex border-b border-[#2563eb]/20 pb-1 gap-2 text-[10px]">
        {dialogues.length > 0 && (
          <button
            onClick={() => setActiveTab('dialogue')}
            className={`px-2 py-0.5 rounded transition-all ${
              activeTab === 'dialogue'
                ? 'bg-[#2563eb]/20 text-[#60a5fa] font-bold border border-[#2563eb]/30'
                : 'text-[#94a3b8] hover:text-[#c0caf5]'
            }`}
          >
            Dialogues ({dialogues.length})
          </button>
        )}
        {fileTraces.length > 0 && (
          <button
            onClick={() => setActiveTab('files')}
            className={`px-2 py-0.5 rounded transition-all ${
              activeTab === 'files'
                ? 'bg-[#2563eb]/20 text-[#60a5fa] font-bold border border-[#2563eb]/30'
                : 'text-[#94a3b8] hover:text-[#c0caf5]'
            }`}
          >
            File Traces ({fileTraces.length})
          </button>
        )}
      </div>

      <div className="flex flex-col gap-2 max-h-[350px] overflow-y-auto pr-1">
        {activeTab === 'dialogue' ? (
          dialogues.map((item, i) => (
            <div
              key={i}
              className="flex flex-col gap-1.5 p-2 rounded border bg-[#050507]/90 hover:bg-[#0b0b12]/80 transition-colors border-[#2563eb]/15"
            >
              <div className="flex flex-wrap items-center justify-between gap-1.5 text-[8px] border-b border-[#2563eb]/10 pb-1">
                <span className="font-bold text-[#60a5fa] truncate max-w-[190px]" title={item.title}>
                  🗰 {item.title}
                </span>
                <div className="flex items-center gap-1">
                  <span className="text-[#94a3b8] opacity-75">{item.relTime}</span>
                  <span className="text-[#94a3b8]/40">•</span>
                  <span className="text-[#a78bfa] font-semibold">{item.speaker}</span>
                </div>
              </div>
              <div className="text-[10px] leading-relaxed italic text-[#c0caf5] select-text pl-1.5 border-l border-[#60a5fa]/30">
                "{item.content}"
              </div>
            </div>
          ))
        ) : (
          fileTraces.map((item, i) => {
            const match = item.content.match(/Processed file:\s*\*\*([^*]+)\*\*\s*\(([^)]+)\)/);
            const fileName = match ? match[1] : 'Unknown File';
            const fileType = match ? match[2] : 'unknown';
            const isExpanded = expandedFile === fileName;
            const fileData = loadedFiles[fileName];

            return (
              <div
                key={i}
                className="flex flex-col gap-2 p-2.5 rounded border bg-[#08080f]/90 border-[#2563eb]/20 hover:border-[#2563eb]/45 transition-colors"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 text-[8px] border-b border-[#2563eb]/10 pb-1.5">
                  <div className="flex items-center gap-1.5 truncate max-w-[190px]">
                    <span className="text-xs">📄</span>
                    <span className="font-bold text-[#60a5fa] truncate" title={fileName}>
                      {fileName}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="px-1.5 py-0.5 text-[7px] font-bold rounded bg-[#2563eb]/15 text-[#60a5fa] border border-[#2563eb]/25 uppercase">
                      {fileType}
                    </span>
                    <span className="text-[#94a3b8] opacity-75">{item.relTime}</span>
                  </div>
                </div>

                <div className="text-[10px] leading-normal text-[#94a3b8] italic px-1 bg-[#10101b]/60 rounded py-1 border border-[#2563eb]/5">
                  "{item.content}"
                </div>

                <div className="flex flex-col gap-1.5 mt-1">
                  <div className="flex items-center justify-between text-[7px] text-[#64748b]">
                    <span>ℹ️ Only this trace notification is added to context.</span>
                    <button
                      onClick={() => {
                        if (isExpanded) {
                          setExpandedFile(null);
                        } else {
                          setExpandedFile(fileName);
                          handleLoadFile(fileName);
                        }
                      }}
                      className="px-2 py-0.5 rounded font-semibold bg-[#2563eb]/10 hover:bg-[#2563eb]/25 text-[#60a5fa] border border-[#2563eb]/20 transition-all"
                    >
                      {isExpanded ? 'Collapse Details' : 'Load Summary & Chunks'}
                    </button>
                  </div>

                  {isExpanded && (
                    <div className="flex flex-col gap-2 mt-1.5 pt-2 border-t border-[#2563eb]/10 text-[9px]">
                      {fileData?.loading && (
                        <div className="text-[#94a3b8] animate-pulse py-1">
                          ⚡ Connecting to perception repository, retrieving file indexes...
                        </div>
                      )}
                      {fileData?.error && (
                        <div className="text-red-400 bg-red-950/20 border border-red-900/30 p-1.5 rounded">
                          ❌ {fileData.error}
                        </div>
                      )}
                      {fileData && !fileData.loading && !fileData.error && (
                        <>
                          {/* File Summary block */}
                          <div className="flex flex-col gap-1 bg-[#10101d]/80 p-2 rounded border border-[#2563eb]/10">
                            <span className="font-bold text-[#60a5fa] text-[8px] uppercase tracking-wider">
                              File Summary (Database)
                            </span>
                            <p className="text-[#c0caf5] whitespace-pre-wrap select-text leading-relaxed">
                              {fileData.summary}
                            </p>
                          </div>

                          {/* File Chunks block */}
                          <div className="flex flex-col gap-1">
                            <span className="font-bold text-[#a78bfa] text-[8px] uppercase tracking-wider">
                              Ingested Chunks ({fileData.chunks?.length || 0})
                            </span>
                            {fileData.chunks && fileData.chunks.length > 0 ? (
                              <div className="flex flex-col gap-1.5 max-h-[150px] overflow-y-auto pr-1">
                                {fileData.chunks.map((ch, idx) => (
                                  <div
                                    key={idx}
                                    className="p-1.5 rounded bg-[#030305] border border-[#a78bfa]/10 hover:border-[#a78bfa]/25 text-[8px]"
                                  >
                                    <div className="flex justify-between text-[#94a3b8] border-b border-[#a78bfa]/5 pb-0.5 mb-1 font-mono text-[7px]">
                                      <span>Chunk #{ch.chunk_index}</span>
                                      <span>{ch.token_count} tokens</span>
                                    </div>
                                    <div className="text-[#94a3b8] font-mono whitespace-pre-wrap leading-normal select-text">
                                      {ch.chunk_text}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="text-[#94a3b8] italic">No chunks found in sediment.</div>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

const FileSectionViewer: React.FC<{ content: string }> = ({ content }) => {
  const { manifests, chunks } = parseFileSedimentContent(content);

  const fileTabs: { id: string; label: string; count: number }[] = [];
  if (manifests.length > 0) {
    fileTabs.push({ id: 'files', label: 'Files & Summaries', count: manifests.length });
  }
  if (chunks.length > 0) {
    fileTabs.push({ id: 'chunks', label: 'Retrieved Chunks', count: chunks.length });
  }

  const [activeFileTab, setActiveFileTab] = useState(fileTabs[0]?.id || 'files');

  if (fileTabs.length === 0) {
    return <div className="whitespace-pre-wrap select-text">{content}</div>;
  }

  // Group chunks by fileName
  const chunksByFile = chunks.reduce((acc, chunk) => {
    if (!acc[chunk.fileName]) {
      acc[chunk.fileName] = [];
    }
    acc[chunk.fileName].push(chunk);
    return acc;
  }, {} as Record<string, typeof chunks>);

  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex border-b border-[#2d2d3d] pb-1 gap-1.5">
        {fileTabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveFileTab(tab.id)}
            className={`px-2 py-0.5 text-[8.5px] rounded font-bold tracking-wide uppercase transition-all duration-200 border ${
              activeFileTab === tab.id
                ? 'bg-[#0f1f18] text-[#4ade80] border-[#4ade80]/30'
                : 'text-[#94a3b8]/60 border-transparent hover:text-[#94a3b8] hover:bg-[#1a1a24]/30'
            }`}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-2 max-h-[350px] overflow-y-auto pr-1">
        {activeFileTab === 'files' && (
          <div className="flex flex-col gap-2">
            {manifests.map((file, i) => (
              <div
                key={i}
                className="flex flex-col gap-1.5 p-2 rounded border bg-[#050507]/90 border-[#059669]/15"
              >
                <div className="flex flex-wrap items-center justify-between gap-1.5 text-[8px]">
                  <div className="flex items-center gap-1.5">
                    {file.isNew && (
                      <span className="text-[6.5px] text-[#4ade80] bg-[#4ade80]/15 px-1 rounded uppercase font-bold tracking-wide border border-[#4ade80]/30 animate-pulse">
                        New
                      </span>
                    )}
                    <span className="font-bold text-[#4ade80] truncate max-w-[190px]">
                      🖹 {file.fileName}
                    </span>
                  </div>
                  <span className="text-[#94a3b8] opacity-75">
                    {file.fileType.toUpperCase()} • {file.tokens} tokens • {file.chunks} chunks
                  </span>
                </div>
                <div className="text-[9.5px] leading-relaxed text-[#c0caf5] pl-2 border-l border-[#059669]/30">
                  <span className="font-semibold text-[#a3e635] text-[8.5px]">Summary: </span>
                  {file.summary}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeFileTab === 'chunks' && (
          <div className="flex flex-col gap-3.5">
            {Object.entries(chunksByFile).map(([fileName, fileChunks], idx) => (
              <div key={idx} className="flex flex-col gap-2 p-2.5 rounded border bg-[#050c08]/50 border-[#059669]/20">
                <div className="flex items-center justify-between border-b border-[#059669]/15 pb-1.5 mb-1 font-mono">
                  <span className="font-bold text-[#4ade80] truncate max-w-[240px]">
                    📄 {fileName}
                  </span>
                  <span className="text-[7.5px] text-[#94a3b8] bg-[#059669]/10 px-1.5 py-0.5 rounded border border-[#059669]/15 font-semibold uppercase">
                    {fileChunks.length} {fileChunks.length === 1 ? 'chunk' : 'chunks'}
                  </span>
                </div>
                <div className="flex flex-col gap-2">
                  {fileChunks.map((chunk, chunkIdx) => (
                    <div
                      key={chunkIdx}
                      className="flex flex-col gap-1.5 p-2 rounded border bg-[#050507]/90 border-[#059669]/10 hover:border-[#059669]/25 transition-all"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-1.5 text-[8px] border-b border-[#059669]/5 pb-1">
                        <span className="text-[#a3e635] font-semibold">
                          Chunk #{chunk.chunkIndex}
                        </span>
                        {chunk.similarity && (
                          <span className="text-[#a3e635] font-mono text-[7px] bg-[#059669]/5 px-1 rounded border border-[#059669]/15">
                            sim={chunk.similarity}
                          </span>
                        )}
                      </div>
                      <div className="text-[9.5px] leading-relaxed font-mono whitespace-pre-wrap select-text text-[#c0caf5] bg-[#020203] p-1.5 rounded border border-[#1a1a24] overflow-x-auto max-h-[250px] overflow-y-auto">
                        {chunk.content}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

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
                className="p-3 pt-1.5 border-t text-[11px] text-[#c0caf5] leading-relaxed bg-[#050507]/90 font-mono overflow-x-auto select-text"
                style={{
                  borderColor: `${style.border}20`,
                }}
              >
                {section.type === 'history' ? (
                  <HistorySectionViewer content={section.content} style={style} />
                ) : section.type === 'sediment' ? (
                  <SedimentSectionViewer content={section.content} />
                ) : section.type === 'file' ? (
                  <FileSectionViewer content={section.content} />
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
