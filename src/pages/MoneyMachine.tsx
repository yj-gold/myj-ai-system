import { useStore } from '../store/useStore'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar,
} from 'recharts'
import { Zap, TrendingUp, DollarSign, ArrowUpRight, RefreshCw } from 'lucide-react'

const fmt = (n: number) =>
  n >= 1e9 ? `$${(n / 1e9).toFixed(3)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : `$${(n / 1e3).toFixed(1)}K`

const DAILY_AUM = 1340000000
const MGMT_FEE_RATE = 0.02
const PERF_FEE_RATE = 0.20
const DAILY_MGMT = (DAILY_AUM * MGMT_FEE_RATE) / 365
const MONTHLY_MGMT = DAILY_MGMT * 30
const ANNUAL_MGMT = DAILY_AUM * MGMT_FEE_RATE

const ANNUAL_RETURN_PCT = 0.248
const ANNUAL_PERF = DAILY_AUM * ANNUAL_RETURN_PCT * PERF_FEE_RATE

const COMPOUND_DATA = Array.from({ length: 20 }, (_, i) => {
  const year = 2024 + i
  const aum = DAILY_AUM * Math.pow(1 + 0.15, i)
  const fees = aum * 0.02 + aum * 0.248 * 0.20
  return { year: String(year), aum: aum / 1e9, fees: fees / 1e6 }
})

const FEE_ACCRUAL = [
  { day: 'Mon', mgmt: DAILY_MGMT, perf: DAILY_MGMT * 1.8 },
  { day: 'Tue', mgmt: DAILY_MGMT, perf: DAILY_MGMT * 2.1 },
  { day: 'Wed', mgmt: DAILY_MGMT, perf: DAILY_MGMT * 0.9 },
  { day: 'Thu', mgmt: DAILY_MGMT, perf: DAILY_MGMT * 2.4 },
  { day: 'Fri', mgmt: DAILY_MGMT, perf: DAILY_MGMT * 3.2 },
]

const REVENUE_STREAMS = [
  { name: 'Management Fees (2% p.a.)', annual: ANNUAL_MGMT, daily: DAILY_MGMT, pct: 60, color: '#3b82f6' },
  { name: 'Performance Fees (20% HWM)', annual: ANNUAL_PERF, daily: ANNUAL_PERF / 365, pct: 33, color: '#8b5cf6' },
  { name: 'Transaction & Advisory', annual: 1800000, daily: 1800000 / 365, pct: 5, color: '#10b981' },
  { name: 'Other', annual: 600000, daily: 600000 / 365, pct: 2, color: '#f59e0b' },
]

const totalAnnual = REVENUE_STREAMS.reduce((s, r) => s + r.annual, 0)
const totalDaily = REVENUE_STREAMS.reduce((s, r) => s + r.daily, 0)

export default function MoneyMachine() {
  const { clients } = useStore()
  const totalAUM = clients.reduce((s, c) => s + c.aum, 0)

  return (
    <div className="space-y-5">
      <div className="bg-gradient-to-r from-blue-600/10 to-violet-600/10 border border-blue-500/20 rounded-xl p-5 flex items-center gap-5">
        <div className="w-12 h-12 rounded-xl bg-blue-600/20 flex items-center justify-center">
          <Zap size={24} className="text-blue-400" />
        </div>
        <div className="flex-1">
          <div className="text-white font-bold text-lg">Money Machine Dashboard</div>
          <div className="text-slate-400 text-sm">Automated revenue generation · Real-time fee accrual · Compound growth engine</div>
        </div>
        <div className="text-right">
          <div className="text-slate-400 text-xs">Generating right now</div>
          <div className="text-2xl font-bold text-emerald-400 tabular-nums">{fmt(totalDaily)}<span className="text-sm text-slate-400">/day</span></div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Annual Revenue Run Rate', value: fmt(totalAnnual), sub: `From $${(totalAUM / 1e9).toFixed(2)}B AUM`, color: 'text-blue-400', bg: 'bg-blue-500/10' },
          { label: 'Daily Fee Accrual', value: fmt(totalDaily), sub: 'Mgmt + Perf fees combined', color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
          { label: 'Management Fees p.a.', value: fmt(ANNUAL_MGMT), sub: '2% of AUM', color: 'text-violet-400', bg: 'bg-violet-500/10' },
          { label: 'Performance Fees p.a.', value: fmt(ANNUAL_PERF), sub: '20% of 24.8% returns', color: 'text-amber-400', bg: 'bg-amber-500/10' },
        ].map((k) => (
          <div key={k.label} className={`bg-[#0d1117] border border-[#1e2433] rounded-xl p-4`}>
            <div className="text-slate-400 text-xs mb-3">{k.label}</div>
            <div className={`text-2xl font-bold ${k.color}`}>{k.value}</div>
            <div className="text-slate-500 text-xs mt-1">{k.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-1">Revenue Streams</div>
          <div className="text-slate-500 text-xs mb-4">Annual breakdown by source</div>
          <div className="space-y-4">
            {REVENUE_STREAMS.map((r) => (
              <div key={r.name}>
                <div className="flex justify-between text-xs mb-1.5">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-sm" style={{ background: r.color }} />
                    <span className="text-slate-300">{r.name}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-white font-semibold">{fmt(r.annual)}</span>
                    <span className="text-slate-500 ml-2">{fmt(r.daily)}/day</span>
                  </div>
                </div>
                <div className="h-2 bg-[#1e2433] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: `${r.pct}%`, background: r.color }} />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-[#1e2433] flex justify-between items-center">
            <span className="text-slate-400 text-xs">Total Annual Revenue</span>
            <div className="text-right">
              <span className="text-white font-bold text-lg">{fmt(totalAnnual)}</span>
              <div className="text-emerald-400 text-xs flex items-center gap-1 justify-end"><ArrowUpRight size={11} />+18.4% YoY</div>
            </div>
          </div>
        </div>

        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-1">Daily Fee Accrual — This Week</div>
          <div className="text-slate-500 text-xs mb-4">Management fees + performance fees by day</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={FEE_ACCRUAL} barGap={4}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" vertical={false} />
              <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`} />
              <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid #1e2433', borderRadius: '8px', fontSize: 12 }}
                formatter={(v: number, name: string) => [fmt(v), name === 'mgmt' ? 'Management Fee' : 'Performance Fee']} />
              <Bar dataKey="mgmt" fill="#3b82f6" radius={[3, 3, 0, 0]} />
              <Bar dataKey="perf" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-white font-semibold text-sm">20-Year Compound Growth Projection</div>
            <div className="text-slate-500 text-xs mt-0.5">AUM growth at 15% p.a. · Fee revenue projection</div>
          </div>
          <div className="text-right">
            <div className="text-slate-400 text-xs">Projected AUM in 20 years</div>
            <div className="text-emerald-400 font-bold text-xl">${(DAILY_AUM / 1e9 * Math.pow(1.15, 20)).toFixed(1)}B</div>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={COMPOUND_DATA}>
            <defs>
              <linearGradient id="aumG" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="feeG" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" />
            <XAxis dataKey="year" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} interval={2} />
            <YAxis yAxisId="aum" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v.toFixed(0)}B`} />
            <YAxis yAxisId="fees" orientation="right" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v.toFixed(0)}M`} />
            <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid #1e2433', borderRadius: '8px', fontSize: 12 }}
              formatter={(v: number, name: string) => [name === 'aum' ? `$${v.toFixed(2)}B` : `$${v.toFixed(0)}M`, name === 'aum' ? 'AUM' : 'Annual Fees']} />
            <Area yAxisId="aum" type="monotone" dataKey="aum" stroke="#3b82f6" strokeWidth={2} fill="url(#aumG)" />
            <Area yAxisId="fees" type="monotone" dataKey="fees" stroke="#8b5cf6" strokeWidth={2} fill="url(#feeG)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: '10-Year AUM Target', value: `$${(DAILY_AUM / 1e9 * Math.pow(1.15, 10)).toFixed(1)}B`, sub: 'At 15% CAGR', color: 'blue' },
          { label: 'Fee Rev. at $5B AUM', value: fmt(5e9 * 0.02 + 5e9 * 0.15 * 0.20), sub: '2% mgmt + 20% perf', color: 'violet' },
          { label: 'AUM Needed for $100M Rev', value: fmt((100e6 / (0.02 + 0.15 * 0.20))), sub: 'At current fee structure', color: 'emerald' },
        ].map((k) => (
          <div key={k.label} className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-4">
            <div className="text-slate-400 text-xs mb-2">{k.label}</div>
            <div className={`text-2xl font-bold text-${k.color}-400`}>{k.value}</div>
            <div className="text-slate-500 text-xs mt-1">{k.sub}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
