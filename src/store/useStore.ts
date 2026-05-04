import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'
import type { Client, Investor, Deal, DealStage, ComplianceItem, FundingRound, SyncSource, Position, Trade } from '../types'
import {
  clients as initClients,
  investors as initInvestors,
  deals as initDeals,
  positions as initPositions,
  recentTrades as initTrades,
  complianceItems as initCompliance,
  fundingRounds as initFunding,
  syncSources as initSync,
} from '../data/mockData'

interface Store {
  clients: Client[]
  addClient: (c: Omit<Client, 'id'>) => void
  updateClient: (id: string, u: Partial<Client>) => void
  deleteClient: (id: string) => void

  investors: Investor[]
  addInvestor: (i: Omit<Investor, 'id'>) => void
  updateInvestor: (id: string, u: Partial<Investor>) => void
  deleteInvestor: (id: string) => void

  deals: Deal[]
  addDeal: (d: Omit<Deal, 'id'>) => void
  updateDeal: (id: string, u: Partial<Deal>) => void
  deleteDeal: (id: string) => void
  moveDeal: (id: string, stage: DealStage) => void

  positions: Position[]
  updatePosition: (id: string, u: Partial<Position>) => void

  trades: Trade[]

  complianceItems: ComplianceItem[]
  addComplianceItem: (c: Omit<ComplianceItem, 'id'>) => void
  updateComplianceItem: (id: string, u: Partial<ComplianceItem>) => void
  deleteComplianceItem: (id: string) => void

  fundingRounds: FundingRound[]
  addFundingRound: (f: Omit<FundingRound, 'id'>) => void
  updateFundingRound: (id: string, u: Partial<FundingRound>) => void

  syncSources: SyncSource[]
  updateSyncSource: (id: string, u: Partial<SyncSource>) => void
}

export const useStore = create<Store>((set) => ({
  clients: initClients,
  addClient: (c) => set((s) => ({ clients: [...s.clients, { ...c, id: uuidv4() }] })),
  updateClient: (id, u) => set((s) => ({ clients: s.clients.map((c) => c.id === id ? { ...c, ...u } : c) })),
  deleteClient: (id) => set((s) => ({ clients: s.clients.filter((c) => c.id !== id) })),

  investors: initInvestors,
  addInvestor: (i) => set((s) => ({ investors: [...s.investors, { ...i, id: uuidv4() }] })),
  updateInvestor: (id, u) => set((s) => ({ investors: s.investors.map((i) => i.id === id ? { ...i, ...u } : i) })),
  deleteInvestor: (id) => set((s) => ({ investors: s.investors.filter((i) => i.id !== id) })),

  deals: initDeals,
  addDeal: (d) => set((s) => ({ deals: [...s.deals, { ...d, id: uuidv4() }] })),
  updateDeal: (id, u) => set((s) => ({ deals: s.deals.map((d) => d.id === id ? { ...d, ...u } : d) })),
  deleteDeal: (id) => set((s) => ({ deals: s.deals.filter((d) => d.id !== id) })),
  moveDeal: (id, stage) => set((s) => ({ deals: s.deals.map((d) => d.id === id ? { ...d, stage } : d) })),

  positions: initPositions,
  updatePosition: (id, u) => set((s) => ({ positions: s.positions.map((p) => p.id === id ? { ...p, ...u } : p) })),

  trades: initTrades,

  complianceItems: initCompliance,
  addComplianceItem: (c) => set((s) => ({ complianceItems: [...s.complianceItems, { ...c, id: uuidv4() }] })),
  updateComplianceItem: (id, u) => set((s) => ({ complianceItems: s.complianceItems.map((c) => c.id === id ? { ...c, ...u } : c) })),
  deleteComplianceItem: (id) => set((s) => ({ complianceItems: s.complianceItems.filter((c) => c.id !== id) })),

  fundingRounds: initFunding,
  addFundingRound: (f) => set((s) => ({ fundingRounds: [...s.fundingRounds, { ...f, id: uuidv4() }] })),
  updateFundingRound: (id, u) => set((s) => ({ fundingRounds: s.fundingRounds.map((f) => f.id === id ? { ...f, ...u } : f) })),

  syncSources: initSync,
  updateSyncSource: (id, u) => set((s) => ({ syncSources: s.syncSources.map((s2) => s2.id === id ? { ...s2, ...u } : s2) })),
}))
