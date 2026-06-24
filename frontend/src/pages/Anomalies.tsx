import { useEffect, useState } from 'react';
import { api, formatCurrency } from '../api/client';
import type { Anomaly } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import SeverityBadge from '../components/SeverityBadge';

export default function Anomalies() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    api.anomalies()
      .then((res) => {
        setAnomalies(res.anomalies);
        setCounts(res.count_by_severity);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const filtered =
    filter === 'all' ? anomalies : anomalies.filter((a) => a.severity === filter);

  if (loading) return <LoadingSpinner message="Detecting anomalies..." />;
  if (error) return <EmptyState title="Failed to load anomalies" description={error} />;

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white">Cost Anomaly Detection</h2>
        <p className="mt-1 text-slate-400">
          Statistical analysis of billing data to identify unusual spending patterns
        </p>
      </div>

      <div className="mb-6 flex gap-4">
        {['all', 'high', 'medium', 'low'].map((sev) => (
          <button
            key={sev}
            onClick={() => setFilter(sev)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              filter === sev
                ? 'bg-brand-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            {sev === 'all' ? 'All' : sev.charAt(0).toUpperCase() + sev.slice(1)}
            {sev !== 'all' && counts[sev] !== undefined && ` (${counts[sev]})`}
            {sev === 'all' && ` (${anomalies.length})`}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState title="No anomalies found" description="No cost anomalies match the selected filter." />
      ) : (
        <div className="space-y-4">
          {filtered.map((a) => (
            <div key={a.id} className="card">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="text-lg font-semibold text-white">
                      {a.service} — {a.date}
                    </h3>
                    <SeverityBadge severity={a.severity} />
                  </div>
                  <p className="mt-2 text-sm text-slate-400">{a.explanation}</p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-2xl font-bold text-red-400">{formatCurrency(a.amount)}</p>
                  <p className="text-sm text-slate-500">
                    Expected: {formatCurrency(a.expected_amount)}
                  </p>
                  <p className="text-sm font-medium text-amber-400">
                    +{a.deviation_percent.toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
