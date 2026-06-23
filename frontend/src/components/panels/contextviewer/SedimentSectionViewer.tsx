import React, { useState, memo } from 'react';

interface ParsedSedimentMemory {
  title: string;
  relTime: string;
  speaker: string;
  content: string;
  messageId?: number;
  conversationId?: string;
}

function parseSedimentContent(content: string): ParsedSedimentMemory[] {
  const regex = /^\[system\]:\s*\[Memory from "([^"]+)"\s*\|\s*([^|]+)\s*\|\s*Speaker:\s*([^|\]]+?)(?:\s*\|\s*msg:\s*(\d+))?(?:\s*\|\s*conv:\s*([^|\]]+))?\]:\s*[\r\n]+([\s\S]*?)(?=(?:^\[system\]:\s*\[Memory from ")|(?![\s\S]))/gm;
  const matches = [...content.matchAll(regex)];
  
  return matches.map(match => {
    let memoryContent = match[6].trim();
    if (memoryContent.startsWith('"') && memoryContent.endsWith('"')) {
      memoryContent = memoryContent.slice(1, -1);
    }
    return {
      title: match[1],
      relTime: match[2].trim(),
      speaker: match[3].trim(),
      messageId: match[4] ? parseInt(match[4], 10) : undefined,
      conversationId: match[5] ? match[5].trim() : undefined,
      content: memoryContent
    };
  });
}

export const SedimentSectionViewer: React.FC<{ content: string }> = memo(({ content }) => {
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
                {item.conversationId ? (
                  <a
                    href={`/nodes?c=${encodeURIComponent(item.conversationId)}${item.messageId ? `&m=${item.messageId}` : ""}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-bold text-[#60a5fa] hover:text-[#a78bfa] transition-colors truncate max-w-[190px] hover:underline"
                    title={`Sediment Fold: Open conversation in new tab`}
                  >
                    🗰 {item.title}
                  </a>
                ) : (
                  <span className="font-bold text-[#60a5fa] truncate max-w-[190px]" title={item.title}>
                    🗰 {item.title}
                  </span>
                )}
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
});
