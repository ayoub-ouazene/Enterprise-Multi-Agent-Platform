import { useMutation } from '@tanstack/react-query';
import { api } from '../client';
import type { AssistantMessageRequest, AssistantMessageResponse } from '../types';

async function sendAssistantMessage(
  payload: AssistantMessageRequest,
): Promise<AssistantMessageResponse> {
  return api.post<AssistantMessageResponse>('/assistant/message', payload);
}

export function useAssistantMessage() {
  return useMutation<
    AssistantMessageResponse,
    Error,
    AssistantMessageRequest
  >({
    mutationFn: sendAssistantMessage,
  });
}
