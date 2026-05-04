import { useStore } from '../store/useStore'
import { navHistory, revenueData } from '../data/mockData'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import { TrendingUp, Users, UserCheck, DollarSign, Activity, ArrowUpRight, ArrowDownRight } from 'lucide-react'

const fmt = (n: number) =>
  n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : `$${(n / 1e3).toFixed(0)}K`

const pct = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`

const PIE_COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444']

export default function Dashboard() {
  const { clients, investors, positions, deals } = useStore()

  const totalAUM = clients.reduce((s, c) => s + c.aum, 0)
  const activeClients = clients.filter((c) => c.status === 'active').length
  const totalNAV = positions.reduce((s, p) => s + (p.side === 'long' ? p.marketValue : 0), 0)
  const totalPnL = positions.reduce((s, p) => s + p.pnl, 0)
  const portfolioDeals = deals.filter((d) => d.stage === 'portfolio').length

  const sectorAlloc = Object.values(
    positions.reduce((acc, p) => {
      const key = p.sector
      if (!acc[key]) acc[key] = { name: key, value: 0 }
      acc[key].value += Math.abs(p.marketValue)
      return acc
    }, {} as Record<string, { name: string; value: number }>)
  )

  const kpis = [
    { label: 'Total AUM', value: fmt(totalAUM), delta: '+12.4%', up: true, icon: DollarSign, color: 'blue' },
    { label: 'Portfolio NAV', value: fmt(totalNAV), delta: pct(totalPnL / (totalNAV - totalPnL) * 100), up: totalPnL > 0, icon: TrendingUp, color: 'emerald' },
    { label: 'Active Clients', value: String(activeClients), delta: '+2 this quarter', up: true, icon: Users, color: 'violet' },
    { label: 'Portfolio Companies', value: String(portfolioDeals), delta: '+1 this month', up: true, icon: UserCheck, color: 'amber' },
    { label: 'Gross P&L', value: fmt(totalPnL), delta: pct(24.8), up: true, icon: Activity, color: 'emerald' },
    { label: 'Fund IV Progress', value: '35%', delta: '$210M / $600M', up: true, icon: DollarSign, color: 'blue' },
  ]

  const colorMap: Record<string, string> = {
    blue: 'text-blue-400 bg-blue-500/10',
    emerald: 'text-emerald-400 bg-emerald-500/10',
    violet: 'text-violet-400 bg-violet-500/10',
    amber: 'text-amber-400 bg-amber-500/10',
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {kpis.map((k) => {
          const Icon = k.icon
          const cls = colorMap[k.color]
          return (
            <div key={k.label} className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-slate-400 text-xs">{k.label}</span>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${cls}`}>
                  <Icon size={15} />
                </div>
              </div>
              <div className="text-2xl font-bold text-white">{k.value}</div>
              <div className={`flex items-center gap-1 mt-1 text-xs ${k.up ? 'text-emerald-400' : 'text-red-400'}`}>
                {k.up ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                {k.delta}
              </div>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-white font-semibold text-sm">Fund Performance (NAV Index)</div>
              <div className="text-slate-500 text-xs mt-0.5">Base 100 — Jan 2023</div>
            </div>
            <div className="flex items-center gap-1 text-emerald-400 text-sm font-semibold">
              <ArrowUpRight size={14} />
              +48.7%
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={navHistory}>
              <defs>
                <linearGradient id="navGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" />
              <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} domain={[95, 155]} />
              <Tooltip
                contentStyle={{ background: '#0d1117', border: '1px solid #1e2433', borderRadius: '8px', color: '#fff', fontSize: 12 }}
                formatter={(v: number) => [`${v.toFixed(1)}`, 'NAV Index']}
              />
              <Area type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} fill="url(#navGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-4">Sector Allocation</div>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={sectorAlloc} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={3} dataKey="value">
                {sectorAlloc.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#0d1117', border: '1px solid #1e2433', borderRadius: '8px', fontSize: 12 }}
                formatter={(v: number) => [fmt(v), '']}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5 mt-2">
            {sectorAlloc.slice(0, 5).map((s, i) => (
              <div key={s.name} className="flex items-center gap-2 text-xs">
                <div className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: PIE_COLORS[i] }} />
                <span className="text-slate-400 flex-1 truncate">{s.name}</span>
                <span className="text-white font-medium">{fmt(s.value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-4">Monthly Revenue</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={revenueData} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" vertical={false} />
              <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${(v / 1e6).toFixed(1)}M`} />
              <Tooltip
                contentStyle={{ background: '#0d1117', border: '1px solid #1e2433', borderRadius: '8px', fontSize: 12 }}
                formatter={(v: number, name: string) => [fmt(v), name === 'value' ? 'Mgmt Fees' : 'Perf Fees']}
              />
              <Bar dataKey="value" fill="#3b82f6" radius={[3, 3, 0, 0]} />
              <Bar dataKey="value2" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-4">Top Positions</div>
          <div className="space-y-2">
            {positions.slice(0, 6).map((p) => (
              <div key={p.id} className="flex items-center gap-3">
                <div className={`w-1 h-8 rounded-full ${p.side === 'long' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-white text-xs font-medium">{p.ticker}</span>
                    <span className="text-slate-500 text-[10px] truncate">{p.name}</span>
                  </div>
                  <div className="text-slate-500 text-[10px]">{fmt(p.marketValue)}</div>
                </div>
                <div className={`text-xs font-medium ${p.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {pct(p.pnlPct)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
