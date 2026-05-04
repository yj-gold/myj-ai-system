import { useState } from 'react'
import { useStore } from '../store/useStore'
import type { ComplianceItem, ComplianceCategory, ComplianceStatus, Priority } from '../types'
import { Plus, Edit2, Trash2, X, ShieldCheck, AlertTriangle, Clock, CheckCircle2 } from 'lucide-react'

const STATUS_CONFIG: Record<ComplianceStatus, { label: string; color: string; icon: typeof CheckCircle2 }> = {
  compliant: { label: 'Compliant', color: 'bg-emerald-500/15 text-emerald-400', icon: CheckCircle2 },
  pending: { label: 'Pending', color: 'bg-amber-500/15 text-amber-400', icon: Clock },
  overdue: { label: 'Overdue', color: 'bg-red-500/15 text-red-400', icon: AlertTriangle },
  review: { label: 'In Review', color: 'bg-blue-500/15 text-blue-400', icon: Clock },
}

const CATEGORY_COLORS: Record<ComplianceCategory, string> = {
  kyc: 'bg-violet-500/15 text-violet-400',
  aml: 'bg-orange-500/15 text-orange-400',
  regulatory: 'bg-blue-500/15 text-blue-400',
  reporting: 'bg-teal-500/15 text-teal-400',
  internal: 'bg-slate-500/15 text-slate-400',
}

const PRIORITY_COLORS: Record<Priority, string> = {
  high: 'text-red-400',
  medium: 'text-amber-400',
  low: 'text-slate-400',
}

const EMPTY: Omit<ComplianceItem, 'id'> = {
  title: '', category: 'regulatory', status: 'pending', dueDate: '',
  assignee: '', priority: 'medium', description: '',
}

export default function Compliance() {
  const { complianceItems, addComplianceItem, updateComplianceItem, deleteComplianceItem } = useStore()
  const [filter, setFilter] = useState<ComplianceStatus | 'all'>('all')
  const [modal, setModal] = useState<null | 'add' | 'edit'>(null)
  const [editTarget, setEditTarget] = useState<ComplianceItem | null>(null)
  const [form, setForm] = useState<Omit<ComplianceItem, 'id'>>(EMPTY)

  const filtered = complianceItems.filter((c) => filter === 'all' || c.status === filter)

  const openAdd = () => { setForm(EMPTY); setEditTarget(null); setModal('add') }
  const openEdit = (c: ComplianceItem) => { const { id: _, ...rest } = c; setForm(rest); setEditTarget(c); setModal('edit') }
  const save = () => {
    if (modal === 'add') addComplianceItem(form)
    else if (modal === 'edit' && editTarget) updateComplianceItem(editTarget.id, form)
    setModal(null)
  }

  const counts = {
    compliant: complianceItems.filter((c) => c.status === 'compliant').length,
    pending: complianceItems.filter((c) => c.status === 'pending').length,
    overdue: complianceItems.filter((c) => c.status === 'overdue').length,
    review: complianceItems.filter((c) => c.status === 'review').length,
  }

  const field = (key: keyof typeof form, label: string, type = 'text', opts?: string[]) => (
    <div>
      <label className="text-slate-400 text-xs mb-1 block">{label}</label>
      {opts ? (
        <select className="w-full bg-[#161b26] border border-[#1e2433] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          value={String(form[key])} onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}>
          {opts.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input type={type} className="w-full bg-[#161b26] border border-[#1e2433] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          value={form[key] as string} onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))} />
      )}
    </div>
  )

  const score = Math.round((counts.compliant / complianceItems.length) * 100)

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {(['all', 'compliant', 'pending', 'overdue', 'review'] as const).map((s) => (
            <button key={s} onClick={() => setFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filter === s ? 'bg-blue-600 text-white' : 'bg-[#0d1117] border border-[#1e2433] text-slate-400 hover:text-white'}`}>
              {s === 'all' ? 'All' : STATUS_CONFIG[s as ComplianceStatus].label}
              {s !== 'all' && <span className="ml-1.5 text-[10px] opacity-70">{counts[s as ComplianceStatus]}</span>}
            </button>
          ))}
        </div>
        <button onClick={openAdd} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded-lg transition-colors">
          <Plus size={15} /> Add Item
        </button>
      </div>

      <div className="grid grid-cols-5 gap-4">
        <div className="col-span-1 bg-[#0d1117] border border-[#1e2433] rounded-xl p-5 flex flex-col items-center justify-center">
          <div className="relative w-20 h-20 mb-3">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="15.9" fill="none" stroke="#1e2433" strokeWidth="3" />
              <circle cx="18" cy="18" r="15.9" fill="none" stroke={score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444'}
                strokeWidth="3" strokeDasharray={`${score} 100`} strokeLinecap="round" />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xl font-bold text-white">{score}%</span>
            </div>
          </div>
          <div className="text-slate-400 text-xs text-center">Compliance Score</div>
          <div className={`text-xs mt-1 font-medium ${score >= 80 ? 'text-emerald-400' : score >= 60 ? 'text-amber-400' : 'text-red-400'}`}>
            {score >= 80 ? 'Good' : score >= 60 ? 'Needs Attention' : 'Critical'}
          </div>
        </div>
        {Object.entries(counts).map(([status, count]) => {
          const cfg = STATUS_CONFIG[status as ComplianceStatus]
          const Icon = cfg.icon
          return (
            <div key={status} className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Icon size={14} className={cfg.color.split(' ')[1]} />
                <span className="text-slate-400 text-xs">{cfg.label}</span>
              </div>
              <div className="text-3xl font-bold text-white">{count}</div>
            </div>
          )
        })}
      </div>

      <div className="space-y-2">
        {filtered.map((item) => {
          const cfg = STATUS_CONFIG[item.status]
          const Icon = cfg.icon
          return (
            <div key={item.id} className={`bg-[#0d1117] border rounded-xl p-4 flex items-start gap-4 ${item.status === 'overdue' ? 'border-red-500/20' : 'border-[#1e2433]'}`}>
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${cfg.color}`}>
                <Icon size={15} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start gap-3 flex-wrap">
                  <span className="text-white text-sm font-medium">{item.title}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${CATEGORY_COLORS[item.category]}`}>{item.category.toUpperCase()}</span>
                  <span className={`text-[10px] font-medium ${PRIORITY_COLORS[item.priority]}`}>{item.priority.toUpperCase()} PRIORITY</span>
                </div>
                <div className="text-slate-500 text-xs mt-1">{item.description}</div>
                <div className="flex items-center gap-4 mt-2 text-[10px] text-slate-500">
                  <span>Due: <span className={item.status === 'overdue' ? 'text-red-400' : 'text-slate-300'}>{item.dueDate}</span></span>
                  <span>Assignee: <span className="text-slate-300">{item.assignee}</span></span>
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${cfg.color}`}>{cfg.label}</span>
                <button onClick={() => openEdit(item)} className="p-1.5 rounded hover:bg-white/5 text-slate-500 hover:text-blue-400 transition-colors ml-2"><Edit2 size={13} /></button>
                <button onClick={() => deleteComplianceItem(item.id)} className="p-1.5 rounded hover:bg-white/5 text-slate-500 hover:text-red-400 transition-colors"><Trash2 size={13} /></button>
              </div>
            </div>
          )
        })}
      </div>

      {modal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[#0d1117] border border-[#1e2433] rounded-2xl w-[540px] max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-[#1e2433]">
              <h2 className="text-white font-semibold">{modal === 'add' ? 'New Compliance Item' : `Edit — ${editTarget?.title.slice(0, 30)}`}</h2>
              <button onClick={() => setModal(null)} className="text-slate-500 hover:text-white"><X size={18} /></button>
            </div>
            <div className="p-5 grid grid-cols-2 gap-4">
              <div className="col-span-2">{field('title', 'Title')}</div>
              {field('category', 'Category', 'text', ['kyc', 'aml', 'regulatory', 'reporting', 'internal'])}
              {field('status', 'Status', 'text', ['pending', 'compliant', 'overdue', 'review'])}
              {field('priority', 'Priority', 'text', ['high', 'medium', 'low'])}
              {field('assignee', 'Assignee')}
              {field('dueDate', 'Due Date', 'date')}
              <div className="col-span-2">
                <label className="text-slate-400 text-xs mb-1 block">Description</label>
                <textarea rows={3} className="w-full bg-[#161b26] border border-[#1e2433] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 resize-none"
                  value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
              </div>
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
