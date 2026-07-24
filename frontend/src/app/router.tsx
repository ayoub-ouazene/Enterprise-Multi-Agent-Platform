import { createBrowserRouter, Navigate } from 'react-router-dom';
import {
  ProtectedRoute,
  UnauthenticatedOnlyRoute,
  PasswordChangeRoute,
  OnboardingRoute,
  RoleRoute,
  AdminRoute,
} from '../auth/guards';
import { ActorType } from '../api/types';
import { AppShell } from './layout/AppShell';
import { LoginPage } from './pages/LoginPage';
import { ChangePasswordPage } from './pages/ChangePasswordPage';
import { OverviewPage } from './pages/OverviewPage';
import { RequestsPage } from './pages/RequestsPage';
import { RequestDetailPage } from './pages/RequestDetailPage';
import { NewRequestPage } from './pages/NewRequestPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { HumanActionsPage } from './pages/HumanActionsPage';
import { HumanActionDetailPage } from './pages/HumanActionDetailPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { AdminShell } from './layout/AdminShell';
import {
  AdminOverviewPage,
  CompanyProfilePage,
  EmployeeDirectoryPage,
  ManagersPage,
  DepartmentsPage,
  AssetsPage,
  SoftwareCatalogPage,
  BudgetsPage,
  SuppliersPage,
  HolidaysPage,
  StaffingRulesPage,
  PoliciesPage,
} from './pages/admin';
import { AccessDenied } from '../components/feedback/AccessDenied';
import { NotFound } from '../components/feedback/NotFound';

function AuthenticatedLayout() {
  return (
    <ProtectedRoute>
      <PasswordChangeRoute>
        <OnboardingRoute>
          <AppShell />
        </OnboardingRoute>
      </PasswordChangeRoute>
    </ProtectedRoute>
  );
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: (
      <UnauthenticatedOnlyRoute>
        <LoginPage />
      </UnauthenticatedOnlyRoute>
    ),
  },
  {
    path: '/change-password',
    element: (
      <ProtectedRoute>
        <ChangePasswordPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/access-denied',
    element: <AccessDenied />,
  },
  {
    path: '/',
    element: <Navigate to="/app" replace />,
  },
  {
    path: '/app',
    element: <AuthenticatedLayout />,
    children: [
      { index: true, element: <Navigate to="overview" replace /> },
      { path: 'overview', element: <OverviewPage /> },
      { path: 'requests', element: <RequestsPage /> },
      { path: 'requests/new', element: <NewRequestPage /> },
      { path: 'requests/:requestId', element: <RequestDetailPage /> },
      { path: 'human-actions', element: <HumanActionsPage /> },
      { path: 'human-actions/:actionId', element: <HumanActionDetailPage /> },
      { path: 'notifications', element: <NotificationsPage /> },
      {
        path: 'onboarding',
        element: (
          <RoleRoute allowed={[ActorType.COMPANY]}>
            <OnboardingPage />
          </RoleRoute>
        ),
      },
      {
        path: 'admin',
        element: (
          <AdminRoute>
            <AdminShell />
          </AdminRoute>
        ),
        children: [
          { index: true, element: <Navigate to="overview" replace /> },
          { path: 'overview', element: <AdminOverviewPage /> },
          { path: 'company', element: <CompanyProfilePage /> },
          { path: 'employees', element: <EmployeeDirectoryPage /> },
          { path: 'managers', element: <ManagersPage /> },
          { path: 'departments', element: <DepartmentsPage /> },
          { path: 'assets', element: <AssetsPage /> },
          { path: 'software', element: <SoftwareCatalogPage /> },
          { path: 'budgets', element: <BudgetsPage /> },
          { path: 'suppliers', element: <SuppliersPage /> },
          { path: 'holidays', element: <HolidaysPage /> },
          { path: 'staffing-rules', element: <StaffingRulesPage /> },
          { path: 'policies', element: <PoliciesPage /> },
        ],
      },
      { path: '*', element: <NotFound /> },
    ],
  },
  { path: '*', element: <NotFound /> },
]);
