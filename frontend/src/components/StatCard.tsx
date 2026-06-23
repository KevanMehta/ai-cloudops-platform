interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export default function StatCard({ title, value, subtitle, trend }: StatCardProps) {
  const trendColor =
    trend === 'up' ? 'text-red-400' : trend === 'down' ? 'text-emerald-400' : 'text-slate-400';

  return (
    <div className="card" data-testid="stat-card">
      <p className="text-sm font-medium text-slate-400">{title}</p>
      <p className="mt-2 text-3xl font-bold text-brand-400" data-testid="stat-value">
        {value}
      </p>
      {subtitle && (
        <p className={`mt-1 text-sm ${trend ? trendColor : 'text-slate-500'}`}>{subtitle}</p>
      )}
    </div>
  );
}
