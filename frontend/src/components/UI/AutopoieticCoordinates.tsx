import React from 'react';
import telemetrySchemas from '../../config/telemetry_schemas.json';

const { SIGNATURE_DIMENSIONS_16 } = telemetrySchemas;

export interface SectorDefinition {
  name: string;
  color: string;
  dimensions: Array<{ index: number; label: string; explanation: string }>;
}

export const SECTORS: SectorDefinition[] = [
  {
    name: 'Behavioral Dynamics',
    color: '#38bdf8', // Light blue
    dimensions: SIGNATURE_DIMENSIONS_16.slice(0, 4).map((d, i) => ({ index: i, label: d.label, explanation: d.desc }))
  },
  {
    name: 'Structural Topology',
    color: '#a78bfa', // Purple
    dimensions: SIGNATURE_DIMENSIONS_16.slice(4, 8).map((d, i) => ({ index: i + 4, label: d.label, explanation: d.desc }))
  },
  {
    name: 'Informational Flow',
    color: '#34d399', // Emerald
    dimensions: SIGNATURE_DIMENSIONS_16.slice(8, 12).map((d, i) => ({ index: i + 8, label: d.label, explanation: d.desc }))
  },
  {
    name: 'Relational Coupling',
    color: '#fb7185', // Rose
    dimensions: SIGNATURE_DIMENSIONS_16.slice(12, 16).map((d, i) => ({ index: i + 12, label: d.label, explanation: d.desc }))
  }
];

interface AutopoieticCoordinatesProps {
  signature: number[];
  hoveredIndex: number | null;
  onHoverChange: (index: number | null) => void;
  isStagnant?: boolean;
}

export const AutopoieticCoordinates: React.FC<AutopoieticCoordinatesProps> = ({
  signature,
  hoveredIndex,
  onHoverChange,
  isStagnant = false
}) => {
  return (
    <div className="flex flex-col gap-2 flex-1 min-w-[200px] w-full">
      <div className="text-[9px] font-bold tracking-wider uppercase text-slate-500 font-mono flex items-center justify-between">
        <span>Autopoietic Coordinates</span>
        {isStagnant && (
          <span className="text-red-400 animate-pulse text-[8px] border border-red-500/30 px-1 rounded bg-red-950/20">
            Stagnation Warn
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-2 xl:grid-cols-4 gap-x-2 sm:gap-x-3 gap-y-1.5 text-[8.5px] font-mono w-full">
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
                  onMouseEnter={() => onHoverChange(dim.index)}
                  onMouseLeave={() => onHoverChange(null)}
                  className="flex items-start justify-between cursor-help py-0.5 px-0.5 rounded transition-colors duration-150"
                  style={{
                    backgroundColor: isHovered ? `${sector.color}15` : 'transparent',
                    color: isHovered ? sector.color : '#94a3b8'
                  }}
                >
                  <span className="text-[7.5px] sm:text-[8px] leading-tight pr-1" title={dim.label}>{dim.label}</span>
                  <span className="font-mono text-[7.5px] sm:text-[8px] font-bold opacity-80 mt-[1px]">
                    {value != null ? value.toFixed(1) : '0.0'}
                  </span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};
