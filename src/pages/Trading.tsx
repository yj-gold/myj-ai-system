import { useStore } from '../store/useStore'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid } from 'recharts'
import { TrendingUp, TrendingDown, Activity, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { navHistory } from '../data/mockData'

const fmt = (n: number) =>
  n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : `$${(n / 1e3).toFixed(0)}K`

const PIE_COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4']

const PERF_METRICS = [
  { label: 'Sharpe Ratio', value: '2.14', sub: 'Annualized' },
  { label: 'Sortino Ratio', value: '3.28', sub: 'Annualized' },
  { label: 'Max Drawdown', value: '-8.2%', sub: 'Since inception' },
  { label: 'Beta vs S&P500', value: '0.62', sub: '12-month' },
  { label: 'Alpha (Jensen)', value: '+12.4%', sub: 'vs benchmark' },
  { label: 'Information Ratio', value: '1.87', sub: 'Active returns' },
]

export default function Trading() {
  const { positions, trades } = useStore()

  const longPositions = positions.filter((p) => p.side === 'long')
  const shortPositions = positions.filter((p) => p.side === 'short')
  const totalLong = longPositions.reduce((s, p) => s + p.marketValue, 0)
  const totalShort = Math.abs(shortPositions.reduce((s, p) => s + p.marketValue, 0))
  const totalPnL = positions.reduce((s, p) => s + p.pnl, 0)
  const grossExposure = totalLong + totalShort
  const netExposure = totalLong - totalShort

  const sectorAlloc = Object.values(
    positions.reduce((acc, p) => {
      const key = p.sector
      if (!acc[key]) acc[key] = { name: key, value: 0 }
      acc[key].value += Math.abs(p.marketValue)
      return acc
    }, {} as Record<string, { name: string; value: number }>)
  ).sort((a, b) => b.value - a.value)

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Gross Exposure', value: fmt(grossExposure), delta: `${(grossExposure / 133800000 * 100).toFixed(0)}% of NAV`, up: true },
          { label: 'Net Exposure', value: fmt(netExposure), delta: `${(netExposure / 133800000 * 100).toFixed(0)}% of NAV`, up: true },
          { label: 'Total P&L', value: fmt(totalPnL), delta: '+31.2%', up: totalPnL > 0 },
          { label: 'Positions', value: String(positions.length), delta: `${longPositions.length} long · ${shortPositions.length} short`, up: true },
        ].map((k) => (
          <div key={k.label} className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-4">
            <div className="text-slate-400 text-xs mb-2">{k.label}</div>
            <div className="text-2xl font-bold text-white">{k.value}</div>
            <div className={`flex items-center gap-1 mt-1 text-xs ${k.up ? 'text-emerald-400' : 'text-red-400'}`}>
              {k.up ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}{k.delta}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-4">NAV Performance</div>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={navHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" />
              <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} domain={[95, 155]} />
              <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid #1e2433', borderRadius: '8px', fontSize: 12 }}
                formatter={(v: number) => [`${v.toFixed(1)}`, 'NAV']} />
              <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-3">Sector Exposure</div>
          <ResponsiveContainer width="100%" height={150}>
            <PieChart>
              <Pie data={sectorAlloc} cx="50%" cy="50%" outerRadius={65} dataKey="value" paddingAngle={2}>
                {sectorAlloc.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid #1e2433', borderRadius: '8px', fontSize: 12 }}
                formatter={(v: number) => [fmt(v), '']} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1 mt-1">
            {sectorAlloc.map((s, i) => (
              <div key={s.name} className="flex items-center gap-2 text-[10px]">
                <div className="w-2 h-2 rounded-sm shrink-0" style={{ background: PIE_COLORS[i] }} />
                <span className="text-slate-400 flex-1 truncate">{s.name}</span>
                <span className="text-white">{(s.value / grossExposure * 100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-[#1e2433] flex items-center justify-between">
          <div className="text-white font-semibold text-sm">Positions</div>
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-emerald-500 inline-block"></span> Long</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-red-500 inline-block"></span> Short</span>
          </div>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1e2433]">
              {['', 'Ticker', 'Name', 'Side', 'Qty', 'Entry', 'Current', 'Market Value', 'P&L', 'P&L %', 'Weight', 'Strategy'].map((h) => (
                <th key={h} className="text-left text-slate-500 text-xs font-medium px-4 py-3 whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <tr key={p.id} className="border-b border-[#1e2433] hover:bg-white/2 transition-colors">
                <td className="px-4 py-3">
                  <div className={`w-1 h-6 rounded-full ${p.side === 'long' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                </td>
                <td className="px-4 py-3 text-white font-semibold text-xs">{p.ticker}</td>
                <td className="px-4 py-3 text-slate-400 text-xs">{p.name}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${p.side === 'long' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>
                    {p.side.toUpperCase()}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-300 text-xs">{p.quantity.toLocaleString()}</td>
                <td className="px-4 py-3 text-slate-400 text-xs">${p.entryPrice.toFixed(2)}</td>
                <td className="px-4 py-3 text-white text-xs font-medium">${p.currentPrice.toFixed(2)}</td>
                <td className="px-4 py-3 text-white text-xs font-medium">{fmt(Math.abs(p.marketValue))}</td>
                <td className={`px-4 py-3 text-xs font-medium ${p.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {p.pnl >= 0 ? '+' : ''}{fmt(p.pnl)}
                </td>
                <td className={`px-4 py-3 text-xs font-semibold ${p.pnlPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  <div className="flex items-center gap-0.5">
                    {p.pnlPct >= 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                    {p.pnlPct >= 0 ? '+' : ''}{p.pnlPct.toFixed(1)}%
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs">{Math.abs(p.weight).toFixed(1)}%</td>
                <td className="px-4 py-3 text-slate-400 text-xs">{p.strategy}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-4">Performance Metrics</div>
          <div className="grid grid-cols-3 gap-3">
            {PERF_METRICS.map((m) => (
              <div key={m.label} className="bg-[#161b26] rounded-lg p-3">
                <div className="text-slate-500 text-[10px] mb-1">{m.label}</div>
                <div className="text-white font-bold text-lg">{m.value}</div>
                <div className="text-slate-600 text-[10px]">{m.sub}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-[#1e2433]">
            <div className="text-white font-semibold text-sm">Recent Trades</div>
          </div>
          <div className="divide-y divide-[#1e2433]">
            {trades.map((t) => (
              <div key={t.id} className="px-5 py-3 flex items-center gap-3">
                <div className={`w-6 h-6 rounded flex items-center justify-center shrink-0 ${t.side === 'buy' ? 'bg-emerald-500/15' : 'bg-red-500/15'}`}>
                  {t.side === 'buy' ? <TrendingUp size={11} className="text-emerald-400" /> : <TrendingDown size={11} className="text-red-400" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-white text-xs font-medium">{t.ticker} <span className="text-slate-500">{t.name}</span></div>
                  <div className="text-slate-500 text-[10px]">{t.date} · {t.strategy}</div>
                </div>
                <div className="text-right">
                  <div className="text-white text-xs font-medium">{fmt(t.value)}</div>
                  <div className={`text-[10px] ${t.status === 'filled' ? 'text-emerald-400' : t.status === 'pending' ? 'text-amber-400' : 'text-red-400'}`}>
                    {t.status}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
