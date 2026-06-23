import { useEffect, useState } from 'react';
import { api, formatCurrency } from '../api/client';
import type { DashboardData } from '../types';
import StatCard from '../components/StatCard';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import SeverityBadge from '../components/SeverityBadge';
import { CostTrendChart, ServiceBreakdownChart } from '../components/charts/CostCharts';

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.dashboard()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner message="Loading dashboard..." />;
  if (error) return <EmptyState title="Failed to load dashboard" description={error} />;
  if (!data) return <EmptyState title="No data" description="Dashboard data is unavailable." />;

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white">Cloud Operations Dashboard</h2>
        <p className="mt-1 text-slate-400">Real-time overview of cloud spend, anomalies, and optimizations</p>
      </div>

      <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Monthly Spend"
          value={formatCurrency(data.total_monthly_spend)}
          subtitle="Current month to date"
        />
        <StatCard
          title="Projected Spend"
          value={formatCurrency(data.projected_spend)}
          subtitle="End-of-month forecast"
          trend="up"
        />
        <StatCard
          title="Active Anomalies"
          value={String(data.anomaly_count)}
          subtitle="Requires investigation"
          trend={data.anomaly_count > 0 ? 'up' : 'neutral'}
        />
        <StatCard
          title="Top Service"
          value={data.top_expensive_services[0]?.service ?? 'N/A'}
          subtitle={
            data.top_expensive_services[0]
              ? formatCurrency(data.top_expensive_services[0].total) + ' / 30d'
              : undefined
          }
        />
      </div>

      <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold text-white">Cost Trend (30 days)</h3>
          <CostTrendChart data={data.cost_trend} />
        </div>
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold text-white">Service Breakdown</h3>
          <ServiceBreakdownChart data={data.service_breakdown} />
        </div>
      </div>

      <div className="card">
        <h3 className="mb-4 text-lg font-semibold text-white">Top Optimization Recommendations</h3>
        {data.optimization_recommendations.length === 0 ? (
          <p className="text-slate-400">No recommendations available. Run the AI agent to generate insights.</p>
        ) : (
          <div className="space-y-4">
            {data.optimization_recommendations.map((rec) => (
              <div key={rec.id} className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h4 className="font-medium text-white">{rec.title}</h4>
                    <p className="mt-1 text-sm text-slate-400">{rec.explanation}</p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-2">
                    <SeverityBadge severity={rec.severity} />
                    {rec.estimated_monthly_savings > 0 && (
                      <span className="text-sm font-medium text-emerald-400">
                        Save {formatCurrency(rec.estimated_monthly_savings)}/mo
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
