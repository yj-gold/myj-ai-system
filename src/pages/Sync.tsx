import { useStore } from '../store/useStore'
import type { SyncSource } from '../types'
import {
  TrendingUp, Shield, BarChart2, BookOpen, Users, FileText,
  RefreshCw, CheckCircle2, AlertCircle, XCircle, Loader,
  Wifi, WifiOff, type LucideIcon,
} from 'lucide-react'

const ICON_MAP: Record<string, LucideIcon> = {
  TrendingUp, Shield, BarChart2, BookOpen, Users, FileText,
}

const TYPE_COLORS: Record<SyncSource['type'], string> = {
  broker: 'bg-blue-500/10 text-blue-400',
  custodian: 'bg-violet-500/10 text-violet-400',
  data: 'bg-emerald-500/10 text-emerald-400',
  accounting: 'bg-amber-500/10 text-amber-400',
  crm: 'bg-orange-500/10 text-orange-400',
}

const STATUS_CONFIG = {
  connected: { label: 'Connected', color: 'text-emerald-400', icon: CheckCircle2, dot: 'bg-emerald-400' },
  disconnected: { label: 'Disconnected', color: 'text-slate-400', icon: WifiOff, dot: 'bg-slate-500' },
  syncing: { label: 'Syncing', color: 'text-blue-400', icon: Loader, dot: 'bg-blue-400' },
  error: { label: 'Error', color: 'text-red-400', icon: AlertCircle, dot: 'bg-red-400' },
}

export default function Sync() {
  const { syncSources, updateSyncSource } = useStore()

  const connected = syncSources.filter((s) => s.status === 'connected').length
  const syncing = syncSources.filter((s) => s.status === 'syncing').length
  const errors = syncSources.filter((s) => s.status === 'error').length
  const totalRecords = syncSources.reduce((s, src) => s + src.records, 0)

  const toggleSource = (src: SyncSource) => {
    if (src.status === 'disconnected') updateSyncSource(src.id, { status: 'connected', lastSync: new Date().toISOString() })
    else if (src.status === 'connected') updateSyncSource(src.id, { status: 'disconnected' })
  }

  const syncNow = (src: SyncSource) => {
    updateSyncSource(src.id, { status: 'syncing' })
    setTimeout(() => updateSyncSource(src.id, { status: 'connected', lastSync: new Date().toISOString() }), 2000)
  }

  const byType = syncSources.reduce((acc, src) => {
    if (!acc[src.type]) acc[src.type] = []
    acc[src.type].push(src)
    return acc
  }, {} as Record<string, SyncSource[]>)

  const TYPE_LABELS: Record<string, string> = {
    broker: 'Prime Brokers', custodian: 'Custodians', data: 'Market Data',
    accounting: 'Accounting', crm: 'CRM & Documents',
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Connected', value: connected, color: 'text-emerald-400', icon: Wifi },
          { label: 'Syncing', value: syncing, color: 'text-blue-400', icon: RefreshCw },
          { label: 'Errors', value: errors, color: 'text-red-400', icon: XCircle },
          { label: 'Total Records', value: totalRecords.toLocaleString(), color: 'text-white', icon: BarChart2 },
        ].map((k) => {
          const Icon = k.icon
          return (
            <div key={k.label} className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-400 text-xs">{k.label}</span>
                <Icon size={15} className={k.color} />
              </div>
              <div className={`text-2xl font-bold ${k.color}`}>{k.value}</div>
            </div>
          )
        })}
      </div>

      {Object.entries(byType).map(([type, sources]) => (
        <div key={type} className="bg-[#0d1117] border border-[#1e2433] rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-[#1e2433] flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded font-medium ${TYPE_COLORS[type as SyncSource['type']]}`}>{type.toUpperCase()}</span>
            <span className="text-white font-semibold text-sm">{TYPE_LABELS[type]}</span>
          </div>
          <div className="divide-y divide-[#1e2433]">
            {sources.map((src) => {
              const cfg = STATUS_CONFIG[src.status]
              const StatusIcon = cfg.icon
              const Icon = ICON_MAP[src.icon] ?? BarChart2
              const lastSyncDate = new Date(src.lastSync)
              const minutesAgo = Math.floor((Date.now() - lastSyncDate.getTime()) / 60000)
              const syncLabel = minutesAgo < 60
                ? `${minutesAgo}m ago`
                : minutesAgo < 1440
                ? `${Math.floor(minutesAgo / 60)}h ago`
                : lastSyncDate.toLocaleDateString()

              return (
                <div key={src.id} className="px-5 py-4 flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${TYPE_COLORS[src.type]}`}>
                    <Icon size={18} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-medium text-sm">{src.name}</span>
                      <div className="flex items-center gap-1">
                        <div className={`w-1.5 h-1.5 rounded-full ${cfg.dot} ${src.status === 'syncing' ? 'animate-pulse' : ''}`} />
                        <span className={`text-xs ${cfg.color}`}>{cfg.label}</span>
                      </div>
                    </div>
                    <div className="text-slate-500 text-xs mt-0.5">
                      Last sync: {syncLabel} · {src.records.toLocaleString()} records
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {src.status === 'error' && (
                      <div className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 border border-red-500/20 rounded-lg">
                        <AlertCircle size={12} className="text-red-400" />
                        <span className="text-red-400 text-xs">Auth failed</span>
                      </div>
                    )}
                    <button
                      onClick={() => syncNow(src)}
                      disabled={src.status === 'disconnected' || src.status === 'syncing'}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-[#161b26] border border-[#1e2433] rounded-lg text-slate-400 hover:text-white text-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <RefreshCw size={11} className={src.status === 'syncing' ? 'animate-spin' : ''} />
                      {src.status === 'syncing' ? 'Syncing...' : 'Sync Now'}
                    </button>
                    <button
                      onClick={() => toggleSource(src)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                        src.status === 'disconnected'
                          ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20'
                          : 'bg-[#161b26] border-[#1e2433] text-slate-400 hover:text-red-400 hover:border-red-500/20'
                      }`}
                    >
                      {src.status === 'disconnected' ? 'Connect' : 'Disconnect'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}

      <div className="bg-[#0d1117] border border-[#1e2433] rounded-xl p-5">
        <div className="text-white font-semibold text-sm mb-4">Sync Schedule</div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Real-time', desc: 'Positions, trades, prices', sources: 'IBKR, Goldman', color: 'emerald' },
            { label: 'Every 15min', desc: 'Market data, analytics', sources: 'Bloomberg, Refinitiv', color: 'blue' },
            { label: 'Daily (6am)', desc: 'Accounting, custody, CRM', sources: 'Geneva, BNY', color: 'violet' },
          ].map((s) => (
            <div key={s.label} className="bg-[#161b26] border border-[#1e2433] rounded-lg p-4">
              <div className={`text-xs font-semibold mb-1 text-${s.color}-400`}>{s.label}</div>
              <div className="text-white text-sm font-medium">{s.desc}</div>
              <div className="text-slate-500 text-xs mt-1">{s.sources}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
