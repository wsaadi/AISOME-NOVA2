import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { SnackbarProvider } from 'notistack';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ConsumptionPage from './pages/ConsumptionPage';
import CatalogPage from './pages/CatalogPage';
import CatalogManagementPage from './pages/CatalogManagementPage';
import SettingsPage from './pages/SettingsPage';
import SystemPage from './pages/SystemPage';
import AgentRuntimePage from './pages/AgentRuntimePage';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

const AppRoutes: React.FC = () => (
  <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
      <Route index element={<Navigate to="/dashboard" replace />} />
      <Route path="dashboard" element={<DashboardPage />} />
      <Route path="consumption" element={<ConsumptionPage />} />
      <Route path="catalog" element={<CatalogPage />} />
      <Route path="catalog/manage" element={<CatalogManagementPage />} />
      <Route path="agent/:slug" element={<AgentRuntimePage />} />
      <Route path="settings" element={<SettingsPage />} />
      <Route path="system" element={<SystemPage />} />
    </Route>
  </Routes>
);

const App: React.FC = () => (
  <ThemeProvider>
    <SnackbarProvider maxSnack={3} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </SnackbarProvider>
  </ThemeProvider>
);

export default App;
