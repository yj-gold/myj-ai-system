import type { Client, Investor, Deal, Position, Trade, ComplianceItem, FundingRound, MonthlyPoint, SyncSource } from '../types'

export const clients: Client[] = [
  { id: '1', name: 'BlackRock Pension Trust', email: 'contact@blackrock-trust.com', phone: '+1 212 555 0101', type: 'pension_fund', aum: 450000000, status: 'active', since: '2019-03-15', advisor: 'Marc Lefebvre', country: 'USA', notes: 'Long-term LP, committed to Fund III', lastContact: '2024-04-28' },
  { id: '2', name: 'Al-Faisal Family Office', email: 'invest@alfaisal.ae', phone: '+971 4 555 0202', type: 'family_office', aum: 280000000, status: 'active', since: '2020-07-22', advisor: 'Sophie Chen', country: 'UAE', notes: 'Interested in Fund IV close', lastContact: '2024-04-30' },
  { id: '3', name: 'Zurich Endowment Capital', email: 'capital@zurich-endow.ch', phone: '+41 44 555 0303', type: 'endowment', aum: 175000000, status: 'active', since: '2021-01-10', advisor: 'Marc Lefebvre', country: 'Switzerland', notes: 'ESG-focused mandate', lastContact: '2024-04-15' },
  { id: '4', name: 'Nexus Institutional LP', email: 'lp@nexus-inst.com', phone: '+44 20 555 0404', type: 'institutional', aum: 620000000, status: 'active', since: '2018-11-05', advisor: 'James Park', country: 'UK', notes: 'Largest LP, priority relationship', lastContact: '2024-05-01' },
  { id: '5', name: 'Dr. Laurent Moreau', email: 'l.moreau@private.fr', phone: '+33 1 555 0505', type: 'hnwi', aum: 42000000, status: 'active', since: '2022-06-18', advisor: 'Sophie Chen', country: 'France', notes: 'Tech entrepreneur, high conviction', lastContact: '2024-04-20' },
  { id: '6', name: 'Singapore Sovereign Wealth', email: 'invest@sgwealth.sg', phone: '+65 6555 0606', type: 'institutional', aum: 900000000, status: 'prospect', since: '2024-02-01', advisor: 'James Park', country: 'Singapore', notes: 'In due diligence phase', lastContact: '2024-04-25' },
  { id: '7', name: 'Maple Grove Endowment', email: 'fund@maplegrove.ca', phone: '+1 416 555 0707', type: 'endowment', aum: 95000000, status: 'onboarding', since: '2024-04-01', advisor: 'Marc Lefebvre', country: 'Canada', notes: 'KYC in progress', lastContact: '2024-04-29' },
  { id: '8', name: 'Herzog Family Office', email: 'invest@herzog-fo.de', phone: '+49 30 555 0808', type: 'family_office', aum: 130000000, status: 'inactive', since: '2020-03-12', advisor: 'Sophie Chen', country: 'Germany', notes: 'Redemption processed Q1 2024', lastContact: '2024-01-15' },
]

export const investors: Investor[] = [
  { id: '1', name: 'BlackRock Pension Trust', type: 'Pension Fund', committed: 50000000, called: 42000000, distributed: 18500000, nav: 31200000, irr: 18.4, multiple: 1.18, status: 'active', fund: 'MYJ Fund III', since: '2019-03-15', country: 'USA' },
  { id: '2', name: 'Al-Faisal Family Office', type: 'Family Office', committed: 30000000, called: 30000000, distributed: 8200000, nav: 26100000, irr: 22.1, multiple: 1.14, status: 'active', fund: 'MYJ Fund III', since: '2020-07-22', country: 'UAE' },
  { id: '3', name: 'Nexus Institutional LP', type: 'Institutional', committed: 75000000, called: 60000000, distributed: 22000000, nav: 48500000, irr: 19.8, multiple: 1.17, status: 'active', fund: 'MYJ Fund II', since: '2018-11-05', country: 'UK' },
  { id: '4', name: 'Zurich Endowment Capital', type: 'Endowment', committed: 20000000, called: 14000000, distributed: 0, nav: 16800000, irr: 24.3, multiple: 1.2, status: 'active', fund: 'MYJ Fund IV', since: '2021-01-10', country: 'Switzerland' },
  { id: '5', name: 'Dr. Laurent Moreau', type: 'HNWI', committed: 5000000, called: 5000000, distributed: 2100000, nav: 3900000, irr: 16.2, multiple: 1.2, status: 'active', fund: 'MYJ Fund III', since: '2022-06-18', country: 'France' },
  { id: '6', name: 'Maple Grove Endowment', type: 'Endowment', committed: 10000000, called: 0, distributed: 0, nav: 0, irr: 0, multiple: 0, status: 'committed', fund: 'MYJ Fund IV', since: '2024-04-01', country: 'Canada' },
  { id: '7', name: 'Pioneer Capital Group', type: 'Institutional', committed: 40000000, called: 40000000, distributed: 58000000, nav: 0, irr: 31.2, multiple: 1.45, status: 'exited', fund: 'MYJ Fund I', since: '2015-06-01', country: 'USA' },
]

export const deals: Deal[] = [
  { id: '1', company: 'NovaTech AI', sector: 'Technology', stage: 'portfolio', amount: 25000000, manager: 'Marc Lefebvre', date: '2023-06-15', description: 'Enterprise AI platform for supply chain optimization', irr_target: 28, country: 'USA' },
  { id: '2', company: 'GreenCore Energy', sector: 'CleanTech', stage: 'portfolio', amount: 18000000, manager: 'Sophie Chen', date: '2023-09-20', description: 'Next-gen solar panel manufacturer', irr_target: 24, country: 'Germany' },
  { id: '3', company: 'MedStream Analytics', sector: 'Healthcare', stage: 'closing', amount: 30000000, manager: 'James Park', date: '2024-03-01', description: 'Real-time patient data analytics SaaS', irr_target: 32, country: 'USA' },
  { id: '4', company: 'FinLedger Pro', sector: 'FinTech', stage: 'due_diligence', amount: 15000000, manager: 'Marc Lefebvre', date: '2024-04-10', description: 'Blockchain-based settlement infrastructure', irr_target: 26, country: 'Singapore' },
  { id: '5', company: 'AgroSense Systems', sector: 'AgriTech', stage: 'term_sheet', amount: 12000000, manager: 'Sophie Chen', date: '2024-04-20', description: 'Precision agriculture IoT platform', irr_target: 22, country: 'France' },
  { id: '6', company: 'UrbanFlow Mobility', sector: 'PropTech', stage: 'screening', amount: 20000000, manager: 'James Park', date: '2024-04-28', description: 'Smart city mobility infrastructure', irr_target: 20, country: 'UAE' },
  { id: '7', company: 'CyberShield Networks', sector: 'Cybersecurity', stage: 'prospect', amount: 35000000, manager: 'Marc Lefebvre', date: '2024-05-01', description: 'Zero-trust enterprise security platform', irr_target: 30, country: 'UK' },
  { id: '8', company: 'DataVault Storage', sector: 'Technology', stage: 'passed', amount: 8000000, manager: 'Sophie Chen', date: '2024-02-15', description: 'Distributed cold storage solution', irr_target: 18, country: 'USA' },
]

export const positions: Position[] = [
  { id: '1', ticker: 'NVDA', name: 'NVIDIA Corp', side: 'long', quantity: 12500, entryPrice: 485.20, currentPrice: 875.40, marketValue: 10942500, pnl: 4875000, pnlPct: 80.5, sector: 'Technology', strategy: 'AI Thematic', weight: 8.2 },
  { id: '2', ticker: 'MSFT', name: 'Microsoft Corp', side: 'long', quantity: 18000, entryPrice: 312.50, currentPrice: 415.80, marketValue: 7484400, pnl: 1858500, pnlPct: 33.1, sector: 'Technology', strategy: 'Large Cap Growth', weight: 5.6 },
  { id: '3', ticker: 'TSLA', name: 'Tesla Inc', side: 'short', quantity: 8500, entryPrice: 245.30, currentPrice: 178.60, marketValue: -1518100, pnl: 567050, pnlPct: 27.2, sector: 'Consumer', strategy: 'L/S Equity', weight: -1.1 },
  { id: '4', ticker: 'JPM', name: 'JPMorgan Chase', side: 'long', quantity: 22000, entryPrice: 148.20, currentPrice: 198.45, marketValue: 4365900, pnl: 1105500, pnlPct: 33.9, sector: 'Financials', strategy: 'Value', weight: 3.3 },
  { id: '5', ticker: 'BRK.B', name: 'Berkshire Hathaway', side: 'long', quantity: 15000, entryPrice: 325.40, currentPrice: 385.20, marketValue: 5778000, pnl: 897000, pnlPct: 18.4, sector: 'Financials', strategy: 'Value', weight: 4.3 },
  { id: '6', ticker: 'AMZN', name: 'Amazon.com Inc', side: 'long', quantity: 28000, entryPrice: 138.50, currentPrice: 182.30, marketValue: 5104400, pnl: 1226400, pnlPct: 31.6, sector: 'Consumer', strategy: 'Large Cap Growth', weight: 3.8 },
  { id: '7', ticker: 'META', name: 'Meta Platforms', side: 'long', quantity: 9500, entryPrice: 298.70, currentPrice: 508.90, marketValue: 4834550, pnl: 1996850, pnlPct: 70.4, sector: 'Technology', strategy: 'AI Thematic', weight: 3.6 },
  { id: '8', ticker: 'NFLX', name: 'Netflix Inc', side: 'short', quantity: 5000, entryPrice: 622.80, currentPrice: 698.50, marketValue: -3492500, pnl: -378500, pnlPct: -12.2, sector: 'Consumer', strategy: 'L/S Equity', weight: -2.6 },
  { id: '9', ticker: 'GLD', name: 'SPDR Gold Trust', side: 'long', quantity: 45000, entryPrice: 178.40, currentPrice: 215.60, marketValue: 9702000, pnl: 1674000, pnlPct: 20.9, sector: 'Commodities', strategy: 'Macro Hedge', weight: 7.3 },
  { id: '10', ticker: 'TLT', name: 'iShares 20Y Treasury', side: 'long', quantity: 60000, entryPrice: 98.20, currentPrice: 102.80, marketValue: 6168000, pnl: 276000, pnlPct: 4.7, sector: 'Fixed Income', strategy: 'Macro Hedge', weight: 4.6 },
]

export const recentTrades: Trade[] = [
  { id: '1', date: '2024-05-01', ticker: 'NVDA', name: 'NVIDIA Corp', side: 'buy', quantity: 2500, price: 865.20, value: 2163000, status: 'filled', strategy: 'AI Thematic' },
  { id: '2', date: '2024-05-01', ticker: 'TSLA', name: 'Tesla Inc', side: 'sell', quantity: 1500, price: 181.40, value: 272100, status: 'filled', strategy: 'L/S Equity' },
  { id: '3', date: '2024-04-30', ticker: 'GLD', name: 'SPDR Gold Trust', side: 'buy', quantity: 5000, price: 213.80, value: 1069000, status: 'filled', strategy: 'Macro Hedge' },
  { id: '4', date: '2024-04-30', ticker: 'META', name: 'Meta Platforms', side: 'buy', quantity: 500, price: 502.30, value: 251150, status: 'filled', strategy: 'AI Thematic' },
  { id: '5', date: '2024-04-29', ticker: 'NFLX', name: 'Netflix Inc', side: 'buy', quantity: 1000, price: 685.40, value: 685400, status: 'filled', strategy: 'L/S Equity' },
  { id: '6', date: '2024-04-29', ticker: 'JPM', name: 'JPMorgan Chase', side: 'buy', quantity: 3000, price: 195.80, value: 587400, status: 'pending', strategy: 'Value' },
  { id: '7', date: '2024-04-28', ticker: 'BRK.B', name: 'Berkshire Hathaway', side: 'buy', quantity: 2000, price: 382.10, value: 764200, status: 'filled', strategy: 'Value' },
]

export const complianceItems: ComplianceItem[] = [
  { id: '1', title: 'Annual KYC Refresh — Nexus Institutional LP', category: 'kyc', status: 'overdue', dueDate: '2024-04-15', assignee: 'James Park', priority: 'high', description: 'Annual KYC documentation refresh required for Nexus Institutional LP per FATF guidelines' },
  { id: '2', title: 'Q1 2024 Regulatory Filing — SEC Form ADV', category: 'regulatory', status: 'compliant', dueDate: '2024-03-31', assignee: 'Compliance Team', priority: 'high', description: 'Quarterly SEC Form ADV filing completed and submitted' },
  { id: '3', title: 'AML Screening — Maple Grove Endowment', category: 'aml', status: 'pending', dueDate: '2024-05-10', assignee: 'Sophie Chen', priority: 'high', description: 'Initial AML screening for new investor onboarding' },
  { id: '4', title: 'Fund IV Offering Memorandum Review', category: 'regulatory', status: 'review', dueDate: '2024-05-15', assignee: 'Legal Team', priority: 'medium', description: 'Legal review of updated Fund IV OM prior to distribution' },
  { id: '5', title: 'GDPR Data Audit', category: 'internal', status: 'pending', dueDate: '2024-05-31', assignee: 'Tech Team', priority: 'medium', description: 'Quarterly GDPR compliance audit of investor data storage and access logs' },
  { id: '6', title: 'Q1 Investor Capital Account Statements', category: 'reporting', status: 'compliant', dueDate: '2024-04-30', assignee: 'Finance Team', priority: 'medium', description: 'Q1 2024 capital account statements distributed to all LPs' },
  { id: '7', title: 'MiFID II Transaction Reporting', category: 'regulatory', status: 'compliant', dueDate: '2024-04-30', assignee: 'Trading Desk', priority: 'high', description: 'Monthly MiFID II transaction reporting submitted to ESMA' },
  { id: '8', title: 'Insider Trading Policy Certification', category: 'internal', status: 'pending', dueDate: '2024-05-20', assignee: 'All Staff', priority: 'medium', description: 'Annual certification of insider trading and market manipulation policy' },
  { id: '9', title: 'FATCA / CRS Reporting', category: 'regulatory', status: 'overdue', dueDate: '2024-04-30', assignee: 'Finance Team', priority: 'high', description: 'Annual FATCA and CRS reporting to relevant tax authorities' },
  { id: '10', title: 'Risk Management Policy Annual Review', category: 'internal', status: 'review', dueDate: '2024-06-01', assignee: 'Risk Team', priority: 'low', description: 'Annual review and update of the fund risk management framework' },
]

export const fundingRounds: FundingRound[] = [
  { id: '1', fund: 'MYJ Fund I', target: 100000000, raised: 100000000, status: 'closed', closeDate: '2016-12-31', investors: 12, type: 'Private Equity', vintage: '2015' },
  { id: '2', fund: 'MYJ Fund II', target: 250000000, raised: 250000000, status: 'closed', closeDate: '2020-06-30', investors: 18, type: 'Private Equity', vintage: '2019' },
  { id: '3', fund: 'MYJ Fund III', target: 400000000, raised: 380000000, status: 'closed', closeDate: '2023-03-31', investors: 24, type: 'Growth Equity', vintage: '2022' },
  { id: '4', fund: 'MYJ Fund IV', target: 600000000, raised: 210000000, status: 'open', closeDate: '2025-06-30', investors: 8, type: 'Growth Equity', vintage: '2024' },
  { id: '5', fund: 'MYJ Opportunities I', target: 150000000, raised: 0, status: 'upcoming', closeDate: '2025-12-31', investors: 0, type: 'Opportunistic', vintage: '2025' },
]

export const syncSources: SyncSource[] = [
  { id: '1', name: 'Interactive Brokers', type: 'broker', status: 'connected', lastSync: '2024-05-01T09:15:00Z', records: 4821, icon: 'TrendingUp' },
  { id: '2', name: 'Goldman Sachs Prime', type: 'broker', status: 'connected', lastSync: '2024-05-01T08:45:00Z', records: 2341, icon: 'TrendingUp' },
  { id: '3', name: 'BNY Mellon Custody', type: 'custodian', status: 'connected', lastSync: '2024-05-01T07:30:00Z', records: 12540, icon: 'Shield' },
  { id: '4', name: 'Bloomberg Data', type: 'data', status: 'syncing', lastSync: '2024-05-01T09:20:00Z', records: 98420, icon: 'BarChart2' },
  { id: '5', name: 'Refinitiv Eikon', type: 'data', status: 'connected', lastSync: '2024-05-01T09:00:00Z', records: 45200, icon: 'BarChart2' },
  { id: '6', name: 'Geneva World (Advent)', type: 'accounting', status: 'connected', lastSync: '2024-05-01T06:00:00Z', records: 8920, icon: 'BookOpen' },
  { id: '7', name: 'Salesforce CRM', type: 'crm', status: 'error', lastSync: '2024-04-30T18:00:00Z', records: 1240, icon: 'Users' },
  { id: '8', name: 'DocuSign', type: 'crm', status: 'disconnected', lastSync: '2024-04-28T12:00:00Z', records: 340, icon: 'FileText' },
]

export const navHistory: MonthlyPoint[] = [
  { month: 'Jan 23', value: 100 },
  { month: 'Feb 23', value: 103.2 },
  { month: 'Mar 23', value: 108.5 },
  { month: 'Apr 23', value: 106.8 },
  { month: 'May 23', value: 112.4 },
  { month: 'Jun 23', value: 115.1 },
  { month: 'Jul 23', value: 119.8 },
  { month: 'Aug 23', value: 117.3 },
  { month: 'Sep 23', value: 121.6 },
  { month: 'Oct 23', value: 118.9 },
  { month: 'Nov 23', value: 126.4 },
  { month: 'Dec 23', value: 131.2 },
  { month: 'Jan 24', value: 134.5 },
  { month: 'Feb 24', value: 139.8 },
  { month: 'Mar 24', value: 143.2 },
  { month: 'Apr 24', value: 148.7 },
]

export const revenueData: MonthlyPoint[] = [
  { month: 'Jan', value: 2840000, value2: 1250000 },
  { month: 'Feb', value: 2960000, value2: 980000 },
  { month: 'Mar', value: 3120000, value2: 2100000 },
  { month: 'Apr', value: 3080000, value2: 1850000 },
  { month: 'May', value: 3240000, value2: 2300000 },
  { month: 'Jun', value: 3380000, value2: 1650000 },
  { month: 'Jul', value: 3150000, value2: 1900000 },
  { month: 'Aug', value: 3420000, value2: 2450000 },
  { month: 'Sep', value: 3560000, value2: 2800000 },
  { month: 'Oct', value: 3280000, value2: 1400000 },
  { month: 'Nov', value: 3650000, value2: 3100000 },
  { month: 'Dec', value: 3890000, value2: 4200000 },
]

export const cashFlowData: MonthlyPoint[] = [
  { month: 'Jan', value: 18500000, value2: 12400000 },
  { month: 'Feb', value: 22000000, value2: 14800000 },
  { month: 'Mar', value: 31000000, value2: 18500000 },
  { month: 'Apr', value: 19500000, value2: 22100000 },
  { month: 'May', value: 28000000, value2: 16200000 },
  { month: 'Jun', value: 24500000, value2: 19800000 },
  { month: 'Jul', value: 21000000, value2: 17400000 },
  { month: 'Aug', value: 26500000, value2: 21000000 },
  { month: 'Sep', value: 34000000, value2: 24500000 },
  { month: 'Oct', value: 23000000, value2: 18000000 },
  { month: 'Nov', value: 29500000, value2: 22400000 },
  { month: 'Dec', value: 42000000, value2: 31200000 },
]
