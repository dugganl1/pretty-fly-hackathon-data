import type { ReactNode } from 'react';

interface ObservationCardProps {
  number: number;
  title: string;
  headline: string;
  commentary: string;
  recommendation: string;
  chart: ReactNode;
}

export default function ObservationCard({
  number,
  title,
  headline,
  commentary,
  recommendation,
  chart,
}: ObservationCardProps) {
  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-0">
        {/* Chart side */}
        <div className="p-6 border-b lg:border-b-0 lg:border-r border-border min-h-[300px] flex items-center justify-center">
          {chart}
        </div>
        {/* Text side */}
        <div className="p-6 flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <span className="flex-shrink-0 w-7 h-7 rounded-full bg-accent/20 text-accent text-xs font-bold flex items-center justify-center">
              {number}
            </span>
            <h3 className="text-lg font-semibold text-white">{title}</h3>
          </div>
          <p className="text-2xl font-bold text-white tracking-tight">{headline}</p>
          <p className="text-sm text-neutral-400 leading-relaxed">{commentary}</p>
          <div className="mt-auto pt-3 border-t border-border">
            <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium mb-1">
              What we'd do
            </p>
            <p className="text-sm text-accent">{recommendation}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
