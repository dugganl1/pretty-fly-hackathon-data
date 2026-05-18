import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import { DataProvider } from './data/DataContext';
import Layout from './Layout';
import Assessment from './pages/Assessment';
import PnL from './pages/PnL';
import RevenueMarketing from './pages/RevenueMarketing';
import Operations from './pages/Operations';
import CustomersSupport from './pages/CustomersSupport';
import Reconcile from './pages/Reconcile';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DataProvider>
      <HashRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/assessment" replace />} />
            <Route path="/assessment" element={<Assessment />} />
            <Route path="/pnl" element={<PnL />} />
            <Route path="/revenue" element={<RevenueMarketing />} />
            <Route path="/operations" element={<Operations />} />
            <Route path="/customers" element={<CustomersSupport />} />
          </Route>
          <Route path="/reconcile" element={<Reconcile />} />
        </Routes>
      </HashRouter>
    </DataProvider>
  </StrictMode>,
);
