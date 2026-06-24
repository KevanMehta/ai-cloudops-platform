import { useState } from 'react';
import { api } from '../api/client';
import type { AgentRun } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';

const STEPS = [
  'analyze_cost_data',
  'detect_anomalies',
  'inspect_infrastructure',
  'generate_recommendations',
  'executive_summary',
];

export default function AgentReport() {
  const [run, setRun] = useState<AgentRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.runAgent();
      setRun(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Agent run failed');
    } finally {
      setLoading(false);
    }
  };

  const completedSteps: string[] = run ? JSON.parse(run.steps_completed || '[]') : [];

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">AI CloudOps Agent</h2>
          <p className="mt-1 text-slate-400">
            LangGraph-style workflow: analyze costs, detect anomalies, inspect infra, recommend actions
          </p>
        </div>
        <button
          onClick={handleRun}
          disabled={loading}
          className="rounded-lg bg-brand-600 px-6 py-3 font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
        >
          {loading ? 'Running Agent...' : 'Run Agent Workflow'}
        </button>
      </div>

      {loading && <LoadingSpinner message="Agent analyzing cloud infrastructure..." />}
      {error && <EmptyState title="Agent run failed" description={error} />}

      {!run && !loading && !error && (
        <EmptyState
          title="No agent report yet"
          description="Click 'Run Agent Workflow' to execute the full CloudOps analysis pipeline."
        />
      )}

      {run && !loading && (
        <div className="space-y-6">
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">Run #{run.id}</h3>
                <p className="text-sm text-slate-400">
                  Status: <span className={run.status === 'completed' ? 'text-emerald-400' : 'text-red-400'}>{run.status}</span>
                  {run.used_openai && ' • Powered by OpenAI'}
                  {!run.used_openai && ' • Rule-based AI (no API key)'}
                </p>
              </div>
            </div>
            <div className="mt-6 flex flex-wrap gap-2">
              {STEPS.map((step) => (
                <span
                  key={step}
                  className={`rounded-full px-3 py-1 text-xs font-medium ${
                    completedSteps.includes(step)
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-slate-800 text-slate-500'
                  }`}
                >
                  {step.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>

          {[
            { title: 'Cost Analysis', content: run.cost_analysis },
            { title: 'Anomaly Summary', content: run.anomaly_summary },
            { title: 'Infrastructure Inspection', content: run.infra_inspection },
            { title: 'Recommendations', content: run.recommendations_summary },
          ].map(
            (section) =>
              section.content && (
                <div key={section.title} className="card">
                  <h3 className="mb-2 text-lg font-semibold text-white">{section.title}</h3>
                  <p className="text-slate-300">{section.content}</p>
                </div>
              ),
          )}

          {run.executive_summary && (
            <div className="card border-brand-600/30">
              <h3 className="mb-4 text-lg font-semibold text-brand-400">Executive Summary</h3>
              <div className="prose prose-invert max-w-none whitespace-pre-wrap text-slate-300">
                {run.executive_summary}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
