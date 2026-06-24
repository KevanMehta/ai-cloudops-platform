import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { KubernetesWorkload } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';

function HealthIndicator({ health }: { health: string }) {
  const colors: Record<string, string> = {
    healthy: 'bg-emerald-500',
    warning: 'bg-amber-500',
    unhealthy: 'bg-red-500',
    idle: 'bg-blue-500',
  };
  return (
    <span className={`inline-block h-2.5 w-2.5 rounded-full ${colors[health] ?? 'bg-slate-500'}`} />
  );
}

export default function KubernetesHealth() {
  const [workloads, setWorkloads] = useState<KubernetesWorkload[]>([]);
  const [summary, setSummary] = useState<Record<string, number | string>>({});
  const [unhealthyCount, setUnhealthyCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.kubernetes()
      .then((res) => {
        setWorkloads(res.workloads);
        setSummary(res.cluster_summary);
        setUnhealthyCount(res.unhealthy_count);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner message="Loading Kubernetes workloads..." />;
  if (error) return <EmptyState title="Failed to load Kubernetes data" description={error} />;

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white">Kubernetes Health Monitor</h2>
        <p className="mt-1 text-slate-400">Pod health, resource utilization, and workload recommendations</p>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="card text-center">
          <p className="text-sm text-slate-400">Workloads</p>
          <p className="text-3xl font-bold text-white">{summary.total_workloads}</p>
        </div>
        <div className="card text-center">
          <p className="text-sm text-slate-400">Unhealthy</p>
          <p className="text-3xl font-bold text-red-400">{unhealthyCount}</p>
        </div>
        <div className="card text-center">
          <p className="text-sm text-slate-400">Avg CPU</p>
          <p className="text-3xl font-bold text-brand-400">{summary.avg_cpu_percent}%</p>
        </div>
        <div className="card text-center">
          <p className="text-sm text-slate-400">Avg Memory</p>
          <p className="text-3xl font-bold text-purple-400">{summary.avg_memory_percent}%</p>
        </div>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400">
              <th className="pb-3 pr-4">Health</th>
              <th className="pb-3 pr-4">Namespace</th>
              <th className="pb-3 pr-4">Name</th>
              <th className="pb-3 pr-4">Type</th>
              <th className="pb-3 pr-4">Replicas</th>
              <th className="pb-3 pr-4">CPU</th>
              <th className="pb-3 pr-4">Memory</th>
              <th className="pb-3 pr-4">Restarts</th>
              <th className="pb-3">Recommendation</th>
            </tr>
          </thead>
          <tbody>
            {workloads.map((w) => (
              <tr key={w.id} className="border-b border-slate-800/50">
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2">
                    <HealthIndicator health={w.health} />
                    <span className="capitalize text-slate-300">{w.health}</span>
                  </div>
                </td>
                <td className="py-3 pr-4 text-slate-400">{w.namespace}</td>
                <td className="py-3 pr-4 font-medium text-white">{w.name}</td>
                <td className="py-3 pr-4 text-slate-400">{w.workload_type}</td>
                <td className="py-3 pr-4 text-slate-300">
                  {w.ready_replicas}/{w.replicas}
                </td>
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-16 rounded-full bg-slate-800">
                      <div
                        className={`h-2 rounded-full ${w.cpu_usage_percent > 90 ? 'bg-red-500' : 'bg-brand-500'}`}
                        style={{ width: `${Math.min(w.cpu_usage_percent, 100)}%` }}
                      />
                    </div>
                    <span className="text-slate-400">{w.cpu_usage_percent}%</span>
                  </div>
                </td>
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-16 rounded-full bg-slate-800">
                      <div
                        className={`h-2 rounded-full ${w.memory_usage_percent > 90 ? 'bg-red-500' : 'bg-purple-500'}`}
                        style={{ width: `${Math.min(w.memory_usage_percent, 100)}%` }}
                      />
                    </div>
                    <span className="text-slate-400">{w.memory_usage_percent}%</span>
                  </div>
                </td>
                <td className={`py-3 pr-4 ${w.restart_count > 10 ? 'font-bold text-red-400' : 'text-slate-400'}`}>
                  {w.restart_count}
                </td>
                <td className="py-3 text-xs text-slate-500">{w.recommendation ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
