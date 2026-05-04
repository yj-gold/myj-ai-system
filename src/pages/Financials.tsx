import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { ArrowUpRight, ArrowDownRight } from 'lucide-react'

const fmt = (n: number, compact = false) => {
  if (compact) return n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : `$${(n / 1e3).toFixed(0)}K`
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

const PNL = [
  { q: 'Q1 23', revenue: 8400000, expenses: 4200000, net: 4200000 },
  { q: 'Q2 23', revenue: 9200000, expenses: 4500000, net: 4700000 },
  { q: 'Q3 23', revenue: 10100000, expenses: 4800000, net: 5300000 },
  { q: 'Q4 23', revenue: 11800000, expenses: 5200000, net: 6600000 },
  { q: 'Q1 24', revenue: 9800000, expenses: 4600000, net: 5200000 },
]

const BS_ASSETS = [
  { name: 'Cash & Equivalents', value: 39070000 },
  { name: 'Portfolio Investments', value: 133800000 },
  { name: 'Receivables', value: 8200000 },
  { name: 'Other Assets', value: 2400000 },
]

const BS_LIABILITIES = [
  { name: 'Management Fees Payable', value: 3800000 },
  { name: 'Accrued Expenses', value: 2100000 },
  { name: 'Other Liabilities', value: 1200000 },
]

const MARGINS = [
  { q: 'Q1 23', gross: 78, net: 50 },
  { q: 'Q2 23', gross: 80, net: 51 },
  { q: 'Q3 23', gross: 81, net: 52.5 },
  { q: 'Q4 23', gross: 83, net: 55.9 },
  { q: 'Q1 24', gross: 82, net: 53.1 },
]

const IS_ROWS = [
  { label: 'Management Fees', q1: 3120000, q2: 3240000, q3: 3380000, q4: 3890000, fy: 13630000, change: 12.4 },
  { label: 'Performance Fees', q1: 2100000, q2: 2300000, q3: 2800000, q4: 4200000, fy: 11400000, change: 31.5 },
  { label: 'Transaction Fees', q1: 980000, q2: 1580000, q3: 1820000, q4: 1510000, fy: 5890000, change: 8.2 },
  { label: 'Other Income', q1: 200000, q2: 80000, q3: 100000, q4: 200000, fy: 580000, change: -5.1 },
  { label: 'Total Revenue', q1: 6400000, q2: 7200000, q3: 8100000, q4: 9800000, fy: 31500000, change: 18.4, bold: true },
  { label: 'Personnel Costs', q1: -2100000, q2: -2250000, q3: -2400000, q4: -2600000, fy: -9350000, change: 14.2 },
  { label: 'Technology & Data', q1: -480000, q2: -490000, q3: -510000, q4: -520000, fy: -2000000, change: 6.3 },
  { label: 'Compliance & Legal', q1: -380000, q2: -410000, q3: -400000, q4: -450000, fy: -1640000, change: 9.3 },
  { label: 'Other OpEx', q1: -240000, q2: -350000, q3: -490000, q4: -630000, fy: -1710000, change: 42.5 },
  { label: 'Total Expenses', q1: -3200000, q2: -3500000, q3: -3800000, q4: -4200000, fy: -14700000, change: 15.6, bold: true },
  { label: 'EBITDA', q1: 3200000, q2: 3700000, q3: 4300000, q4: 5600000, fy: 16800000, change: 21.7, bold: true },
  { label: 'D&A', q1: -120000, q2: -125000, q3: -130000, q4: -135000, fy: -510000, change: 8.5 },
  { label: 'Net Income', q1: 3080000, q2: 3575000, q3: 4170000, q4: 5465000, fy: 16290000, change: 22.1, bold: true },
]

const totalAssets = BS_ASSETS.reduce((s, a) => s + a.value, 0)
const totalLiabilities = BS_LIABILITIES.reduce((s, l) => s + l.value, 0)
const totalEquity = totalAssets - totalLiabilities

export default function Financials() {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total Revenue FY', value: fmt(31500000, true), delta: '+18.4%', up: true },
          { label: 'Net Income FY', value: fmt(16290000, true), delta: '+22.1%', up: true },
          { label: 'EBITDA FY', value: fmt(16800000, true), delta: '+21.7%', up: true },
          { label: 'EBITDA Margin', value: '53.3%', delta: '+1.5pp YoY', up: true },
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

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-4">P&L Quarterly</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={PNL} barGap={4}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" vertical={false} />
              <XAxis dataKey="q" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${(v / 1e6).toFixed(0)}M`} />
              <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid #1e2433', borderRadius: '8px', fontSize: 12 }}
                formatter={(v: number, name: string) => [fmt(v, true), name === 'revenue' ? 'Revenue' : name === 'expenses' ? 'Expenses' : 'Net Income']} />
              <Legend formatter={(v) => <span className="text-slate-400 text-xs capitalize">{v}</span>} />
              <Bar dataKey="revenue" fill="#3b82f6" radius={[3, 3, 0, 0]} />
              <Bar dataKey="expenses" fill="#ef4444" opacity={0.7} radius={[3, 3, 0, 0]} />
              <Bar dataKey="net" fill="#10b981" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-4">Margin Trends</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={MARGINS}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" />
              <XAxis dataKey="q" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} domain={[45, 90]} />
              <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid #1e2433', borderRadius: '8px', fontSize: 12 }}
                formatter={(v: number, name: string) => [`${v}%`, name === 'gross' ? 'Gross Margin' : 'Net Margin']} />
              <Legend formatter={(v) => <span className="text-slate-400 text-xs">{v === 'gross' ? 'Gross Margin' : 'Net Margin'}</span>} />
              <Line type="monotone" dataKey="gross" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3, fill: '#3b82f6' }} />
              <Line type="monotone" dataKey="net" stroke="#10b981" strokeWidth={2} dot={{ r: 3, fill: '#10b981' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-[#0d1117] border border-[#1e2433] rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-[#1e2433]">
            <div className="text-white font-semibold text-sm">Income Statement</div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[#1e2433]">
                  {['', 'Q1 24', 'Q2 24', 'Q3 24', 'Q4 24', 'FY 24', 'YoY'].map((h) => (
                    <th key={h} className="text-right first:text-left text-slate-500 font-medium px-4 py-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {IS_ROWS.map((r) => (
                  <tr key={r.label} className={`border-b border-[#1e2433]/50 ${r.bold ? 'bg-[#161b26]' : 'hover:bg-white/1'}`}>
                    <td className={`px-4 py-2.5 ${r.bold ? 'text-white font-semibold' : 'text-slate-400'}`}>{r.label}</td>
                    {[r.q1, r.q2, r.q3, r.q4, r.fy].map((v, i) => (
                      <td key={i} className={`px-4 py-2.5 text-right ${r.bold ? 'text-white font-semibold' : v < 0 ? 'text-red-400' : 'text-slate-300'}`}>
                        {fmt(v, true)}
                      </td>
                    ))}
                    <td className={`px-4 py-2.5 text-right ${r.change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {r.change >= 0 ? '+' : ''}{r.change}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
          <div className="text-white font-semibold text-sm mb-4">Balance Sheet</div>
          <div className="space-y-4">
            <div>
              <div className="text-slate-500 text-xs font-medium uppercase mb-2">Assets</div>
              {BS_ASSETS.map((a) => (
                <div key={a.name} className="flex justify-between py-2 border-b border-[#1e2433]/50 text-xs">
                  <span className="text-slate-400">{a.name}</span>
                  <span className="text-white font-medium">{fmt(a.value, true)}</span>
                </div>
              ))}
              <div className="flex justify-between py-2 text-xs font-semibold">
                <span className="text-white">Total Assets</span>
                <span className="text-blue-400">{fmt(totalAssets, true)}</span>
              </div>
            </div>
            <div>
              <div className="text-slate-500 text-xs font-medium uppercase mb-2">Liabilities</div>
              {BS_LIABILITIES.map((l) => (
                <div key={l.name} className="flex justify-between py-2 border-b border-[#1e2433]/50 text-xs">
                  <span className="text-slate-400">{l.name}</span>
                  <span className="text-white font-medium">{fmt(l.value, true)}</span>
                </div>
              ))}
              <div className="flex justify-between py-2 text-xs font-semibold">
                <span className="text-white">Total Liabilities</span>
                <span className="text-red-400">{fmt(totalLiabilities, true)}</span>
              </div>
            </div>
            <div className="pt-2 border-t border-[#1e2433]">
              <div className="flex justify-between py-2 text-sm font-bold">
                <span className="text-white">Net Equity (NAV)</span>
                <span className="text-emerald-400">{fmt(totalEquity, true)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
