import { useState } from 'react';
import { BookOpen, Plus, Search, Trash2, RefreshCw, FileUp, ChevronDown, ChevronUp } from 'lucide-react';
import { PageContainer, PageHeader } from '../../../components/layout/PageContainer';
import { Skeleton } from '../../../components/layout/Skeleton';
import { EmptyState } from '../../../components/ui/EmptyState';
import { Modal } from '../../../components/ui/Modal';
import { ErrorState } from './components/ErrorState';
import { useDocumentList, useUploadDocument, useReplaceDocument, useRetryIngestion, useDeleteDocument } from '../../../api/hooks/useDocuments';
import { useDocumentSearch } from '../../../api/hooks/useDocumentSearch';
import { relativeTime, formatDate } from '../../../lib/formatters';
import { clsx } from 'clsx';
import {
  KnowledgeDocumentType,
  KnowledgeDocumentStatus,
  KnowledgeDepartmentScope,
  KnowledgeAccessScope,
  KnowledgeIngestionStatus,
} from '../../../api/types';
import type { KnowledgeDocumentResponse, KnowledgeSearchRequest } from '../../../api/types';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function ingestionBadge(status: KnowledgeIngestionStatus): string {
  switch (status) {
    case KnowledgeIngestionStatus.COMPLETED:
      return 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300';
    case KnowledgeIngestionStatus.PROCESSING:
      return 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300';
    case KnowledgeIngestionStatus.FAILED:
      return 'bg-danger-100 text-danger-700 dark:bg-danger-900/30 dark:text-danger-300';
    default:
      return 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300';
  }
}

export function DocumentsPage() {
  const [searchOpen, setSearchOpen] = useState(false);
  const [typeFilter, setTypeFilter] = useState<KnowledgeDocumentType | ''>('');
  const [statusFilter, setStatusFilter] = useState<KnowledgeDocumentStatus | ''>('');
  const [ingestionFilter, setIngestionFilter] = useState<KnowledgeIngestionStatus | ''>('');
  const [deptFilter, setDeptFilter] = useState<KnowledgeDepartmentScope | ''>('');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [replaceDoc, setReplaceDoc] = useState<KnowledgeDocumentResponse | null>(null);
  const [retryDoc, setRetryDoc] = useState<KnowledgeDocumentResponse | null>(null);
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);

  const filters = {
    ...(typeFilter ? { document_type: typeFilter } : {}),
    ...(statusFilter ? { status: statusFilter } : {}),
    ...(ingestionFilter ? { ingestion_status: ingestionFilter } : {}),
    ...(deptFilter ? { department: deptFilter } : {}),
    limit: 50,
  };

  const { data: documents, isLoading, error } = useDocumentList(filters);
  const upload = useUploadDocument();
  const replace = useReplaceDocument();
  const retry = useRetryIngestion();
  const remove = useDeleteDocument();

  return (
    <PageContainer>
      <PageHeader title="Knowledge Documents" description="Manage uploaded knowledge base documents and search semantic chunks." />
      <div className="mb-4 flex flex-wrap gap-3">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as KnowledgeDocumentType | '')}
          className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
        >
          <option value="">All types</option>
          {Object.values(KnowledgeDocumentType).map((t) => (
            <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as KnowledgeDocumentStatus | '')}
          className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
        >
          <option value="">All statuses</option>
          {Object.values(KnowledgeDocumentStatus).map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <select
          value={ingestionFilter}
          onChange={(e) => setIngestionFilter(e.target.value as KnowledgeIngestionStatus | '')}
          className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
        >
          <option value="">All ingestion</option>
          {Object.values(KnowledgeIngestionStatus).map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <select
          value={deptFilter}
          onChange={(e) => setDeptFilter(e.target.value as KnowledgeDepartmentScope | '')}
          className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
        >
          <option value="">All departments</option>
          {Object.values(KnowledgeDepartmentScope).map((d) => (
            <option key={d} value={d}>{d.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <button
          onClick={() => setSearchOpen(true)}
          className="ml-auto inline-flex h-9 items-center gap-2 rounded-md bg-primary-600 px-3 text-sm font-medium text-white hover:bg-primary-700"
        >
          <Search size={14} /> Search
        </button>
        <button
          onClick={() => setUploadOpen(true)}
          className="inline-flex h-9 items-center gap-2 rounded-md bg-primary-600 px-3 text-sm font-medium text-white hover:bg-primary-700"
        >
          <Plus size={14} /> Upload
        </button>
      </div>

      {error && <ErrorState message="Failed to load documents." />}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : !documents || documents.length === 0 ? (
        <EmptyState title="No documents" description="Upload knowledge documents to enable department assistants." />
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <DocumentCard
              key={doc.id}
              doc={doc}
              expanded={expandedDoc === doc.id}
              onToggle={() => setExpandedDoc(expandedDoc === doc.id ? null : doc.id)}
              onReplace={() => setReplaceDoc(doc)}
              onRetry={() => setRetryDoc(doc)}
              onDelete={() => remove.mutate(doc.id)}
            />
          ))}
        </div>
      )}

      {searchOpen && <SearchModal onClose={() => setSearchOpen(false)} />}
      {uploadOpen && <UploadModal onClose={() => setUploadOpen(false)} onSubmit={(fd) => upload.mutate(fd)} isPending={upload.isPending} />}
      {replaceDoc && <UploadModal onClose={() => setReplaceDoc(null)} onSubmit={(fd) => replace.mutate({ id: replaceDoc.id, formData: fd })} isPending={replace.isPending} mode="replace" />}
      {retryDoc && retryDoc.ingestion_status === KnowledgeIngestionStatus.FAILED && (
        <RetryModal doc={retryDoc} onClose={() => setRetryDoc(null)} onSubmit={(file) => retry.mutate({ id: retryDoc.id, file })} isPending={retry.isPending} />
      )}
    </PageContainer>
  );
}

function DocumentCard({ doc, expanded, onToggle, onReplace, onRetry, onDelete }: {
  doc: KnowledgeDocumentResponse;
  expanded: boolean;
  onToggle: () => void;
  onReplace: () => void;
  onRetry: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-800">
      <div
        className="flex cursor-pointer items-center justify-between gap-4 p-4"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400">
            <BookOpen size={14} />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-neutral-900 dark:text-neutral-100">{doc.title}</p>
            <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">
              {doc.original_filename} &middot; {formatBytes(doc.file_size_bytes)} &middot; v{doc.version}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={clsx('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', ingestionBadge(doc.ingestion_status))}>
            {doc.ingestion_status}
          </span>
          <span className="text-neutral-400 dark:text-neutral-500">
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </span>
        </div>
      </div>
      {expanded && (
        <div className="border-t border-neutral-200 px-4 py-3 dark:border-neutral-700">
          <div className="grid gap-2 text-xs text-neutral-600 dark:text-neutral-400 sm:grid-cols-2 lg:grid-cols-3">
            <div><span className="font-medium">Type:</span> {doc.document_type.replace(/_/g, ' ')}</div>
            <div><span className="font-medium">Status:</span> {doc.status}</div>
            <div><span className="font-medium">Access:</span> {doc.access_scope.replace(/_/g, ' ')}</div>
            <div><span className="font-medium">Departments:</span> {doc.department_scope.map(d => d.replace(/_/g, ' ')).join(', ')}</div>
            <div><span className="font-medium">Chunks:</span> {doc.chunk_count}</div>
            <div><span className="font-medium">MIME:</span> {doc.mime_type}</div>
            {doc.effective_date && <div><span className="font-medium">Effective:</span> {formatDate(doc.effective_date)}</div>}
            {doc.ingestion_error_safe && (
              <div className="col-span-full rounded bg-danger-50 p-2 text-danger-700 dark:bg-danger-900/20 dark:text-danger-300">
                {doc.ingestion_error_safe}
              </div>
            )}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={(e) => { e.stopPropagation(); onReplace(); }}
              className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 bg-white px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-neutral-700"
            >
              <RefreshCw size={12} /> Replace
            </button>
            {doc.ingestion_status === KnowledgeIngestionStatus.FAILED && (
              <button
                onClick={(e) => { e.stopPropagation(); onRetry(); }}
                className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 bg-white px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-neutral-700"
              >
                <FileUp size={12} /> Retry Ingestion
              </button>
            )}
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(); }}
              className="inline-flex items-center gap-1.5 rounded-md border border-danger-200 bg-white px-2.5 py-1.5 text-xs font-medium text-danger-600 hover:bg-danger-50 dark:border-danger-800 dark:bg-neutral-800 dark:text-danger-400 dark:hover:bg-danger-900/20"
            >
              <Trash2 size={12} /> Delete
            </button>
          </div>
          <p className="mt-2 text-xs text-neutral-400 dark:text-neutral-500">Uploaded {relativeTime(doc.created_at)}</p>
        </div>
      )}
    </div>
  );
}

function SearchModal({ onClose }: { onClose: () => void }) {
  const [query, setQuery] = useState('');
  const [dept, setDept] = useState<KnowledgeDepartmentScope | ''>('');
  const search = useDocumentSearch();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    const payload: KnowledgeSearchRequest = {
      query_text: query.trim(),
      ...(dept ? { department: dept } : {}),
      top_k: 5,
    };
    search.mutate(payload);
  }

  return (
    <Modal title="Semantic Search" isOpen onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">Query</label>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
            placeholder="Search knowledge base..."
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">Department</label>
          <select
            value={dept}
            onChange={(e) => setDept(e.target.value as KnowledgeDepartmentScope | '')}
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
          >
            <option value="">Any</option>
            {Object.values(KnowledgeDepartmentScope).map((d) => (
              <option key={d} value={d}>{d.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={search.isPending || !query.trim()}
          className="inline-flex h-9 items-center gap-2 rounded-md bg-primary-600 px-4 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          <Search size={14} /> {search.isPending ? 'Searching...' : 'Search'}
        </button>
      </form>
      {search.data && (
        <div className="mt-4 space-y-3">
          <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400">{search.data.length} results</p>
          {search.data.map((r) => (
            <div key={r.record_id} className="rounded-md border border-neutral-200 p-3 dark:border-neutral-700 dark:bg-neutral-800/50">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{r.title}</p>
                <span className="text-xs text-neutral-500">score {r.similarity_score.toFixed(3)}</span>
              </div>
              <p className="mt-1 line-clamp-3 text-xs text-neutral-600 dark:text-neutral-400">{r.chunk_text}</p>
              <div className="mt-1 flex gap-2 text-xs text-neutral-500">
                <span>{r.document_type.replace(/_/g, ' ')}</span>
                <span>&middot;</span>
                <span>{r.department_scope.map(d => d.replace(/_/g, ' ')).join(', ')}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}

function UploadModal({ onClose, onSubmit, isPending, mode = 'upload' }: {
  onClose: () => void;
  onSubmit: (formData: FormData) => void;
  isPending: boolean;
  mode?: 'upload' | 'replace';
}) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [docType, setDocType] = useState<KnowledgeDocumentType>(KnowledgeDocumentType.POLICY);
  const [deptScopes, setDeptScopes] = useState<KnowledgeDepartmentScope[]>([KnowledgeDepartmentScope.SHARED]);
  const [access, setAccess] = useState<KnowledgeAccessScope>(KnowledgeAccessScope.ALL_AUTHENTICATED);
  const [effectiveDate, setEffectiveDate] = useState('');

  function toggleDept(d: KnowledgeDepartmentScope) {
    if (d === KnowledgeDepartmentScope.SHARED) {
      setDeptScopes([KnowledgeDepartmentScope.SHARED]);
      return;
    }
    setDeptScopes((prev) => {
      const filtered = prev.filter((x) => x !== KnowledgeDepartmentScope.SHARED);
      if (filtered.includes(d)) return filtered.filter((x) => x !== d);
      if (filtered.length >= 5) return filtered;
      return [...filtered, d];
    });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title || file.name);
    formData.append('document_type', docType);
    deptScopes.forEach((d) => formData.append('department_scope', d));
    formData.append('access_scope', access);
    if (effectiveDate) formData.append('effective_date', effectiveDate);
    formData.append('custom_metadata', '{}');
    onSubmit(formData);
  }

  return (
    <Modal title={mode === 'replace' ? 'Replace Document' : 'Upload Document'} isOpen onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">File</label>
          <input
            type="file"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) { setFile(f); if (!title) setTitle(f.name); } }}
            className="w-full text-sm text-neutral-600 file:mr-3 file:rounded-md file:border-0 file:bg-primary-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-primary-700 dark:text-neutral-300 dark:file:bg-primary-900/20 dark:file:text-primary-300"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">Title</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
            placeholder="Document title"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">Type</label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value as KnowledgeDocumentType)}
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
            >
              {Object.values(KnowledgeDocumentType).map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">Access</label>
            <select
              value={access}
              onChange={(e) => setAccess(e.target.value as KnowledgeAccessScope)}
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
            >
              {Object.values(KnowledgeAccessScope).map((a) => (
                <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">Department Scope</label>
          <div className="flex flex-wrap gap-2">
            {Object.values(KnowledgeDepartmentScope).map((d) => (
              <label key={d} className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs dark:border-neutral-600 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={deptScopes.includes(d)}
                  onChange={() => toggleDept(d)}
                  className="h-3.5 w-3.5 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-neutral-700 dark:text-neutral-300">{d.replace(/_/g, ' ')}</span>
              </label>
            ))}
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">Effective Date</label>
          <input
            type="date"
            value={effectiveDate}
            onChange={(e) => setEffectiveDate(e.target.value)}
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
          />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isPending || !file}
            className="inline-flex h-9 items-center gap-2 rounded-md bg-primary-600 px-4 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {isPending ? (mode === 'replace' ? 'Replacing...' : 'Uploading...') : (mode === 'replace' ? 'Replace' : 'Upload')}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function RetryModal({ doc, onClose, onSubmit, isPending }: {
  doc: KnowledgeDocumentResponse;
  onClose: () => void;
  onSubmit: (file: File) => void;
  isPending: boolean;
}) {
  const [file, setFile] = useState<File | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (file) onSubmit(file);
  }

  return (
    <Modal title={`Retry Ingestion: ${doc.title}`} isOpen onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Re-upload the file to retry ingestion for <strong>{doc.title}</strong>.
        </p>
        <input
          type="file"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="w-full text-sm text-neutral-600 file:mr-3 file:rounded-md file:border-0 file:bg-primary-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-primary-700 dark:text-neutral-300 dark:file:bg-primary-900/20 dark:file:text-primary-300"
        />
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isPending || !file}
            className="inline-flex h-9 items-center gap-2 rounded-md bg-primary-600 px-4 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {isPending ? 'Retrying...' : 'Retry Ingestion'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
