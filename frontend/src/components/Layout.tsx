import { NavLink, Outlet } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api } from '../api/client';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊' },
  { to: '/costs', label: 'Cost Analytics', icon: '💰' },
  { to: '/anomalies', label: 'Anomalies', icon: '⚠️' },
  { to: '/agent', label: 'AI Agent Report', icon: '🤖' },
  { to: '/terraform', label: 'Terraform Analyzer', icon: '🏗️' },
  { to: '/kubernetes', label: 'Kubernetes Health', icon: '☸️' },
  { to: '/recommendations', label: 'Recommendations', icon: '💡' },
];

export default function Layout() {
  const [health, setHealth] = useState<string>('checking');

  useEffect(() => {
    api.health()
      .then((h) => setHealth(h.status))
      .catch(() => setHealth('offline'));
  }, []);

  return (
    <div className="flex min-h-screen">
      <aside className="fixed flex h-full w-64 flex-col border-r border-slate-800 bg-slate-950">
        <div className="border-b border-slate-800 p-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600 text-xl">
              ☁️
            </div>
            <div>
              <h1 className="text-sm font-bold text-white">AI CloudOps</h1>
              <p className="text-xs text-slate-500">Platform v1.0</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-4">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-600/20 text-brand-400'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-800 p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span
              className={`h-2 w-2 rounded-full ${
                health === 'healthy' ? 'bg-emerald-500' : health === 'checking' ? 'bg-amber-500' : 'bg-red-500'
              }`}
            />
            API {health}
          </div>
        </div>
      </aside>
      <main className="ml-64 flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}
