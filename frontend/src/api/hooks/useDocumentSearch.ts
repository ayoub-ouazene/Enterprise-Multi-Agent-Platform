import { useMutation } from '@tanstack/react-query';
import { api } from '../client';
import { KnowledgeChunkResult, KnowledgeSearchRequest } from '../types';

export function useDocumentSearch() {
  return useMutation<KnowledgeChunkResult[], Error, KnowledgeSearchRequest>({
    mutationFn: (payload) => api.post<KnowledgeChunkResult[]>('/documents/search', payload),
  });
}
