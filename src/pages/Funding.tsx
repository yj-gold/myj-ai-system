import { useState } from 'react'
import { useStore } from '../store/useStore'
import type { FundingRound } from '../types'
import { Plus, Edit2, X, Landmark, ArrowUpRight } from 'lucide-react'

const fmt = (n: number) =>
  n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : `$${(n / 1e3).toFixed(0)}K`

const STATUS_COLORS = {
  open: 'bg-emerald-500/15 text-emerald-400',
  closed: 'bg-slate-500/15 text-slate-400',
  upcoming: 'bg-blue-500/15 text-blue-400',
}

const EMPTY: Omit<FundingRound, 'id'> = {
  fund: '', target: 0, raised: 0, status: 'upcoming', closeDate: '', investors: 0, type: 'Growth Equity', vintage: '',
}

export default function Funding() {
  const { fundingRounds, addFundingRound, updateFundingRound } = useStore()
  const [modal, setModal] = useState<null | 'add' | 'edit'>(null)
  const [editTarget, setEditTarget] = useState<FundingRound | null>(null)
  const [form, setForm] = useState<Omit<FundingRound, 'id'>>(EMPTY)

  const openAdd = () => { setForm(EMPTY); setEditTarget(null); setModal('add') }
  const openEdit = (f: FundingRound) => { const { id: _, ...rest } = f; setForm(rest); setEditTarget(f); setModal('edit') }
  const save = () => {
    if (modal === 'add') addFundingRound(form)
    else if (modal === 'edit' && editTarget) updateFundingRound(editTarget.id, form)
    setModal(null)
  }

  const totalRaised = fundingRounds.reduce((s, f) => s + f.raised, 0)
  const totalTarget = fundingRounds.reduce((s, f) => s + f.target, 0)
  const openFunds = fundingRounds.filter((f) => f.status === 'open')

  const field = (key: keyof typeof form, label: string, type = 'text', opts?: string[]) => (
    <div>
      <label className="text-slate-400 text-xs mb-1 block">{label}</label>
      {opts ? (
        <select className="w-full bg-[#161b26] border border-[#1e2433] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          value={String(form[key])} onChange={(e) => setForm((f2) => ({ ...f2, [key]: e.target.value }))}>
          {opts.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input type={type} className="w-full bg-[#161b26] border border-[#1e2433] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          value={type === 'number' ? String(form[key]) : (form[key] as string)}
          onChange={(e) => setForm((f2) => ({ ...f2, [key]: type === 'number' ? Number(e.target.value) : e.target.value }))} />
      )}
    </div>
  )

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 text-sm text-slate-400">
          <span>Total Raised: <span className="text-white font-semibold">{fmt(totalRaised)}</span></span>
          <span>Total Target: <span className="text-white font-semibold">{fmt(totalTarget)}</span></span>
        </div>
        <button onClick={openAdd} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded-lg transition-colors">
          <Plus size={15} /> New Fund
        </button>
      </div>

      {openFunds.length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          {openFunds.map((f) => {
            const pct = (f.raised / f.target) * 100
            const remaining = f.target - f.raised
            return (
              <div key={f.id} className="bg-[#0d1117] border border-emerald-500/20 rounded-xl p-5">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-medium">Open</span>
                      <span className="text-xs text-slate-500">{f.vintage} Vintage</span>
                    </div>
                    <div className="text-white font-bold text-lg">{f.fund}</div>
                    <div className="text-slate-500 text-xs">{f.type}</div>
                  </div>
                  <button onClick={() => openEdit(f)} className="p-2 rounded-lg hover:bg-white/5 text-slate-500 hover:text-blue-400 transition-colors">
                    <Edit2 size={14} />
                  </button>
                </div>
                <div className="flex items-end justify-between mb-2">
                  <div>
                    <div className="text-slate-400 text-xs">Raised</div>
                    <div className="text-2xl font-bold text-white">{fmt(f.raised)}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-slate-400 text-xs">Target</div>
                    <div className="text-lg font-semibold text-slate-300">{fmt(f.target)}</div>
                  </div>
                </div>
                <div className="h-2 bg-[#1e2433] rounded-full overflow-hidden mb-3">
                  <div className="h-full bg-emerald-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
                </div>
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="text-emerald-400 font-semibold">{pct.toFixed(1)}% funded</span>
                  <span>{fmt(remaining)} remaining</span>
                  <span>{f.investors} investors · Close {f.closeDate}</span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-[#1e2433]">
          <div className="text-white font-semibold text-sm">All Funds</div>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1e2433]">
              {['Fund', 'Type', 'Vintage', 'Target', 'Raised', 'Progress', 'Investors', 'Close Date', 'Status', ''].map((h) => (
                <th key={h} className="text-left text-slate-500 text-xs font-medium px-4 py-3 whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {fundingRounds.map((f) => {
              const pct = f.target > 0 ? (f.raised / f.target) * 100 : 0
              return (
                <tr key={f.id} className="border-b border-[#1e2433] hover:bg-white/2 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-blue-500/10 flex items-center justify-center">
                        <Landmark size={13} className="text-blue-400" />
                      </div>
                      <span className="text-white font-medium text-xs">{f.fund}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{f.type}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{f.vintage}</td>
                  <td className="px-4 py-3 text-white font-medium">{fmt(f.target)}</td>
                  <td className="px-4 py-3 text-emerald-400 font-medium">{fmt(f.raised)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-1.5 bg-[#1e2433] rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs text-slate-400">{pct.toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{f.investors}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{f.closeDate}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${STATUS_COLORS[f.status]}`}>
                      {f.status.charAt(0).toUpperCase() + f.status.slice(1)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => openEdit(f)} className="p-1.5 rounded hover:bg-white/5 text-slate-500 hover:text-blue-400 transition-colors"><Edit2 size={13} /></button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {modal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[#0d1117] border border-[#1e2433] rounded-2xl w-[500px] max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-[#1e2433]">
              <h2 className="text-white font-semibold">{modal === 'add' ? 'New Fund' : `Edit — ${editTarget?.fund}`}</h2>
              <button onClick={() => setModal(null)} className="text-slate-500 hover:text-white"><X size={18} /></button>
            </div>
            <div className="p-5 grid grid-cols-2 gap-4">
              {field('fund', 'Fund Name')}
              {field('type', 'Strategy', 'text', ['Private Equity', 'Growth Equity', 'Venture Capital', 'Hedge Fund', 'Opportunistic', 'Credit'])}
              {field('vintage', 'Vintage Year')}
              {field('status', 'Status', 'text', ['upcoming', 'open', 'closed'])}
              {field('target', 'Target Size (USD)', 'number')}
              {field('raised', 'Amount Raised (USD)', 'number')}
              {field('investors', 'Number of Investors', 'number')}
              {field('closeDate', 'Close Date', 'date')}
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
