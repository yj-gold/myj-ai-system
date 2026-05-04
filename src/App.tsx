import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import Dashboard from './pages/Dashboard'
import Clients from './pages/Clients'
import Investors from './pages/Investors'
import Pipeline from './pages/Pipeline'
import Revenue from './pages/Revenue'
import CashFlow from './pages/CashFlow'
import Funding from './pages/Funding'
import Financials from './pages/Financials'
import Trading from './pages/Trading'
import Compliance from './pages/Compliance'
import Sync from './pages/Sync'
import MoneyMachine from './pages/MoneyMachine'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="clients" element={<Clients />} />
          <Route path="investors" element={<Investors />} />
          <Route path="pipeline" element={<Pipeline />} />
          <Route path="revenue" element={<Revenue />} />
          <Route path="cashflow" element={<CashFlow />} />
          <Route path="funding" element={<Funding />} />
          <Route path="financials" element={<Financials />} />
          <Route path="trading" element={<Trading />} />
          <Route path="compliance" element={<Compliance />} />
          <Route path="sync" element={<Sync />} />
          <Route path="money-machine" element={<MoneyMachine />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
