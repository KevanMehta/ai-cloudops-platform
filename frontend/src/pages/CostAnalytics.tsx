import { useEffect, useState } from 'react';
import { api, formatCurrency } from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import { CostTrendChart, ServiceBarChart } from '../components/charts/CostCharts';
import type { CloudCost, CostTrendPoint, ServiceBreakdown } from '../types';

export default function CostAnalytics() {
  const [costs, setCosts] = useState<CloudCost[]>([]);
  const [total, setTotal] = useState(0);
  const [byService, setByService] = useState<ServiceBreakdown[]>([]);
  const [trend, setTrend] = useState<CostTrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(90);

  useEffect(() => {
    setLoading(true);
    api.costs(days)
      .then((res) => {
        setCosts(res.costs);
        setTotal(res.total);
        setByService(res.by_service);
        setTrend(res.trend);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [days]);

  if (loading) return <LoadingSpinner message="Loading cost data..." />;
  if (error) return <EmptyState title="Failed to load costs" description={error} />;

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Cost Analytics</h2>
          <p className="mt-1 text-slate-400">90-day cloud billing analysis across AWS services</p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-white"
        >
          <option value={30}>Last 30 days</option>
          <option value={60}>Last 60 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      <div className="mb-6 card">
        <p className="text-sm text-slate-400">Total spend ({days} days)</p>
        <p className="text-4xl font-bold text-brand-400">{formatCurrency(total)}</p>
      </div>

      <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold">Daily Cost Trend</h3>
          <CostTrendChart data={trend} />
        </div>
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold">Spend by Service</h3>
          <ServiceBarChart data={byService} />
        </div>
      </div>

      <div className="card overflow-x-auto">
        <h3 className="mb-4 text-lg font-semibold">Recent Billing Records</h3>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400">
              <th className="pb-3 pr-4">Date</th>
              <th className="pb-3 pr-4">Service</th>
              <th className="pb-3 pr-4">Region</th>
              <th className="pb-3">Amount</th>
            </tr>
          </thead>
          <tbody>
            {costs.slice(0, 50).map((c) => (
              <tr key={c.id} className="border-b border-slate-800/50">
                <td className="py-3 pr-4 text-slate-300">{c.date}</td>
                <td className="py-3 pr-4 font-medium text-white">{c.service}</td>
                <td className="py-3 pr-4 text-slate-400">{c.region}</td>
                <td className="py-3 text-brand-400">{formatCurrency(c.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
