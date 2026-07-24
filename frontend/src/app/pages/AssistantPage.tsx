import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, User, Loader2, Bot, ArrowRight, ExternalLink } from 'lucide-react';
import { useAssistantMessage } from '../../api/hooks/useAssistant';
import type { AssistantMessageResponse } from '../../api/types';
import { RouterMessageCategory } from '../../api/types';
import { Button } from '../../components/ui/Button';

type ChatRole = 'user' | 'assistant';

interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  meta?: AssistantMessageResponse;
  timestamp: Date;
}

const QUICK_ACTIONS = [
  { label: 'How do I submit an IT ticket?', value: 'How do I submit an IT support ticket?' },
  { label: 'Check my leave balance', value: 'How many leave days do I have remaining?' },
  { label: 'New expense request', value: 'I need to submit an expense reimbursement request.' },
  { label: 'Hardware request', value: 'I need to request a new laptop.' },
];

let idCounter = 0;
function nextId() {
  return String(++idCounter);
}

export function AssistantPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: nextId(),
      role: 'assistant',
      content:
        'Hi! I am your Platform Assistant. I can help route requests, answer questions about company policies, and guide you through platform workflows. What can I help you with today?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mutation = useAssistantMessage();
  const activeRequestId = useRef<string | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const appendMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const handleSend = async (textOverride?: string) => {
    const text = (textOverride ?? input).trim();
    if (!text || mutation.isPending) return;

    appendMessage({
      id: nextId(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    });

    if (!textOverride) {
      setInput('');
    }

    try {
      const response = await mutation.mutateAsync({
        message: text,
        request_id: activeRequestId.current,
      });

      if (response.request_id) {
        activeRequestId.current = response.request_id;
      }

      const assistantMsg: ChatMessage = {
        id: nextId(),
        role: 'assistant',
        content: response.response,
        meta: response,
        timestamp: new Date(),
      };

      appendMessage(assistantMsg);
    } catch {
      appendMessage({
        id: nextId(),
        role: 'assistant',
        content:
          'I am experiencing a temporary issue. Please try again in a moment.',
        timestamp: new Date(),
      });
    } finally {
      setTimeout(scrollToBottom, 50);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSend();
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col bg-neutral-50 dark:bg-neutral-900">
      <div className="border-b border-neutral-200 bg-white px-6 py-4 dark:border-neutral-800 dark:bg-neutral-900">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-300">
            <Bot size={16} />
          </div>
          <div>
            <h1 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
              Platform Assistant
            </h1>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              Ask questions, submit requests, or get guidance
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        <div className="mx-auto max-w-3xl space-y-4">
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              onNavigateToRequest={(id) => navigate(`/app/requests/${id}`)}
            />
          ))}
          {mutation.isPending && (
            <div className="flex items-center gap-2 py-2">
              <Loader2 size={16} className="animate-spin text-neutral-400" />
              <span className="text-xs text-neutral-400">Assistant is thinking...</span>
            </div>
          )}
          <div ref={messagesEndRef} />

          {messages.length <= 1 && (
            <div className="grid grid-cols-1 gap-2 pt-4 sm:grid-cols-2">
              {QUICK_ACTIONS.map((action) => (
                <button
                  key={action.label}
                  onClick={() => handleSend(action.value)}
                  className="flex items-center justify-between rounded-lg border border-neutral-200 bg-white px-4 py-3 text-left text-sm text-neutral-700 transition hover:border-primary-300 hover:bg-primary-50 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:border-primary-700 dark:hover:bg-primary-900/20"
                >
                  <span>{action.label}</span>
                  <ArrowRight size={14} className="text-neutral-400" />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
        <form onSubmit={handleSubmit} className="mx-auto flex max-w-3xl items-end gap-2">
          <div className="relative flex-1">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Type your message..."
              className="w-full rounded-lg border border-neutral-300 bg-white px-4 py-3 text-sm text-neutral-900 shadow-sm transition focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100 dark:focus:border-primary-500"
              disabled={mutation.isPending}
            />
          </div>
          <Button
            type="submit"
            isLoading={mutation.isPending}
            disabled={mutation.isPending || !input.trim()}
            className="h-10 w-10 rounded-full p-0"
          >
            <Send size={16} />
          </Button>
        </form>
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  onNavigateToRequest,
}: {
  message: ChatMessage;
  onNavigateToRequest: (id: string) => void;
}) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
          isUser
            ? 'bg-neutral-200 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300'
            : 'bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-300'
        }`}
      >
        {isUser ? <User size={14} /> : <Bot size={14} />}
      </div>
      <div
        className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? 'bg-primary-600 text-white dark:bg-primary-700'
            : 'border border-neutral-200 bg-white text-neutral-800 shadow-xs dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-200'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>

        {!isUser && message.meta && (
          <MessageMeta
            meta={message.meta}
            onNavigateToRequest={onNavigateToRequest}
          />
        )}
      </div>
    </div>
  );
}

function MessageMeta({
  meta,
  onNavigateToRequest,
}: {
  meta: AssistantMessageResponse;
  onNavigateToRequest: (id: string) => void;
}) {
  return (
    <div className="mt-2 space-y-1.5 border-t border-neutral-100 pt-2 dark:border-neutral-700/60">
      {meta.request_id && (
        <button
          onClick={() => onNavigateToRequest(meta.request_id!)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-primary-600 hover:underline dark:text-primary-400"
        >
          <ExternalLink size={12} />
          View request {meta.request_id.slice(0, 8)}
        </button>
      )}

      {meta.owner_department && (
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          Routed to: <span className="font-medium capitalize">{meta.owner_department.replace(/_/g, ' ')}</span>
        </p>
      )}

      {meta.needs_clarification && meta.clarification_question && (
        <div className="rounded-md bg-warning-50 p-2 text-xs text-warning-700 dark:bg-warning-900/20 dark:text-warning-300">
          <p className="font-medium">Clarification needed:</p>
          <p>{meta.clarification_question}</p>
        </div>
      )}

      {meta.message_category === RouterMessageCategory.UNSUPPORTED && (
        <div className="rounded-md bg-danger-50 p-2 text-xs text-danger-700 dark:bg-danger-900/20 dark:text-danger-300">
          <p>This request is not supported by the platform.</p>
        </div>
      )}
    </div>
  );
}
