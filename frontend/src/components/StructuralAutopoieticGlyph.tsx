import React, { useState } from 'react';

// Define the 16 dimensions grouped into 4 cybernetic sectors with explanations
export const SECTORS = [
  {
    name: "Behavioral Dynamics",
    color: "#a78bfa",
    dimensions: [
      { index: 0, label: "Homeostatic", explanation: "Stabilizing feedback. Maintains system consistency, recovering from perturbations." },
      { index: 1, label: "Amplifying", explanation: "Runaway feedback. Cascading expansion, growth, and positive feedback loops." },
      { index: 2, label: "Cyclic", explanation: "Recursive loops. Periodic oscillations and repeating rhythms of dialogue topics." },
      { index: 3, label: "Bifurcated", explanation: "Phase state bifurcation. Sudden transitions and threshold-triggered changes." }
    ]
  },
  {
    name: "Structural Topology",
    color: "#60a5fa",
    dimensions: [
      { index: 4, label: "Decentralized", explanation: "Mesh structure. Non-hierarchical distribution of control across topics." },
      { index: 5, label: "Rhizomatic", explanation: "Network complexity. Multiple redundant paths and horizontal connections." },
      { index: 6, label: "Boundary Permeability", explanation: "Environmental coupling. Ingestion and openness to outside files/inputs." },
      { index: 7, label: "Recursion Depth", explanation: "Depth of nesting. Embedding level of internal meta-reasoning loops." }
    ]
  },
  {
    name: "Informational Flow",
    color: "#34d399",
    dimensions: [
      { index: 8, label: "Variety Filtering", explanation: "Cybernetic control. Selecting clean relevance out of high cognitive variety." },
      { index: 9, label: "Negentropic Complexity", explanation: "Order creation. Generating structured coherence from semantic noise." },
      { index: 10, label: "Temporal Latency", explanation: "Response delay. Time lag and processing weight of responses." },
      { index: 11, label: "Attractor Depth", explanation: "Conceptual confinement. Locking into stable focus zones or cognitive basins." }
    ]
  },
  {
    name: "Relational Coupling",
    color: "#fbbf24",
    dimensions: [
      { index: 12, label: "Symbiotic", explanation: "Structural coupling. Reciprocal co-evolution between human and agent systems." },
      { index: 13, label: "Nomadic", explanation: "Deterritorialization. Thematic drifts, leaps, and exploratory migrations." },
      { index: 14, label: "Conversational", explanation: "Interlocutor co-orientation. Direct conversational grounding and dialogic alignment." },
      { index: 15, label: "Substrate Materiality", explanation: "Hardware reflexivity. System awareness of hosts, memory limits, and runs." }
    ]
  }
];

export const DIMENSION_NAMES = SECTORS.flatMap(s => s.dimensions).map(d => d.label);

interface GlyphProps {
  signature: number[];
  previousSignature?: number[] | null;
  isStagnant: boolean;
}

export const StructuralAutopoieticGlyph: React.FC<GlyphProps> = ({
  signature,
  previousSignature,
  isStagnant
}) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const SIZE = 140;
  const CENTER = SIZE / 2;
  const MAX_RADIUS = 60;

  const getCoordinates = (index: number, value: number) => {
    const angle = (index * 2 * Math.PI) / 16 - Math.PI / 2;
    const r = value * MAX_RADIUS;
    return {
      x: CENTER + r * Math.cos(angle),
      y: CENTER + r * Math.sin(angle)
    };
  };

  const generatePathData = (sig: number[]) => {
    if (!sig || sig.length < 16) return '';
    const points = sig.slice(0, 16).map((val, i) => {
      const { x, y } = getCoordinates(i, val);
      return `${x},${y}`;
    });
    return `M ${points.join(' L ')} Z`;
  };

  const currentPath = generatePathData(signature);
  const ghostPath = previousSignature ? generatePathData(previousSignature) : null;

  const activeDimension = hoveredIndex !== null
    ? SECTORS.flatMap(s => s.dimensions).find(d => d.index === hoveredIndex)
    : null;

  const activeSector = hoveredIndex !== null
    ? SECTORS.find(s => s.dimensions.some(d => d.index === hoveredIndex))
    : null;

  return (
    <div className="flex flex-col sm:flex-row items-center gap-6 p-4 bg-[#0a0a0c]/80 border border-[#1e1e24] rounded-xl max-w-full">
      {/* SVG Radial Glyph */}
      <div className="relative w-[140px] h-[140px] flex-shrink-0">
        <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="w-full h-full overflow-visible">
          {/* Concentric Reference Rings */}
          {[0.33, 0.66, 1.0].map((level, i) => (
            <circle
              key={i}
              cx={CENTER}
              cy={CENTER}
              r={level * MAX_RADIUS}
              fill="none"
              stroke="#1e293b"
              strokeDasharray="2,2"
              className={level === 1.0 && !isStagnant ? "animate-[pulse_4s_infinite]" : ""}
            />
          ))}

          {/* 16 Spoke Lines */}
          {signature.map((_, i) => {
            const { x, y } = getCoordinates(i, 1.0);
            const sectorColor = SECTORS.find(s => s.dimensions.some(d => d.index === i))?.color || '#334155';
            const isHovered = hoveredIndex === i;
            return (
              <line
                key={i}
                x1={CENTER}
                y1={CENTER}
                x2={x}
                y2={y}
                stroke={isHovered ? sectorColor : '#161b22'}
                strokeWidth={isHovered ? 1.5 : 1}
                className="transition-colors duration-200"
              />
            );
          })}

          {/* Ghost Drift Polygon */}
          {ghostPath && (
            <path
              d={ghostPath}
              fill="none"
              stroke="#334155"
              strokeWidth={1}
              strokeDasharray="3,3"
              opacity={0.35}
            />
          )}

          {/* Single-Color Core Polygon */}
          {currentPath && (
            <path
              d={currentPath}
              fill="url(#glyph-gradient)"
              stroke={isStagnant ? "#f43f5e" : "#10b981"}
              strokeWidth={1.5}
              className={`transition-all duration-300 ${
                !isStagnant
                  ? 'animate-[pulse_3s_ease-in-out_infinite] origin-center'
                  : 'filter drop-shadow-[0_0_3px_rgba(244,63,94,0.5)]'
              }`}
            />
          )}

          {/* Hover Hotspots */}
          {signature.map((val, i) => {
            const { x, y } = getCoordinates(i, val);
            const sectorColor = SECTORS.find(s => s.dimensions.some(d => d.index === i))?.color || '#10b981';
            const isHovered = hoveredIndex === i;
            return (
              <g key={i}>
                <circle
                  cx={x} cy={y} r={8}
                  fill="transparent"
                  className="cursor-pointer"
                  onMouseEnter={() => setHoveredIndex(i)}
                  onMouseLeave={() => setHoveredIndex(null)}
                />
                {isHovered && (
                  <circle
                    cx={x} cy={y} r={4}
                    fill={sectorColor}
                    className="pointer-events-none filter drop-shadow-[0_0_4px_currentColor]"
                  />
                )}
              </g>
            );
          })}

          {/* Gradient Definition */}
          <defs>
            <radialGradient id="glyph-gradient" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor={isStagnant ? "#991b1b" : "#065f46"} stopOpacity={0.15} />
              <stop offset="100%" stopColor={isStagnant ? "#f43f5e" : "#10b981"} stopOpacity={0.35} />
            </radialGradient>
          </defs>
        </svg>

        {/* Floating Value Tooltip */}
        {activeDimension && activeSector && (
          <div
            className="absolute -top-7 left-1/2 -translate-x-1/2 px-2 py-0.5 text-[9px] font-mono rounded border bg-[#0d0d12] shadow-xl pointer-events-none whitespace-nowrap z-10"
            style={{ borderColor: activeSector.color, color: activeSector.color }}
          >
            {activeDimension.label}: {signature[hoveredIndex!].toFixed(2)}
          </div>
        )}
      </div>

      {/* Legend + Explanation */}
      <div className="flex flex-col gap-2 flex-1 min-w-[200px] w-full">
        <div className="text-[9px] font-bold tracking-wider uppercase text-slate-500 font-mono flex items-center justify-between">
          <span>Structural Coordinates</span>
          {isStagnant && (
            <span className="text-red-400 animate-pulse text-[8px] border border-red-500/30 px-1 rounded bg-red-950/20">
              Stagnation Warn
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[10px] font-mono">
          {SECTORS.map((sector) => (
            <div key={sector.name} className="flex flex-col gap-1 col-span-1 border-t border-[#1a1a24] pt-1.5">
              <span className="text-[8px] font-semibold text-slate-600 truncate uppercase tracking-tight mb-0.5">
                {sector.name.split(" ")[0]}
              </span>
              {sector.dimensions.map((dim) => {
                const isHovered = hoveredIndex === dim.index;
                const value = signature[dim.index];
                return (
                  <div
                    key={dim.index}
                    onMouseEnter={() => setHoveredIndex(dim.index)}
                    onMouseLeave={() => setHoveredIndex(null)}
                    className="flex items-center justify-between cursor-help py-0.5 px-1 rounded transition-colors duration-150"
                    style={{
                      backgroundColor: isHovered ? `${sector.color}15` : 'transparent',
                      color: isHovered ? sector.color : '#94a3b8'
                    }}
                  >
                    <span className="truncate max-w-[85px] text-[9px]">{dim.label}</span>
                    <span className="font-mono text-[9px] font-bold opacity-80">
                      {value != null ? value.toFixed(2) : '0.00'}
                    </span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* Explanatory Footnote Panel */}
        <div className="mt-1.5 p-2 bg-[#050507] border border-[#141418] rounded text-[9px] font-mono leading-relaxed min-h-[40px] flex items-center">
          {activeDimension && activeSector ? (
            <div>
              <span className="font-bold mr-1" style={{ color: activeSector.color }}>
                {activeDimension.label}:
              </span>
              <span className="text-slate-400">{activeDimension.explanation}</span>
            </div>
          ) : (
            <span className="text-slate-600 italic">
              Hover a dimension to view its explanation.
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
