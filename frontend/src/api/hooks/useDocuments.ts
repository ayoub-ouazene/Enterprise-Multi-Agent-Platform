import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../client';
import {
  KnowledgeDocumentListFilters,
  KnowledgeDocumentResponse,
} from '../types';

function buildQs(filters: KnowledgeDocumentListFilters): string {
  const params = new URLSearchParams();
  if (filters.document_type) params.set('document_type', filters.document_type);
  if (filters.status) params.set('status', filters.status);
  if (filters.ingestion_status) params.set('ingestion_status', filters.ingestion_status);
  if (filters.department) params.set('department', filters.department);
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters.offset !== undefined) params.set('offset', String(filters.offset));
  const query = params.toString();
  return query ? `?${query}` : '';
}

export function useDocumentList(filters: KnowledgeDocumentListFilters = {}) {
  return useQuery<KnowledgeDocumentResponse[]>({
    queryKey: ['documents', filters],
    queryFn: () => api.get<KnowledgeDocumentResponse[]>(`/documents${buildQs(filters)}`),
    staleTime: 30_000,
  });
}

export function useDocument(id: string) {
  return useQuery<KnowledgeDocumentResponse>({
    queryKey: ['document', id],
    queryFn: () => api.get<KnowledgeDocumentResponse>(`/documents/${id}`),
    enabled: !!id,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation<KnowledgeDocumentResponse, Error, FormData>({
    mutationFn: (formData) =>
            api.upload<KnowledgeDocumentResponse>('/documents', formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function useReplaceDocument() {
  const queryClient = useQueryClient();
  return useMutation<KnowledgeDocumentResponse, Error, { id: string; formData: FormData }>({
    mutationFn: ({ id, formData }) =>
      api.upload<KnowledgeDocumentResponse>(`/documents/${id}/replace`, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function useRetryIngestion() {
  const queryClient = useQueryClient();
  return useMutation<KnowledgeDocumentResponse, Error, { id: string; file: File }>({
    mutationFn: ({ id, file }) => {
      const formData = new FormData();
      formData.append('file', file);
      return api.upload<KnowledgeDocumentResponse>(`/documents/${id}/retry-ingestion`, formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id) => api.del<void>(`/documents/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}
