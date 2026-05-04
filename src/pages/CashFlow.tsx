import { cashFlowData } from '../data/mockData'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'

const fmt = (n: number) =>
  n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : `$${(n / 1e3).toFixed(0)}K`

const enhancedData = cashFlowData.map((d) => ({
  ...d,
  net: d.value - (d.value2 ?? 0),
}))

const WATERFALL = [
  { label: 'Opening Cash', value: 42500000, type: 'balance' },
  { label: 'Capital Calls', value: 38000000, type: 'inflow' },
  { label: 'Distributions', value: -18500000, type: 'outflow' },
  { label: 'Management Fees', value: 3890000, type: 'inflow' },
  { label: 'Performance Fees', value: 4200000, type: 'inflow' },
  { label: 'Operating Expenses', value: -5200000, type: 'outflow' },
  { label: 'Investment Activity', value: -25000000, type: 'outflow' },
  { label: 'FX / Other', value: -820000, type: 'outflow' },
  { label: 'Closing Cash', value: 39070000, type: 'balance' },
]

export default function CashFlow() {
  const totalInflows = enhancedData.reduce((s, d) => s + d.value, 0)
  const totalOutflows = enhancedData.reduce((s, d) => s + (d.value2 ?? 0), 0)
  const netFlow = totalInflows - totalOutflows

  const kpis = [
    { label: 'Total Inflows YTD', value: fmt(totalInflows), delta: '+22.1%', positive: true },
    { label: 'Total Outflows YTD', value: fmt(totalOutflows), delta: '+18.4%', positive: false },
    { label: 'Net Cash Flow', value: fmt(netFlow), delta: `${(netFlow / totalInflows * 100).toFixed(1)}% margin`, positive: true },
    { label: 'Cash Position', value: fmt(39070000), delta: 'As of May 2024', positive: true },
  ]

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-4 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-4">
            <div className="text-slate-400 text-xs mb-2">{k.label}</div>
            <div className="text-2xl font-bold text-white">{k.value}</div>
            <div className={`flex items-center gap-1 mt-1 text-xs ${k.positive ? 'text-emerald-400' : 'text-red-400'}`}>
              {k.positive ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
              {k.delta}
            </div>
          </div>
        ))}
      </div>

      <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
        <div className="text-white font-semibold text-sm mb-1">Cash Flow Statement — Monthly</div>
        <div className="text-slate-500 text-xs mb-4">Inflows, outflows and net cash position</div>
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={enhancedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" vertical={false} />
            <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis yAxisId="bars" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${(v / 1e6).toFixed(0)}M`} />
            <YAxis yAxisId="line" orientation="right" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${(v / 1e6).toFixed(0)}M`} />
            <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid #1e2433', borderRadius: '8px', fontSize: 12 }}
              formatter={(v: number, name: string) => [fmt(v), name === 'value' ? 'Inflows' : name === 'value2' ? 'Outflows' : 'Net']} />
            <Legend formatter={(v) => <span className="text-slate-400 text-xs">{v === 'value' ? 'Inflows' : v === 'value2' ? 'Outflows' : 'Net Flow'}</span>} />
            <Bar yAxisId="bars" dataKey="value" fill="#10b981" opacity={0.8} radius={[3, 3, 0, 0]} name="value" />
            <Bar yAxisId="bars" dataKey="value2" fill="#ef4444" opacity={0.8} radius={[3, 3, 0, 0]} name="value2" />
            <Line yAxisId="line" type="monotone" dataKey="net" stroke="#f59e0b" strokeWidth={2} dot={false} name="net" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-4">Cash Flow Waterfall — Q4 2023</div>
          <div className="space-y-2">
            {WATERFALL.map((w) => {
              const pct = Math.abs(w.value) / 42500000 * 100
              const isBalance = w.type === 'balance'
              const isInflow = w.type === 'inflow'
              return (
                <div key={w.label} className={`flex items-center gap-3 p-2.5 rounded-lg ${isBalance ? 'bg-[#161b26]' : ''}`}>
                  <div className="w-32 text-xs text-slate-400 truncate">{w.label}</div>
                  <div className="flex-1 h-2 bg-[#1e2433] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${isBalance ? 'bg-blue-500' : isInflow ? 'bg-emerald-500' : 'bg-red-500'}`}
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                  <div className={`text-xs font-semibold w-24 text-right ${isBalance ? 'text-blue-400' : isInflow ? 'text-emerald-400' : 'text-red-400'}`}>
                    {isInflow ? '+' : isBalance ? '' : ''}{fmt(w.value)}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-4">Monthly Summary</div>
          <div className="space-y-0">
            <div className="grid grid-cols-4 gap-2 pb-2 border-b border-[#1e2433] text-[10px] text-slate-500 font-medium uppercase">
              <div>Month</div><div className="text-right">Inflow</div><div className="text-right">Outflow</div><div className="text-right">Net</div>
            </div>
            {enhancedData.map((d) => {
              const net = d.value - (d.value2 ?? 0)
              return (
                <div key={d.month} className="grid grid-cols-4 gap-2 py-2 border-b border-[#1e2433]/50 text-xs">
                  <div className="text-slate-400">{d.month}</div>
                  <div className="text-right text-emerald-400">{fmt(d.value)}</div>
                  <div className="text-right text-red-400">{fmt(d.value2 ?? 0)}</div>
                  <div className={`text-right font-medium flex items-center justify-end gap-0.5 ${net >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {net >= 0 ? <ArrowUpRight size={10} /> : <ArrowDownRight size={10} />}
                    {fmt(net)}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
