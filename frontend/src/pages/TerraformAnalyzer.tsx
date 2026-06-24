import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { TerraformFinding } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import SeverityBadge from '../components/SeverityBadge';

export default function TerraformAnalyzer() {
  const [findings, setFindings] = useState<TerraformFinding[]>([]);
  const [files, setFiles] = useState<string[]>([]);
  const [riskScore, setRiskScore] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

  const analyze = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.analyzeTerraform();
      setFindings(res.findings);
      setFiles(res.files_analyzed);
      setRiskScore(res.risk_score);
      setInitialized(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    analyze();
  }, []);

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Terraform Analyzer</h2>
          <p className="mt-1 text-slate-400">
            Scan IaC for risky patterns: overprovisioning, public storage, missing tags, no autoscaling
          </p>
        </div>
        <button
          onClick={analyze}
          disabled={loading}
          className="rounded-lg bg-brand-600 px-6 py-2 font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          Re-analyze
        </button>
      </div>

      {loading && <LoadingSpinner message="Analyzing Terraform files..." />}
      {error && <EmptyState title="Analysis failed" description={error} />}

      {initialized && !loading && (
        <>
          <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="card text-center">
              <p className="text-sm text-slate-400">Files Analyzed</p>
              <p className="text-3xl font-bold text-white">{files.length}</p>
              <p className="mt-1 text-xs text-slate-500">{files.join(', ')}</p>
            </div>
            <div className="card text-center">
              <p className="text-sm text-slate-400">Total Findings</p>
              <p className="text-3xl font-bold text-amber-400">{findings.length}</p>
            </div>
            <div className="card text-center">
              <p className="text-sm text-slate-400">Risk Score</p>
              <p className={`text-3xl font-bold ${riskScore > 60 ? 'text-red-400' : riskScore > 30 ? 'text-amber-400' : 'text-emerald-400'}`}>
                {riskScore}/100
              </p>
            </div>
          </div>

          {findings.length === 0 ? (
            <EmptyState title="No issues found" description="Terraform configuration passed all checks." />
          ) : (
            <div className="space-y-4">
              {findings.map((f) => (
                <div key={f.id} className="card">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex flex-wrap items-center gap--2">
                        <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">{f.file_name}</span>
                        <span className="text-sm font-medium text-white">
                          {f.resource_type}.{f.resource_name}
                        </span>
                        <SeverityBadge severity={f.severity} />
                        <span className="rounded bg-brand-600/20 px-2 py-0.5 text-xs text-brand-400">
                          {f.issue_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-slate-400">{f.description}</p>
                      <p className="mt-2 text-sm text-emerald-400">💡 {f.recommendation}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
