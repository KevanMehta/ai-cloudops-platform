import { useEffect, useState } from 'react';
import { api, formatCurrency, parseActionSteps } from '../api/client';
import type { Recommendation } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import SeverityBadge from '../components/SeverityBadge';

export default function Recommendations() {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [totalSavings, setTotalSavings] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.recommendations()
      .then((res) => {
        setRecs(res.recommendations);
        setTotalSavings(res.total_estimated_savings);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner message="Loading recommendations..." />;
  if (error) return <EmptyState title="Failed to load recommendations" description={error} />;

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white">Optimization Recommendations</h2>
        <p className="mt-1 text-slate-400">
          Actionable insights to reduce costs, improve security, and optimize infrastructure
        </p>
      </div>

      <div className="mb-6 card">
        <p className="text-sm text-slate-400">Total Estimated Monthly Savings</p>
        <p className="text-4xl font-bold text-emerald-400">{formatCurrency(totalSavings)}</p>
      </div>

      {recs.length === 0 ? (
        <EmptyState
          title="No recommendations"
          description="Run the AI agent or Terraform analyzer to generate recommendations."
        />
      ) : (
        <div className="space-y-6">
          {recs.map((rec) => (
            <div key={rec.id} className="card">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-3">
                    <h3 className="text-lg font-semibold text-white">{rec.title}</h3>
                    <SeverityBadge severity={rec.severity} />
                    <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
                      {rec.category.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <p className="mt-2 text-slate-400">{rec.explanation}</p>
                  {rec.estimated_monthly_savings > 0 && (
                    <p className="mt-2 text-sm font-medium text-emerald-400">
                      Estimated savings: {formatCurrency(rec.estimated_monthly_savings)}/month
                    </p>
                  )}
                  <div className="mt-4">
                    <p className="text-sm font-medium text-slate-300">Action Steps:</p>
                    <ol className="mt-2 list-inside list-decimal space-y-1 text-sm text-slate-400">
                      {parseActionSteps(rec.action_steps).map((step, i) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
