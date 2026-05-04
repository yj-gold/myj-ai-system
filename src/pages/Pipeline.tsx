import { useState } from 'react'
import { useStore } from '../store/useStore'
import type { Deal, DealStage } from '../types'
import { Plus, X, ChevronRight, MapPin, User, Target } from 'lucide-react'

const fmt = (n: number) =>
  n >= 1e9 ? `$${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(0)}M` : `$${(n / 1e3).toFixed(0)}K`

const STAGES: { key: DealStage; label: string; color: string; bg: string }[] = [
  { key: 'prospect', label: 'Prospect', color: 'text-slate-400', bg: 'border-slate-600/30' },
  { key: 'screening', label: 'Screening', color: 'text-blue-400', bg: 'border-blue-600/30' },
  { key: 'due_diligence', label: 'Due Diligence', color: 'text-violet-400', bg: 'border-violet-600/30' },
  { key: 'term_sheet', label: 'Term Sheet', color: 'text-amber-400', bg: 'border-amber-600/30' },
  { key: 'closing', label: 'Closing', color: 'text-orange-400', bg: 'border-orange-600/30' },
  { key: 'portfolio', label: 'Portfolio', color: 'text-emerald-400', bg: 'border-emerald-600/30' },
  { key: 'passed', label: 'Passed', color: 'text-red-400', bg: 'border-red-600/30' },
]

const SECTOR_COLORS: Record<string, string> = {
  Technology: 'bg-blue-500/15 text-blue-400',
  CleanTech: 'bg-emerald-500/15 text-emerald-400',
  Healthcare: 'bg-red-500/15 text-red-400',
  FinTech: 'bg-violet-500/15 text-violet-400',
  AgriTech: 'bg-amber-500/15 text-amber-400',
  PropTech: 'bg-orange-500/15 text-orange-400',
  Cybersecurity: 'bg-pink-500/15 text-pink-400',
}

const EMPTY: Omit<Deal, 'id'> = {
  company: '', sector: 'Technology', stage: 'prospect', amount: 0,
  manager: '', date: '', description: '', irr_target: 0, country: '',
}

export default function Pipeline() {
  const { deals, addDeal, updateDeal, deleteDeal, moveDeal } = useStore()
  const [modal, setModal] = useState<null | 'add' | 'edit'>(null)
  const [editTarget, setEditTarget] = useState<Deal | null>(null)
  const [form, setForm] = useState<Omit<Deal, 'id'>>(EMPTY)
  const [drag, setDrag] = useState<string | null>(null)

  const openAdd = () => { setForm(EMPTY); setEditTarget(null); setModal('add') }
  const openEdit = (d: Deal) => { const { id: _, ...rest } = d; setForm(rest); setEditTarget(d); setModal('edit') }
  const save = () => {
    if (modal === 'add') addDeal(form)
    else if (modal === 'edit' && editTarget) updateDeal(editTarget.id, form)
    setModal(null)
  }

  const totalActive = deals.filter((d) => !['passed', 'portfolio'].includes(d.stage)).reduce((s, d) => s + d.amount, 0)
  const totalPortfolio = deals.filter((d) => d.stage === 'portfolio').reduce((s, d) => s + d.amount, 0)

  const field = (key: keyof typeof form, label: string, type = 'text', opts?: string[]) => (
    <div>
      <label className="text-slate-400 text-xs mb-1 block">{label}</label>
      {opts ? (
        <select className="w-full bg-[#161b26] border border-[#1e2433] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          value={String(form[key])} onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}>
          {opts.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input type={type}
          className="w-full bg-[#161b26] border border-[#1e2433] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          value={type === 'number' ? String(form[key]) : (form[key] as string)}
          onChange={(e) => setForm((f) => ({ ...f, [key]: type === 'number' ? Number(e.target.value) : e.target.value }))} />
      )}
    </div>
  )

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 text-sm">
          <div className="text-slate-400">Active Pipeline: <span className="text-white font-semibold">{fmt(totalActive)}</span></div>
          <div className="text-slate-400">Portfolio: <span className="text-emerald-400 font-semibold">{fmt(totalPortfolio)}</span></div>
          <div className="text-slate-400">Total Deals: <span className="text-white font-semibold">{deals.length}</span></div>
        </div>
        <button onClick={openAdd} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded-lg transition-colors">
          <Plus size={15} /> Add Deal
        </button>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-2">
        {STAGES.map((stage) => {
          const stageDeals = deals.filter((d) => d.stage === stage.key)
          const stageTotal = stageDeals.reduce((s, d) => s + d.amount, 0)
          return (
            <div
              key={stage.key}
              className={`flex-shrink-0 w-52 bg-[#0d1117] border rounded-xl overflow-hidden ${stage.bg}`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => { if (drag) moveDeal(drag, stage.key); setDrag(null) }}
            >
              <div className={`px-3 py-2.5 border-b border-[#1e2433] flex items-center justify-between`}>
                <span className={`text-xs font-semibold ${stage.color}`}>{stage.label}</span>
                <div className="flex items-center gap-2">
                  <span className="text-slate-500 text-[10px]">{fmt(stageTotal)}</span>
                  <span className="text-xs text-slate-500 bg-[#161b26] rounded-full w-5 h-5 flex items-center justify-center">{stageDeals.length}</span>
                </div>
              </div>
              <div className="p-2 space-y-2 min-h-[200px]">
                {stageDeals.map((d) => (
                  <div
                    key={d.id}
                    draggable
                    onDragStart={() => setDrag(d.id)}
                    className="bg-[#161b26] border border-[#1e2433] rounded-lg p-3 cursor-grab active:cursor-grabbing hover:border-blue-500/30 transition-colors group"
                  >
                    <div className="flex items-start justify-between gap-1 mb-2">
                      <div className="text-white text-xs font-semibold leading-tight">{d.company}</div>
                      <button onClick={() => openEdit(d)} className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-blue-400 transition-all shrink-0">
                        <ChevronRight size={12} />
                      </button>
                    </div>
                    <div className={`text-[10px] px-1.5 py-0.5 rounded inline-block mb-2 ${SECTOR_COLORS[d.sector] ?? 'bg-slate-500/15 text-slate-400'}`}>{d.sector}</div>
                    <div className="text-emerald-400 text-xs font-semibold">{fmt(d.amount)}</div>
                    <div className="flex items-center justify-between mt-2 text-[10px] text-slate-500">
                      <div className="flex items-center gap-1"><User size={9} />{d.manager.split(' ')[0]}</div>
                      <div className="flex items-center gap-1"><Target size={9} />{d.irr_target}% IRR</div>
                      <div className="flex items-center gap-1"><MapPin size={9} />{d.country}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {modal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[#0d1117] border border-[#1e2433] rounded-2xl w-[540px] max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-[#1e2433]">
              <h2 className="text-white font-semibold">{modal === 'add' ? 'New Deal' : `Edit — ${editTarget?.company}`}</h2>
              <button onClick={() => setModal(null)} className="text-slate-500 hover:text-white"><X size={18} /></button>
            </div>
            <div className="p-5 grid grid-cols-2 gap-4">
              {field('company', 'Company Name')}
              {field('sector', 'Sector', 'text', ['Technology', 'CleanTech', 'Healthcare', 'FinTech', 'AgriTech', 'PropTech', 'Cybersecurity', 'Consumer', 'Industrials'])}
              {field('country', 'Country')}
              {field('stage', 'Stage', 'text', STAGES.map((s) => s.key))}
              {field('amount', 'Investment Amount (USD)', 'number')}
              {field('irr_target', 'IRR Target (%)', 'number')}
              {field('manager', 'Manager')}
              {field('date', 'Date', 'date')}
              <div className="col-span-2">
                <label className="text-slate-400 text-xs mb-1 block">Description</label>
                <textarea rows={3} className="w-full bg-[#161b26] border border-[#1e2433] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 resize-none"
                  value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
              </div>
            </div>
            {modal === 'edit' && editTarget && (
              <div className="px-5 pb-3">
                <button onClick={() => { deleteDeal(editTarget.id); setModal(null) }} className="text-xs text-red-400 hover:text-red-300 transition-colors">Delete deal</button>
              </div>
            )}
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
