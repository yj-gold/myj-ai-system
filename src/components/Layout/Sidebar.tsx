import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Users, UserCheck, GitBranch, TrendingUp,
  ArrowLeftRight, Landmark, BarChart2, LineChart, ShieldCheck,
  RefreshCw, Zap, ChevronRight,
} from 'lucide-react'

const nav = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/clients', icon: Users, label: 'Clients' },
  { to: '/investors', icon: UserCheck, label: 'Investors' },
  { to: '/pipeline', icon: GitBranch, label: 'Pipeline' },
  { to: '/revenue', icon: TrendingUp, label: 'Revenue' },
  { to: '/cashflow', icon: ArrowLeftRight, label: 'Cash Flow' },
  { to: '/funding', icon: Landmark, label: 'Funding' },
  { to: '/financials', icon: BarChart2, label: 'Financials' },
  { to: '/trading', icon: LineChart, label: 'Trading' },
  { to: '/compliance', icon: ShieldCheck, label: 'Compliance' },
  { to: '/sync', icon: RefreshCw, label: 'Sync' },
  { to: '/money-machine', icon: Zap, label: 'Money Machine' },
]

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-full w-56 bg-[#0d1117] border-r border-[#1e2433] flex flex-col z-40">
      <div className="px-5 py-5 border-b border-[#1e2433]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-blue-600 flex items-center justify-center">
            <Zap size={14} className="text-white" />
          </div>
          <div>
            <div className="text-white font-bold text-sm tracking-wide">MYJ Capital</div>
            <div className="text-slate-500 text-[10px] uppercase tracking-widest">Hedge Fund CRM</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 py-3 overflow-y-auto">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg text-sm transition-all group ${
                isActive
                  ? 'bg-blue-600/15 text-blue-400 font-medium'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={16} className={isActive ? 'text-blue-400' : 'text-slate-500 group-hover:text-slate-300'} />
                <span className="flex-1">{label}</span>
                {isActive && <ChevronRight size={12} className="text-blue-400/60" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-[#1e2433]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-violet-500 to-blue-600 flex items-center justify-center text-white text-xs font-bold">M</div>
          <div>
            <div className="text-white text-xs font-medium">Admin</div>
            <div className="text-slate-500 text-[10px]">MYJ Capital</div>
          </div>
          <div className="ml-auto w-2 h-2 rounded-full bg-emerald-400"></div>
        </div>
      </div>
    </aside>
  )
}
