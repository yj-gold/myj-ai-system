import { useState } from 'react'
import { useStore } from '../store/useStore'
import type { Client, ClientType, ClientStatus } from '../types'
import { Plus, Edit2, Trash2, Search, X, Building2, User } from 'lucide-react'
import { v4 as uuidv4 } from 'uuid'

const fmt = (n: number) =>
  n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : `$${(n / 1e3).toFixed(0)}K`

const STATUS_COLORS: Record<ClientStatus, string> = {
  active: 'bg-emerald-500/15 text-emerald-400',
  prospect: 'bg-blue-500/15 text-blue-400',
  onboarding: 'bg-amber-500/15 text-amber-400',
  inactive: 'bg-slate-500/15 text-slate-400',
}

const TYPE_LABELS: Record<ClientType, string> = {
  institutional: 'Institutional',
  hnwi: 'HNWI',
  family_office: 'Family Office',
  pension_fund: 'Pension Fund',
  endowment: 'Endowment',
}

const EMPTY: Omit<Client, 'id'> = {
  name: '', email: '', phone: '', type: 'institutional', aum: 0,
  status: 'prospect', since: '', advisor: '', country: '', notes: '', lastContact: '',
}

export default function Clients() {
  const { clients, addClient, updateClient, deleteClient } = useStore()
  const [search, setSearch] = useState('')
  const [modal, setModal] = useState<null | 'add' | 'edit'>(null)
  const [editTarget, setEditTarget] = useState<Client | null>(null)
  const [form, setForm] = useState<Omit<Client, 'id'>>(EMPTY)

  const filtered = clients.filter((c) =>
    `${c.name} ${c.email} ${c.country} ${c.advisor}`.toLowerCase().includes(search.toLowerCase())
  )

  const openAdd = () => { setForm(EMPTY); setEditTarget(null); setModal('add') }
  const openEdit = (c: Client) => { const { id: _, ...rest } = c; setForm(rest); setEditTarget(c); setModal('edit') }

  const save = () => {
    if (modal === 'add') addClient(form)
    else if (modal === 'edit' && editTarget) updateClient(editTarget.id, form)
    setModal(null)
  }

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
            placeholder="Search clients..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button onClick={openAdd} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded-lg transition-colors">
          <Plus size={15} /> Add Client
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Total Clients', value: clients.length },
          { label: 'Active', value: clients.filter((c) => c.status === 'active').length },
          { label: 'Total AUM', value: fmt(clients.reduce((s, c) => s + c.aum, 0)) },
        ].map((s) => (
          <div key={s.label} className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-4">
            <div className="text-slate-400 text-xs">{s.label}</div>
            <div className="text-2xl font-bold text-white mt-1">{s.value}</div>
          </div>
        ))}
      </div>

      <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1e2433]">
              {['Client', 'Type', 'AUM', 'Status', 'Advisor', 'Last Contact', ''].map((h) => (
                <th key={h} className="text-left text-slate-500 text-xs font-medium px-4 py-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => (
              <tr key={c.id} className="border-b border-[#1e2433] hover:bg-white/2 transition-colors">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400">
                      {c.type === 'hnwi' ? <User size={14} /> : <Building2 size={14} />}
                    </div>
                    <div>
                      <div className="text-white font-medium">{c.name}</div>
                      <div className="text-slate-500 text-xs">{c.email}</div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs">{TYPE_LABELS[c.type]}</td>
                <td className="px-4 py-3 text-white font-medium">{fmt(c.aum)}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${STATUS_COLORS[c.status]}`}>
                    {c.status.charAt(0).toUpperCase() + c.status.slice(1)}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs">{c.advisor}</td>
                <td className="px-4 py-3 text-slate-400 text-xs">{c.lastContact}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    <button onClick={() => openEdit(c)} className="p-1.5 rounded hover:bg-white/5 text-slate-500 hover:text-blue-400 transition-colors">
                      <Edit2 size={13} />
                    </button>
                    <button onClick={() => deleteClient(c.id)} className="p-1.5 rounded hover:bg-white/5 text-slate-500 hover:text-red-400 transition-colors">
                      <Trash2 size={13} />
                    </button>
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
              <h2 className="text-white font-semibold">{modal === 'add' ? 'New Client' : `Edit — ${editTarget?.name}`}</h2>
              <button onClick={() => setModal(null)} className="text-slate-500 hover:text-white"><X size={18} /></button>
            </div>
            <div className="p-5 grid grid-cols-2 gap-4">
              {field('name', 'Full Name')}
              {field('email', 'Email', 'email')}
              {field('phone', 'Phone')}
              {field('country', 'Country')}
              {field('type', 'Type', 'text', ['institutional', 'hnwi', 'family_office', 'pension_fund', 'endowment'])}
              {field('status', 'Status', 'text', ['active', 'prospect', 'onboarding', 'inactive'])}
              {field('aum', 'AUM (USD)', 'number')}
              {field('advisor', 'Advisor')}
              {field('since', 'Client Since', 'date')}
              {field('lastContact', 'Last Contact', 'date')}
              <div className="col-span-2">
                <label className="text-slate-400 text-xs mb-1 block">Notes</label>
                <textarea
                  rows={3}
                  className="w-full bg-[#161b26] border border-[#1e2433] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 resize-none"
                  value={form.notes}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                />
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
