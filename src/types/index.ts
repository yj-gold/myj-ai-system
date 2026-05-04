export type ClientType = 'institutional' | 'hnwi' | 'family_office' | 'pension_fund' | 'endowment'
export type ClientStatus = 'active' | 'prospect' | 'inactive' | 'onboarding'

export interface Client {
  id: string
  name: string
  email: string
  phone: string
  type: ClientType
  aum: number
  status: ClientStatus
  since: string
  advisor: string
  country: string
  notes: string
  lastContact: string
}

export type InvestorStatus = 'active' | 'exited' | 'committed'

export interface Investor {
  id: string
  name: string
  type: string
  committed: number
  called: number
  distributed: number
  nav: number
  irr: number
  multiple: number
  status: InvestorStatus
  fund: string
  since: string
  country: string
}

export type DealStage = 'prospect' | 'screening' | 'due_diligence' | 'term_sheet' | 'closing' | 'portfolio' | 'passed'

export interface Deal {
  id: string
  company: string
  sector: string
  stage: DealStage
  amount: number
  manager: string
  date: string
  description: string
  irr_target: number
  country: string
}

export interface Position {
  id: string
  ticker: string
  name: string
  side: 'long' | 'short'
  quantity: number
  entryPrice: number
  currentPrice: number
  marketValue: number
  pnl: number
  pnlPct: number
  sector: string
  strategy: string
  weight: number
}

export interface Trade {
  id: string
  date: string
  ticker: string
  name: string
  side: 'buy' | 'sell'
  quantity: number
  price: number
  value: number
  status: 'filled' | 'pending' | 'cancelled'
  strategy: string
}

export type ComplianceCategory = 'kyc' | 'aml' | 'regulatory' | 'reporting' | 'internal'
export type ComplianceStatus = 'compliant' | 'pending' | 'overdue' | 'review'
export type Priority = 'high' | 'medium' | 'low'

export interface ComplianceItem {
  id: string
  title: string
  category: ComplianceCategory
  status: ComplianceStatus
  dueDate: string
  assignee: string
  priority: Priority
  description: string
}

export interface FundingRound {
  id: string
  fund: string
  target: number
  raised: number
  status: 'open' | 'closed' | 'upcoming'
  closeDate: string
  investors: number
  type: string
  vintage: string
}

export interface MonthlyPoint {
  month: string
  value: number
  value2?: number
}

export interface SyncSource {
  id: string
  name: string
  type: 'broker' | 'custodian' | 'data' | 'accounting' | 'crm'
  status: 'connected' | 'disconnected' | 'syncing' | 'error'
  lastSync: string
  records: number
  icon: string
}
