import React, { useState, memo } from 'react';

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

export const FileSectionViewer: React.FC<{ content: string }> = memo(({ content }) => {
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
});
