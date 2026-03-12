import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Activity, ShieldAlert, List, Settings } from 'lucide-react';
import { useWebSocket } from '@/hooks';

// Stubs for now
import Dashboard from '@/pages/Dashboard';
import Inventory from '@/pages/Inventory';
import ScanEngine from '@/pages/ScanEngine';
import APIDetail from '@/pages/APIDetail';

const queryClient = new QueryClient();

function Sidebar() {
  const location = useLocation();
  const isActive = (p: string) => location.pathname === p;

  return (
    <nav className="layout-sidebar">
      <div style={{ padding: '24px', fontSize: '1.2rem', fontWeight: 700, letterSpacing: '2px', color: 'var(--color-primary-light)' }}>
        <ShieldAlert size={24} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '8px' }}/>
        ZOMBIE GUARD
      </div>
      <div className="flex-col mt-4">
        <Link to="/" className={`nav-item ${isActive('/') ? 'active' : ''}`}>
          <Activity size={18} /> Dashboard
        </Link>
        <Link to="/inventory" className={`nav-item ${isActive('/inventory') ? 'active' : ''}`}>
          <List size={18} /> API Inventory
        </Link>
        <Link to="/scan" className={`nav-item ${isActive('/scan') ? 'active' : ''}`}>
          <ShieldAlert size={18} /> Scan Engine
        </Link>
        <div style={{ marginTop: 'auto', padding: '24px 24px 12px', fontSize: '0.75rem', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
          Settings
        </div>
        <a href="#" className="nav-item">
           <Settings size={18} /> Preferences
        </a>
      </div>
    </nav>
  );
}

function GlobalLayout({ children }: { children: React.ReactNode }) {
  // Global connection to the WS
  const { connected } = useWebSocket((msg) => {
    // We could spawn toast notifications here easily
    console.log("WS Broadcast Received:", msg);
  });

  return (
    <div className="layout-wrapper">
      <Sidebar />
      <div className="layout-main">
        <header className="layout-header">
           <div className="text-sm font-medium">API Intelligence Platform</div>
           <div className="flex items-center gap-2 text-xs font-mono">
              <div style={{
                width: 8, height: 8, borderRadius: '50%',
                backgroundColor: connected ? 'var(--color-success)' : 'var(--color-critical)',
                boxShadow: `0 0 8px ${connected ? 'var(--color-success)' : 'var(--color-critical)'}`
              }} />
              {connected ? 'REAL-TIME ACTIVE' : 'DISCONNECTED'}
           </div>
        </header>
        <main className="page-container">
          {children}
        </main>
      </div>
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <GlobalLayout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/scan" element={<ScanEngine />} />
            <Route path="/api/:id" element={<APIDetail />} />
          </Routes>
        </GlobalLayout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
