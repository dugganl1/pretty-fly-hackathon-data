interface MetricCardProps {
  label: string;
  value: string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
}

export default function MetricCard({ label, value, subtitle, trend, trendValue }: MetricCardProps) {
  return (
    <div className="bg-surface border border-border rounded-lg p-5">
      <p className="text-xs text-neutral-500 font-medium uppercase tracking-wider mb-1">
        {label}
      </p>
      <p className="text-2xl font-bold text-white tracking-tight">{value}</p>
      {(subtitle || trendValue) && (
        <p className="text-xs mt-1.5">
          {trendValue && (
            <span
              className={
                trend === 'up'
                  ? 'text-positive'
                  : trend === 'down'
                  ? 'text-negative'
                  : 'text-neutral-500'
              }
            >
              {trendValue}
            </span>
          )}
          {subtitle && (
            <span className="text-neutral-500">{trendValue ? ' · ' : ''}{subtitle}</span>
          )}
        </p>
      )}
    </div>
  );
}
