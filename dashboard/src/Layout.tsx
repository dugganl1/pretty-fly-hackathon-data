import { NavLink, Outlet } from 'react-router-dom';

const tabs = [
  { to: '/assessment', label: 'Assessment' },
  { to: '/pnl', label: 'P&L' },
  { to: '/revenue', label: 'Revenue & Marketing' },
  { to: '/operations', label: 'Operations' },
  { to: '/customers', label: 'Customers & Support' },
];

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border bg-surface sticky top-0 z-50">
        <div className="max-w-[1400px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold tracking-tight text-white">
              Pretty Fly
            </h1>
            <span className="text-xs text-neutral-500 font-medium tracking-wide uppercase">
              Wayflyer Assessment
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-[11px] text-neutral-600 font-mono">
              Jun 2024 — May 2026
            </span>
            <span className="text-[10px] text-neutral-700 border border-neutral-800 rounded px-2 py-0.5">
              Wayflyer &times; Fin AI
            </span>
          </div>
        </div>
        <nav className="max-w-[1400px] mx-auto px-6 flex gap-1 -mb-px">
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              className={({ isActive }) =>
                `px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  isActive
                    ? 'border-accent text-white'
                    : 'border-transparent text-neutral-500 hover:text-neutral-300'
                }`
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="flex-1">
        <div className="max-w-[1400px] mx-auto px-6 py-8">
          <Outlet />
        </div>
      </main>
      <footer className="border-t border-border py-6">
        <div className="max-w-[1400px] mx-auto px-6 flex items-center justify-between">
          <div className="text-xs text-neutral-600">
            <span className="font-medium">About this analysis:</span>{' '}
            Prepared by Wayflyer using 24 months of Pretty Fly operational data.
            All metrics derived from source tables — every number reconciles.
          </div>
          <a
            href="#/reconcile"
            className="text-xs text-neutral-600 hover:text-neutral-400 font-mono flex-shrink-0 ml-4"
          >
            /reconcile
          </a>
        </div>
      </footer>
    </div>
  );
}
