import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../client';
import type {
  ImportJob,
  ImportJobDetailed,
  ImportConfirmResponse,
  ImportValidateResponse,
  ImportTemplateResponse,
  OnboardingStatusDetailed,
  AdminDepartmentResponse,
  AdminEmployeeResponse,
  PolicyReadinessResponse,
  DocumentListResponse,
  DocumentUploadPayload,
} from '../types';

// ---------------------------------------------------------------------------
// Onboarding status
// ---------------------------------------------------------------------------

export function useOnboardingStatus() {
  return useQuery({
    queryKey: ['onboarding', 'status', 'detailed'],
    queryFn: () => api.get<OnboardingStatusDetailed>('/onboarding/status'),
  });
}

// ---------------------------------------------------------------------------
// Activation
// ---------------------------------------------------------------------------

export function useActivateCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ company_id: string; activated: boolean; message: string }>('/onboarding/activate'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['onboarding', 'status'] });
      qc.invalidateQueries({ queryKey: ['onboarding', 'status', 'detailed'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Import jobs
// ---------------------------------------------------------------------------

export function useImportJobs(filters?: { import_type?: string; status?: string; limit?: number; offset?: number }) {
  const params = new URLSearchParams();
  if (filters?.import_type) params.set('import_type', filters.import_type);
  if (filters?.status) params.set('status', filters.status);
  if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters?.offset !== undefined) params.set('offset', String(filters.offset));

  const queryString = params.toString();
  const path = `/onboarding/imports${queryString ? `?${queryString}` : ''}`;

  return useQuery({
    queryKey: ['onboarding', 'imports', filters],
    queryFn: () => api.get<ImportJob[]>(path),
  });
}

export function useImportJob(
  jobId: string,
  options?: {
    enabled?: boolean;
    refetchInterval?: number | false | ((query: { state: { data?: ImportJobDetailed } }) => number | false);
  }
) {
  return useQuery({
    queryKey: ['onboarding', 'imports', jobId],
    queryFn: () => api.get<ImportJobDetailed>(`/onboarding/imports/${jobId}`),
    enabled: options?.enabled ?? Boolean(jobId),
    refetchInterval: options?.refetchInterval,
  });
}

// ---------------------------------------------------------------------------
// Import validation & confirmation  (multi-part file upload)
// ---------------------------------------------------------------------------

export function useValidateImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ importType, file }: { importType: string; file: File }) => {
      const formData = new FormData();
      formData.append('upload', file);
      return api.upload<ImportValidateResponse>(`/onboarding/imports/${importType}/validate`, formData);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['onboarding', 'imports'] });
    },
  });
}

export function useConfirmImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => api.post<ImportConfirmResponse>(`/onboarding/imports/${jobId}/confirm`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['onboarding', 'imports'] });
      qc.invalidateQueries({ queryKey: ['onboarding', 'status'] });
      qc.invalidateQueries({ queryKey: ['onboarding', 'status', 'detailed'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Template
// ---------------------------------------------------------------------------

export function useImportTemplate(importType: string) {
  return useQuery({
    queryKey: ['onboarding', 'templates', importType],
    queryFn: () => api.get<ImportTemplateResponse>(`/onboarding/templates/${importType}`),
    enabled: Boolean(importType),
  });
}

// ---------------------------------------------------------------------------
// Admin (used by wizard steps)
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
      qc.invalidateQueries({ queryKey: ['onboarding', 'status'] });
      qc.invalidateQueries({ queryKey: ['onboarding', 'status', 'detailed'] });
    },
  });
}

export function useAdminEmployees(filters?: { department_id?: string; limit?: number; offset?: number }) {
  const params = new URLSearchParams();
  if (filters?.department_id) params.set('department_id', filters.department_id);
  if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters?.offset !== undefined) params.set('offset', String(filters.offset));
  const qs = params.toString();
  return useQuery({
    queryKey: ['admin', 'employees', filters],
    queryFn: () => api.get<AdminEmployeeResponse[]>(`/admin/employees${qs ? `?${qs}` : ''}`),
  });
}

export function useUpdateEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<AdminEmployeeResponse> }) =>
      api.patch<AdminEmployeeResponse>(`/admin/employees/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'employees'] });
      qc.invalidateQueries({ queryKey: ['onboarding', 'status'] });
      qc.invalidateQueries({ queryKey: ['onboarding', 'status', 'detailed'] });
    },
  });
}

export function usePolicyReadiness() {
  return useQuery({
    queryKey: ['admin', 'policy-readiness'],
    queryFn: () => api.get<PolicyReadinessResponse>('/admin/policy-readiness'),
  });
}

// ---------------------------------------------------------------------------
// Documents / RAG (policies)
// ---------------------------------------------------------------------------

export function useDocuments() {
  return useQuery({
    queryKey: ['documents'],
    queryFn: () => api.get<DocumentListResponse[]>('/documents'),
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: DocumentUploadPayload) => {
      const formData = new FormData();
      formData.append('file', payload.file);
      formData.append('title', payload.title);
      formData.append('document_type', payload.document_type);
      payload.department_scope.forEach((s) => formData.append('department_scope', s));
      formData.append('access_scope', payload.access_scope);
      if (payload.effective_date) {
        formData.append('effective_date', payload.effective_date);
      }
      if (payload.custom_metadata) {
        formData.append('custom_metadata', JSON.stringify(payload.custom_metadata));
      }
      return api.upload<DocumentListResponse>('/documents', formData);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] });
      qc.invalidateQueries({ queryKey: ['admin', 'policy-readiness'] });
      qc.invalidateQueries({ queryKey: ['onboarding', 'status'] });
      qc.invalidateQueries({ queryKey: ['onboarding', 'status', 'detailed'] });
    },
  });
}
