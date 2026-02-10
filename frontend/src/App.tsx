import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { SnackbarProvider } from 'notistack';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import UsersPage from './pages/UsersPage';
import RolesPage from './pages/RolesPage';
import LLMConfigPage from './pages/LLMConfigPage';
import ConsumptionPage from './pages/ConsumptionPage';
import QuotasPage from './pages/QuotasPage';
import CostsPage from './pages/CostsPage';
import ModerationPage from './pages/ModerationPage';
import CatalogPage from './pages/CatalogPage';
import CatalogManagementPage from './pages/CatalogManagementPage';
import SettingsPage from './pages/SettingsPage';
import SystemPage from './pages/SystemPage';

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
      <Route path="users" element={<UsersPage />} />
      <Route path="roles" element={<RolesPage />} />
      <Route path="llm-config" element={<LLMConfigPage />} />
      <Route path="consumption" element={<ConsumptionPage />} />
      <Route path="quotas" element={<QuotasPage />} />
      <Route path="costs" element={<CostsPage />} />
      <Route path="moderation" element={<ModerationPage />} />
      <Route path="catalog" element={<CatalogPage />} />
      <Route path="catalog/manage" element={<CatalogManagementPage />} />
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
