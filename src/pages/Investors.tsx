import { useState } from 'react'
import { useStore } from '../store/useStore'
import type { Investor, InvestorStatus } from '../types'
import { Plus, Edit2, Trash2, Search, X, TrendingUp, TrendingDown } from 'lucide-react'

const fmt = (n: number) =>
  n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : `$${(n / 1e3).toFixed(0)}K`

const STATUS_COLORS: Record<InvestorStatus, string> = {
  active: 'bg-emerald-500/15 text-emerald-400',
  committed: 'bg-blue-500/15 text-blue-400',
  exited: 'bg-slate-500/15 text-slate-400',
}

const EMPTY: Omit<Investor, 'id'> = {
  name: '', type: 'Institutional', committed: 0, called: 0, distributed: 0,
  nav: 0, irr: 0, multiple: 0, status: 'committed', fund: 'MYJ Fund IV', since: '', country: '',
}

export default function Investors() {
  const { investors, addInvestor, updateInvestor, deleteInvestor } = useStore()
  const [search, setSearch] = useState('')
  const [modal, setModal] = useState<null | 'add' | 'edit'>(null)
  const [editTarget, setEditTarget] = useState<Investor | null>(null)
  const [form, setForm] = useState<Omit<Investor, 'id'>>(EMPTY)

  const filtered = investors.filter((i) =>
    `${i.name} ${i.type} ${i.fund} ${i.country}`.toLowerCase().includes(search.toLowerCase())
  )

  const openAdd = () => { setForm(EMPTY); setEditTarget(null); setModal('add') }
  const openEdit = (i: Investor) => { const { id: _, ...rest } = i; setForm(rest); setEditTarget(i); setModal('edit') }

  const save = () => {
    if (modal === 'add') addInvestor(form)
    else if (modal === 'edit' && editTarget) updateInvestor(editTarget.id, form)
    setModal(null)
  }

  const totalCommitted = investors.reduce((s, i) => s + i.committed, 0)
  const totalNAV = investors.reduce((s, i) => s + i.nav, 0)
  const totalDistributed = investors.reduce((s, i) => s + i.distributed, 0)
  const avgIRR = investors.filter((i) => i.irr > 0).reduce((s, i) => s + i.irr, 0) / investors.filter((i) => i.irr > 0).length

  const field = (key: keyof typeof form, label: string, type = 'text', opts?: string[]) => (
    <div>
      <label className="text-slate-400 text-xs mb-1 block">{label}</label>
      {opts ? (
        <select
          className="w-full bg-[#161b26] border border-[#1e2433] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          value={String(form[key])}
          onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
        >
          {opts.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input
          type={type}
          className="w-full bg-[#161b26] border border-[#1e2433] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          value={type === 'number' ? String(form[key]) : (form[key] as string)}
          onChange={(e) => setForm((f) => ({ ...f, [key]: type === 'number' ? Number(e.target.value) : e.target.value }))}
        />
      )}
    </div>
  )

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            className="pl-9 pr-4 py-2 bg-[#0d1117] border border-[#1e2433] rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 w-64"
            placeholder="Search investors..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button onClick={openAdd} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded-lg transition-colors">
          <Plus size={15} /> Add Investor
        </button>
      </div>

      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Total Committed', value: fmt(totalCommitted) },
          { label: 'Portfolio NAV', value: fmt(totalNAV) },
          { label: 'Total Distributed', value: fmt(totalDistributed) },
          { label: 'Avg. Net IRR', value: `${avgIRR.toFixed(1)}%` },
        ].map((s) => (
          <div key={s.label} className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-4">
            <div className="text-slate-400 text-xs">{s.label}</div>
            <div className="text-xl font-bold text-white mt-1">{s.value}</div>
          </div>
        ))}
      </div>

      <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1e2433]">
              {['Investor', 'Fund', 'Committed', 'Called', 'NAV', 'Distributed', 'IRR', 'Multiple', 'Status', ''].map((h) => (
                <th key={h} className="text-left text-slate-500 text-xs font-medium px-4 py-3 whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((inv) => (
              <tr key={inv.id} className="border-b border-[#1e2433] hover:bg-white/2 transition-colors">
                <td className="px-4 py-3">
                  <div className="text-white font-medium">{inv.name}</div>
                  <div className="text-slate-500 text-xs">{inv.type} · {inv.country}</div>
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">{inv.fund}</td>
                <td className="px-4 py-3 text-white font-medium">{fmt(inv.committed)}</td>
                <td className="px-4 py-3">
                  <div className="text-white text-xs font-medium">{fmt(inv.called)}</div>
                  <div className="text-slate-500 text-[10px]">{inv.committed > 0 ? Math.round(inv.called / inv.committed * 100) : 0}%</div>
                </td>
                <td className="px-4 py-3 text-white font-medium">{fmt(inv.nav)}</td>
                <td className="px-4 py-3 text-emerald-400 font-medium">{fmt(inv.distributed)}</td>
                <td className="px-4 py-3">
                  <div className={`flex items-center gap-1 text-xs font-semibold ${inv.irr >= 20 ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {inv.irr > 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                    {inv.irr > 0 ? `${inv.irr.toFixed(1)}%` : '—'}
                  </div>
                </td>
                <td className="px-4 py-3 text-white text-xs">{inv.multiple > 0 ? `${inv.multiple.toFixed(2)}x` : '—'}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${STATUS_COLORS[inv.status]}`}>
                    {inv.status.charAt(0).toUpperCase() + inv.status.slice(1)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    <button onClick={() => openEdit(inv)} className="p-1.5 rounded hover:bg-white/5 text-slate-500 hover:text-blue-400 transition-colors"><Edit2 size={13} /></button>
                    <button onClick={() => deleteInvestor(inv.id)} className="p-1.5 rounded hover:bg-white/5 text-slate-500 hover:text-red-400 transition-colors"><Trash2 size={13} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[#0d1117] border border-[#1e2433] rounded-2xl w-[560px] max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-[#1e2433]">
              <h2 className="text-white font-semibold">{modal === 'add' ? 'New Investor' : `Edit — ${editTarget?.name}`}</h2>
              <button onClick={() => setModal(null)} className="text-slate-500 hover:text-white"><X size={18} /></button>
            </div>
            <div className="p-5 grid grid-cols-2 gap-4">
              {field('name', 'Name')}
              {field('type', 'Type', 'text', ['Institutional', 'Family Office', 'HNWI', 'Pension Fund', 'Endowment', 'Sovereign Wealth'])}
              {field('country', 'Country')}
              {field('fund', 'Fund', 'text', ['MYJ Fund I', 'MYJ Fund II', 'MYJ Fund III', 'MYJ Fund IV', 'MYJ Opportunities I'])}
              {field('committed', 'Committed (USD)', 'number')}
              {field('called', 'Called (USD)', 'number')}
              {field('distributed', 'Distributed (USD)', 'number')}
              {field('nav', 'NAV (USD)', 'number')}
              {field('irr', 'Net IRR (%)', 'number')}
              {field('multiple', 'TVPI Multiple', 'number')}
              {field('status', 'Status', 'text', ['active', 'committed', 'exited'])}
              {field('since', 'Since', 'date')}
            </div>
            <div className="flex justify-end gap-3 p-5 border-t border-[#1e2433]">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-slate-400 hover:text-white text-sm transition-colors">Cancel</button>
              <button onClick={save} className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
