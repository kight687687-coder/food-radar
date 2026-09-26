import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { AppErrorBoundary } from './components/AppErrorBoundary'
import { AppProvider } from './context/AppContext'
import { ProfilePage } from './pages/ProfilePage'
import { HomePage } from './pages/HomePage'
import { ScanPage } from './pages/ScanPage'
import { ResultPage } from './pages/ResultPage'
import { ComparePage } from './pages/ComparePage'
import { HistoryPage } from './pages/HistoryPage'
import { ReportPage } from './pages/ReportPage'
import { ToolboxPage } from './pages/ToolboxPage'
import { MinePage } from './pages/MinePage'
import { AvoidPage } from './pages/AvoidPage'
import { FamilyEditPage, FamilyPage } from './pages/FamilyPage'
import { IngredientPage } from './pages/IngredientPage'
import { WikiDetailPage, WikiPage } from './pages/WikiPage'
import { ChatPage } from './pages/ChatPage'
import { TrendPage } from './pages/TrendPage'
import { ExamplesPage } from './pages/ExamplesPage'
import { getProfile } from './services/storage'
import './styles/global.css'
import './styles/pages.css'

function ProfileGate({ children }) {
  const hasProfile = Boolean(getProfile()?.userId)
  return hasProfile ? (children || <Outlet />) : <Navigate to="/profile" replace />
}

function App() {
  return <AppProvider><BrowserRouter><Routes><Route element={<AppShell />}><Route path="/profile" element={<ProfilePage />} /><Route element={<ProfileGate />}><Route path="/" element={<HomePage />} /><Route path="/scan" element={<ScanPage />} /><Route path="/examples" element={<ExamplesPage />} /><Route path="/result" element={<ResultPage />} /><Route path="/compare" element={<ComparePage />} /><Route path="/history" element={<HistoryPage />} /><Route path="/report" element={<ReportPage />} /><Route path="/toolbox" element={<ToolboxPage />} /><Route path="/mine" element={<MinePage />} /><Route path="/avoid" element={<AvoidPage />} /><Route path="/family" element={<FamilyPage />} /><Route path="/family/new" element={<FamilyEditPage isNew />} /><Route path="/family/edit/:memberId" element={<FamilyEditPage />} /><Route path="/ingredient" element={<IngredientPage />} /><Route path="/wiki" element={<WikiPage />} /><Route path="/wiki/:name" element={<WikiDetailPage />} /><Route path="/ai-chat" element={<ChatPage />} /><Route path="/card-report" element={<TrendPage />} /></Route><Route path="*" element={<Navigate to="/" replace />} /></Route></Routes></BrowserRouter></AppProvider>
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppErrorBoundary><App /></AppErrorBoundary>
  </React.StrictMode>,
)
