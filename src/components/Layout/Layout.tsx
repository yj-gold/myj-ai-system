import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import { Bell, Search } from 'lucide-react'

const titles: Record<string, string> = {
  '/': 'Dashboard',
  '/clients': 'Clients',
  '/investors': 'Investors',
  '/pipeline': 'Deal Pipeline',
  '/revenue': 'Revenue',
  '/cashflow': 'Cash Flow',
  '/funding': 'Funding',
  '/financials': 'Financials',
  '/trading': 'Trading',
  '/compliance': 'Compliance',
  '/sync': 'Sync',
  '/money-machine': 'Money Machine',
}

export default function Layout() {
  const { pathname } = useLocation()
  const title = titles[pathname] ?? 'MYJ Capital'

  return (
    <div className="flex h-screen bg-[#080b12] text-white overflow-hidden">
      <Sidebar />
      <div className="flex-1 ml-56 flex flex-col overflow-hidden">
        <header className="h-14 bg-[#0d1117]/80 backdrop-blur border-b border-[#1e2433] flex items-center px-6 gap-4 shrink-0">
          <h1 className="text-sm font-semibold text-white">{title}</h1>
          <div className="ml-auto flex items-center gap-3">
            <div className="flex items-center gap-2 bg-[#161b26] rounded-lg px-3 py-1.5 text-slate-400 text-xs border border-[#1e2433]">
              <Search size={13} />
              <span>Search...</span>
              <span className="text-[10px] bg-[#1e2433] px-1.5 py-0.5 rounded text-slate-500">⌘K</span>
            </div>
            <button className="relative p-2 rounded-lg hover:bg-white/5 text-slate-400 hover:text-white transition-colors">
              <Bell size={16} />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-red-500"></span>
            </button>
            <div className="text-xs text-slate-500 border-l border-[#1e2433] pl-3">
              <span className="text-slate-300 font-medium">NAV</span>{' '}
              <span className="text-emerald-400">$133.8M</span>
            </div>
            <div className="text-xs text-slate-500 border-l border-[#1e2433] pl-3">
              <span className="text-slate-300 font-medium">AUM</span>{' '}
              <span className="text-blue-400">$1.34B</span>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
