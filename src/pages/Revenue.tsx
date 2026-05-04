import { revenueData } from '../data/mockData'
import {
  BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { TrendingUp, DollarSign, Percent, ArrowUpRight } from 'lucide-react'

const fmt = (n: number) =>
  n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : `$${(n / 1e3).toFixed(0)}K`

const AUM_TREND = [
  { month: 'Jan', aum: 1180 }, { month: 'Feb', aum: 1205 }, { month: 'Mar', aum: 1230 },
  { month: 'Apr', aum: 1218 }, { month: 'May', aum: 1265 }, { month: 'Jun', aum: 1290 },
  { month: 'Jul', aum: 1275 }, { month: 'Aug', aum: 1310 }, { month: 'Sep', aum: 1335 },
  { month: 'Oct', aum: 1320 }, { month: 'Nov', aum: 1358 }, { month: 'Dec', aum: 1395 },
]

const FEE_BREAKDOWN = [
  { name: 'Management Fees (2%)', value: 38400000, color: '#3b82f6' },
  { name: 'Performance Fees (20%)', value: 25200000, color: '#8b5cf6' },
  { name: 'Transaction Fees', value: 1800000, color: '#10b981' },
  { name: 'Other', value: 600000, color: '#f59e0b' },
]

export default function Revenue() {
  const totalRevenue = FEE_BREAKDOWN.reduce((s, f) => s + f.value, 0)
  const totalMgmt = revenueData.reduce((s, r) => s + r.value, 0)
  const totalPerf = revenueData.reduce((s, r) => s + (r.value2 ?? 0), 0)
  const lastMonth = revenueData[revenueData.length - 1]

  const kpis = [
    { label: 'Total Revenue YTD', value: fmt(totalRevenue), delta: '+18.4%', icon: DollarSign, color: 'text-blue-400 bg-blue-500/10' },
    { label: 'Management Fees YTD', value: fmt(totalMgmt), delta: '+12.1%', icon: Percent, color: 'text-violet-400 bg-violet-500/10' },
    { label: 'Performance Fees YTD', value: fmt(totalPerf), delta: '+31.5%', icon: TrendingUp, color: 'text-emerald-400 bg-emerald-500/10' },
    { label: 'Last Month Total', value: fmt(lastMonth.value + (lastMonth.value2 ?? 0)), delta: '+8.2%', icon: ArrowUpRight, color: 'text-amber-400 bg-amber-500/10' },
  ]

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-4 gap-4">
        {kpis.map((k) => {
          const Icon = k.icon
          return (
            <div key={k.label} className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-slate-400 text-xs">{k.label}</span>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${k.color}`}><Icon size={15} /></div>
              </div>
              <div className="text-2xl font-bold text-white">{k.value}</div>
              <div className="flex items-center gap-1 mt-1 text-xs text-emerald-400">
                <ArrowUpRight size={12} />{k.delta}
              </div>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-1">Monthly Revenue Breakdown</div>
          <div className="text-slate-500 text-xs mb-4">Management fees vs. performance fees</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={revenueData} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" vertical={false} />
              <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${(v / 1e6).toFixed(1)}M`} />
              <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid #1e2433', borderRadius: '8px', fontSize: 12 }}
                formatter={(v: number, name: string) => [fmt(v), name === 'value' ? 'Mgmt Fees' : 'Perf Fees']} />
              <Legend formatter={(v) => <span className="text-slate-400 text-xs">{v === 'value' ? 'Management Fees' : 'Performance Fees'}</span>} />
              <Bar dataKey="value" fill="#3b82f6" radius={[3, 3, 0, 0]} name="value" />
              <Bar dataKey="value2" fill="#8b5cf6" radius={[3, 3, 0, 0]} name="value2" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-4">Revenue Mix</div>
          <div className="space-y-3">
            {FEE_BREAKDOWN.map((f) => (
              <div key={f.name}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">{f.name}</span>
                  <span className="text-white font-medium">{fmt(f.value)}</span>
                </div>
                <div className="h-1.5 bg-[#1e2433] rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${(f.value / totalRevenue) * 100}%`, background: f.color }} />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-6 pt-4 border-t border-[#1e2433]">
            <div className="text-slate-400 text-xs">Total Revenue</div>
            <div className="text-2xl font-bold text-white">{fmt(totalRevenue)}</div>
            <div className="text-emerald-400 text-xs mt-0.5 flex items-center gap-1"><ArrowUpRight size={11} />+18.4% vs last year</div>
          </div>
        </div>
      </div>

      <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
        <div className="text-white font-semibold text-sm mb-1">AUM Trend (M USD)</div>
        <div className="text-slate-500 text-xs mb-4">Assets under management growth</div>
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={AUM_TREND}>
            <defs>
              <linearGradient id="aumGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" />
            <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}M`} domain={[1150, 1420]} />
            <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid #1e2433', borderRadius: '8px', fontSize: 12 }}
              formatter={(v: number) => [`$${v}M`, 'AUM']} />
            <Area type="monotone" dataKey="aum" stroke="#3b82f6" strokeWidth={2} fill="url(#aumGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
