import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../client';
import type {
  AdminSummaryResponse,
  AdminCompanyProfile,
  AdminDepartmentResponse,
  AdminEmployeeResponse,
  AdminAssetResponse,
  AdminSoftwareCatalogResponse,
  AdminBudgetResponse,
  AdminHolidayResponse,
  AdminStaffingRuleResponse,
  AdminSupplierResponse,
  PolicyReadinessResponse,
} from '../types';

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

export function useAdminSummary() {
  return useQuery({
    queryKey: ['admin', 'summary'],
    queryFn: () => api.get<AdminSummaryResponse>('/admin/summary'),
  });
}

// ---------------------------------------------------------------------------
// Company
// ---------------------------------------------------------------------------

export function useAdminCompany() {
  return useQuery({
    queryKey: ['admin', 'company'],
    queryFn: () => api.get<AdminCompanyProfile>('/admin/company'),
  });
}

export function useUpdateAdminCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name?: string; custom_data?: Record<string, unknown> }) =>
      api.patch<AdminCompanyProfile>('/admin/company', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'company'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Employees
// ---------------------------------------------------------------------------

export function useAdminEmployees(
  filters: {
    department_id?: string;
    q?: string;
    limit?: number;
    offset?: number;
  } = {}
) {
  const params = new URLSearchParams();
  if (filters.department_id) params.set('department_id', filters.department_id);
  if (filters.q) params.set('q', filters.q);
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters.offset !== undefined) params.set('offset', String(filters.offset));
  const qs = params.toString();

  return useQuery({
    queryKey: ['admin', 'employees', filters],
    queryFn: () => api.get<AdminEmployeeResponse[]>(`/admin/employees${qs ? `?${qs}` : ''}`),
  });
}

export function useCreateEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      employee_code: string;
      email: string;
      job_title?: string | null;
      department_id?: string | null;
      hire_date?: string | null;
      manager_employee_id?: string | null;
      employment_status?: string;
      custom_data?: Record<string, unknown>;
    }) => api.post<AdminEmployeeResponse>('/admin/employees', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'employees'] });
      qc.invalidateQueries({ queryKey: ['admin', 'summary'] });
    },
  });
}

export function useUpdateEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<AdminEmployeeResponse> }) =>
      api.patch<AdminEmployeeResponse>(`/admin/employees/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'employees'] });
      qc.invalidateQueries({ queryKey: ['admin', 'summary'] });
    },
  });
}

export function useDeactivateEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.patch<AdminEmployeeResponse>(`/admin/employees/${id}`, {
        employment_status: 'terminated',
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'employees'] });
      qc.invalidateQueries({ queryKey: ['admin', 'summary'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Departments
// ---------------------------------------------------------------------------

export function useAdminDepartments() {
  return useQuery({
    queryKey: ['admin', 'departments'],
    queryFn: () => api.get<AdminDepartmentResponse[]>('/admin/departments'),
  });
}

export function useUpdateDepartment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<AdminDepartmentResponse> }) =>
      api.patch<AdminDepartmentResponse>(`/admin/departments/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'departments'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Assets
// ---------------------------------------------------------------------------

export function useAdminAssets(filters?: { asset_type?: string; limit?: number; offset?: number }) {
  const params = new URLSearchParams();
  if (filters?.asset_type) params.set('asset_type', filters.asset_type);
  if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters?.offset !== undefined) params.set('offset', String(filters.offset));
  const qs = params.toString();

  return useQuery({
    queryKey: ['admin', 'assets', filters],
    queryFn: () => api.get<AdminAssetResponse[]>(`/admin/assets${qs ? `?${qs}` : ''}`),
  });
}

// ---------------------------------------------------------------------------
// Software Catalog
// ---------------------------------------------------------------------------

export function useAdminSoftwareCatalog(filters?: { is_active?: boolean; limit?: number; offset?: number }) {
  const params = new URLSearchParams();
  if (filters?.is_active !== undefined) params.set('is_active', String(filters.is_active));
  if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters?.offset !== undefined) params.set('offset', String(filters.offset));
  const qs = params.toString();

  return useQuery({
    queryKey: ['admin', 'software-catalog', filters],
    queryFn: () => api.get<AdminSoftwareCatalogResponse[]>(`/admin/software-catalog${qs ? `?${qs}` : ''}`),
  });
}

// ---------------------------------------------------------------------------
// Budgets
// ---------------------------------------------------------------------------

export function useAdminBudgets(filters?: { department_id?: string; limit?: number; offset?: number }) {
  const params = new URLSearchParams();
  if (filters?.department_id) params.set('department_id', filters.department_id);
  if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters?.offset !== undefined) params.set('offset', String(filters.offset));
  const qs = params.toString();

  return useQuery({
    queryKey: ['admin', 'budgets', filters],
    queryFn: () => api.get<AdminBudgetResponse[]>(`/admin/budgets${qs ? `?${qs}` : ''}`),
  });
}

// ---------------------------------------------------------------------------
// Holidays
// ---------------------------------------------------------------------------

export function useAdminHolidays(filters?: { year?: number; limit?: number; offset?: number }) {
  const params = new URLSearchParams();
  if (filters?.year !== undefined) params.set('year', String(filters.year));
  if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters?.offset !== undefined) params.set('offset', String(filters.offset));
  const qs = params.toString();

  return useQuery({
    queryKey: ['admin', 'holidays', filters],
    queryFn: () => api.get<AdminHolidayResponse[]>(`/admin/holidays${qs ? `?${qs}` : ''}`),
  });
}

// ---------------------------------------------------------------------------
// Staffing Rules
// ---------------------------------------------------------------------------

export function useAdminStaffingRules(filters?: { department_id?: string; limit?: number; offset?: number }) {
  const params = new URLSearchParams();
  if (filters?.department_id) params.set('department_id', filters.department_id);
  if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters?.offset !== undefined) params.set('offset', String(filters.offset));
  const qs = params.toString();

  return useQuery({
    queryKey: ['admin', 'staffing-rules', filters],
    queryFn: () => api.get<AdminStaffingRuleResponse[]>(`/admin/staffing-rules${qs ? `?${qs}` : ''}`),
  });
}

// ---------------------------------------------------------------------------
// Suppliers
// ---------------------------------------------------------------------------

export function useAdminSuppliers(filters?: { is_active?: boolean; limit?: number; offset?: number }) {
  const params = new URLSearchParams();
  if (filters?.is_active !== undefined) params.set('is_active', String(filters.is_active));
  if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters?.offset !== undefined) params.set('offset', String(filters.offset));
  const qs = params.toString();

  return useQuery({
    queryKey: ['admin', 'suppliers', filters],
    queryFn: () => api.get<AdminSupplierResponse[]>(`/admin/suppliers${qs ? `?${qs}` : ''}`),
  });
}

// ---------------------------------------------------------------------------
// Policy Readiness
// ---------------------------------------------------------------------------

export function useAdminPolicyReadiness() {
  return useQuery({
    queryKey: ['admin', 'policy-readiness'],
    queryFn: () => api.get<PolicyReadinessResponse>('/admin/policy-readiness'),
  });
}
