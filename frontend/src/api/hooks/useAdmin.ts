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
    employment_status?: string;
    q?: string;
    limit?: number;
    offset?: number;
  } = {}
) {
  const params = new URLSearchParams();
  if (filters.department_id) params.set('department_id', filters.department_id);
  if (filters.employment_status) params.set('employment_status', filters.employment_status);
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
      temporary_password: string;
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

export function useAdminEmployee(id: string | undefined) {
  return useQuery({
    queryKey: ['admin', 'employees', 'detail', id],
    queryFn: () => api.get<AdminEmployeeResponse>(`/admin/employees/${id}`),
    enabled: Boolean(id),
  });
}

export function useDeactivateEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.del<void>(`/admin/employees/${id}`),
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

export function useAdminAssets(filters?: { asset_type?: string; asset_status?: string; limit?: number; offset?: number }) {
  const params = new URLSearchParams();
  if (filters?.asset_type) params.set('asset_type', filters.asset_type);
  if (filters?.asset_status) params.set('asset_status', filters.asset_status);
  if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters?.offset !== undefined) params.set('offset', String(filters.offset));
  const qs = params.toString();

  return useQuery({
    queryKey: ['admin', 'assets', filters],
    queryFn: () => api.get<AdminAssetResponse[]>(`/admin/assets${qs ? `?${qs}` : ''}`),
  });
}

export function useAdminAsset(id: string | undefined) {
  return useQuery({
    queryKey: ['admin', 'assets', 'detail', id],
    queryFn: () => api.get<AdminAssetResponse>(`/admin/assets/${id}`),
    enabled: Boolean(id),
  });
}

export function useCreateAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      asset_code: string; asset_type: string; brand: string; model: string;
      serial_number?: string | null; assigned_employee_id?: string | null;
      status?: string; location?: string | null;
    }) => api.post<AdminAssetResponse>('/admin/assets', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'assets'] });
      qc.invalidateQueries({ queryKey: ['admin', 'summary'] });
    },
  });
}

export function useUpdateAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<AdminAssetResponse> & { version: number } }) =>
      api.patch<AdminAssetResponse>(`/admin/assets/${id}`, body),
    onSuccess: (record) => {
      qc.invalidateQueries({ queryKey: ['admin', 'assets'] });
      qc.setQueryData(['admin', 'assets', 'detail', record.id], record);
    },
  });
}

export function useRetireAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.del<void>(`/admin/assets/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'assets'] }),
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

export function useCreateSoftware() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string; access_type: string; requires_manager_approval: boolean;
      requires_it_approval: boolean; license_limited: boolean;
      available_license_count: number | null; is_active: boolean;
    }) => api.post<AdminSoftwareCatalogResponse>('/admin/software-catalog', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'software-catalog'] }),
  });
}

export function useUpdateSoftware() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<AdminSoftwareCatalogResponse> & { version: number } }) =>
      api.patch<AdminSoftwareCatalogResponse>(`/admin/software-catalog/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'software-catalog'] }),
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

export function useCreateBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string; budget_type: string; currency: string; period_start: string;
      period_end: string; allocated_amount: string; approval_threshold?: string | null;
      department_id?: string | null; status?: string;
    }) => api.post<AdminBudgetResponse>('/admin/budgets', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'budgets'] }),
  });
}

export function useUpdateBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<AdminBudgetResponse> & { version: number } }) =>
      api.patch<AdminBudgetResponse>(`/admin/budgets/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'budgets'] }),
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

export function useCreateHoliday() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { holiday_date: string; name: string; is_paid: boolean }) =>
      api.post<AdminHolidayResponse>('/admin/holidays', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'holidays'] }),
  });
}

export function useUpdateHoliday() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<AdminHolidayResponse> }) =>
      api.patch<AdminHolidayResponse>(`/admin/holidays/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'holidays'] }),
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

export function useCreateStaffingRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      department_id: string; minimum_active_employees: number; effective_from: string;
      effective_to?: string | null; is_active: boolean;
    }) => api.post<AdminStaffingRuleResponse>('/admin/staffing-rules', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'staffing-rules'] }),
  });
}

export function useUpdateStaffingRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<AdminStaffingRuleResponse> }) =>
      api.patch<AdminStaffingRuleResponse>(`/admin/staffing-rules/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'staffing-rules'] }),
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

export function useCreateSupplier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string; contact_person?: string | null; email?: string | null;
      phone?: string | null; website?: string | null; is_active: boolean;
    }) => api.post<AdminSupplierResponse>('/admin/suppliers', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'suppliers'] }),
  });
}

export function useUpdateSupplier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<AdminSupplierResponse> }) =>
      api.patch<AdminSupplierResponse>(`/admin/suppliers/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'suppliers'] }),
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
