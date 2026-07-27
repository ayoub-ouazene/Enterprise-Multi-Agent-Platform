import { createBrowserRouter, Navigate } from 'react-router-dom';
import {
  ProtectedRoute,
  UnauthenticatedOnlyRoute,
  PasswordChangeRoute,
  OnboardingRoute,
  RoleRoute,
  AdminRoute,
  DepartmentRoute,
} from '../auth/guards';
import { ActorType } from '../api/types';
import { AppShell } from './layout/AppShell';
import { LoginPage } from './pages/LoginPage';
import { LandingPage } from './pages/LandingPage';
import { SignupPage } from './pages/SignupPage';
import { ChangePasswordPage } from './pages/ChangePasswordPage';
import { OverviewPage } from './pages/OverviewPage';
import { RequestsPage } from './pages/RequestsPage';
import { RequestDetailPage } from './pages/RequestDetailPage';
import { NewRequestPage } from './pages/NewRequestPage';
import { AssistantPage } from './pages/AssistantPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { SelfServicePage } from './pages/SelfServicePage';
import { HumanActionsPage } from './pages/HumanActionsPage';
import { HumanActionDetailPage } from './pages/HumanActionDetailPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { AdminShell } from './layout/AdminShell';
import {
  AdminOverviewPage,
  CompanyProfilePage,
  EmployeeDirectoryPage,
  EmployeeDetailPage,
  ManagersPage,
  DepartmentsPage,
  DepartmentDetailPage,
  AssetsPage,
  AssetDetailPage,
  SoftwareCatalogPage,
  BudgetsPage,
  SuppliersPage,
  HolidaysPage,
  StaffingRulesPage,
  PoliciesPage,
  FailuresPage,
  CapabilityGapsPage,
  DocumentsPage,
} from './pages/admin';
import { DepartmentShell } from './layout/DepartmentShell';
import {
  DepartmentsLandingPage,
  DepartmentOverviewPage,
  DepartmentRequestsPage,
  DepartmentOperationsPage,
  DepartmentActionsPage,
  DepartmentActivityPage,
  DepartmentSettingsPage,
} from './pages/departments';
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
    path: '/',
    element: <LandingPage />,
  },
  {
    path: '/login',
    element: (
      <UnauthenticatedOnlyRoute>
        <LoginPage />
      </UnauthenticatedOnlyRoute>
    ),
  },
  {
    path: '/signup',
    element: (
      <UnauthenticatedOnlyRoute>
        <SignupPage />
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
    path: '/app/onboarding/:stepId?',
    element: (
      <ProtectedRoute>
        <PasswordChangeRoute>
          <RoleRoute allowed={[ActorType.COMPANY]}>
            <OnboardingPage />
          </RoleRoute>
        </PasswordChangeRoute>
      </ProtectedRoute>
    ),
  },
  {
    path: '/app',
    element: <AuthenticatedLayout />,
    children: [
      { index: true, element: <Navigate to="dashboard" replace /> },
      { path: 'dashboard', element: <OverviewPage /> },
      { path: 'overview', element: <Navigate to="/app/dashboard" replace /> },
      { path: 'requests', element: <RequestsPage /> },
      { path: 'requests/new', element: <NewRequestPage /> },
      { path: 'requests/:requestId', element: <RequestDetailPage /> },
      { path: 'human-actions', element: <HumanActionsPage /> },
      { path: 'human-actions/:actionId', element: <HumanActionDetailPage /> },
      { path: 'notifications', element: <NotificationsPage /> },
      { path: 'assistant', element: <AssistantPage /> },
      { path: 'self-service', element: <SelfServicePage /> },
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
          { path: 'employees/:employeeId', element: <EmployeeDetailPage /> },
          { path: 'managers', element: <ManagersPage /> },
          { path: 'departments', element: <DepartmentsPage /> },
          { path: 'departments/:departmentId', element: <DepartmentDetailPage /> },
          { path: 'assets', element: <AssetsPage /> },
          { path: 'assets/:assetId', element: <AssetDetailPage /> },
          { path: 'software', element: <SoftwareCatalogPage /> },
          { path: 'budgets', element: <BudgetsPage /> },
          { path: 'suppliers', element: <SuppliersPage /> },
          { path: 'holidays', element: <HolidaysPage /> },
          { path: 'staffing-rules', element: <StaffingRulesPage /> },
          { path: 'policies', element: <PoliciesPage /> },
          { path: 'documents', element: <DocumentsPage /> },
          { path: 'failures', element: <FailuresPage /> },
          { path: 'capability-gaps', element: <CapabilityGapsPage /> },
        ],
      },
      {
        path: 'departments',
        element: (
          <DepartmentRoute>
            <DepartmentsLandingPage />
          </DepartmentRoute>
        ),
      },
      {
        path: 'departments/:deptSlug',
        element: (
          <DepartmentRoute>
            <DepartmentShell />
          </DepartmentRoute>
        ),
        children: [
          { index: true, element: <Navigate to="overview" replace /> },
          { path: 'overview', element: <DepartmentOverviewPage /> },
          { path: 'requests', element: <DepartmentRequestsPage /> },
          { path: 'operations', element: <DepartmentOperationsPage /> },
          { path: 'actions', element: <DepartmentActionsPage /> },
          { path: 'activity', element: <DepartmentActivityPage /> },
          { path: 'settings', element: <DepartmentSettingsPage /> },
        ],
      },
      { path: '*', element: <NotFound /> },
    ],
  },
  { path: '*', element: <NotFound /> },
]);
