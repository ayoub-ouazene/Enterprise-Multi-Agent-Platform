import { useState } from 'react';
import { ShieldCheck, Upload, CheckCircle2, AlertCircle } from 'lucide-react';
import { useDocuments, useUploadDocument, usePolicyReadiness } from '../../api/hooks/useOnboarding';
import { ApiErrorException } from '../../api/errors';
import type { OnboardingStatusDetailed } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Skeleton } from '../../components/layout/Skeleton';
import { Alert } from '../../components/ui/Alert';

interface PoliciesStepProps {
  status: OnboardingStatusDetailed;
}

const DEPT_LABELS: Record<string, string> = {
  customer_support: 'Customer Support',
  hr: 'Human Resources',
  it: 'Information Technology',
  finance: 'Finance',
  procurement: 'Procurement',
};

export function PoliciesStep({ status }: PoliciesStepProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [scopeKey, setScopeKey] = useState('shared');
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { data: documents, isLoading: docsLoading } = useDocuments();
  const { data: readiness } = usePolicyReadiness();
  const upload = useUploadDocument();

  const policyItem = status.items.find((i) => i.requirement === 'policies');

  async function handleUpload() {
    if (!file || !title.trim()) return;
    setUploadError(null);
    try {
      await upload.mutateAsync({
        file,
        title: title.trim(),
        document_type: 'policy',
        department_scope: scopeKey === 'shared' ? ['shared'] : [scopeKey],
        access_scope: 'all_authenticated',
      });
      setFile(null);
      setTitle('');
    } catch (e) {
      let msg = 'Upload failed';
      if (e instanceof ApiErrorException) {
        if (e.error.fieldErrors && Object.keys(e.error.fieldErrors).length > 0) {
          const fields = Object.entries(e.error.fieldErrors)
            .map(([field, errors]) => `${field}: ${errors.join(', ')}`)
            .join('; ');
          msg = `Validation failed: ${fields}`;
        } else {
          msg = e.error.message;
        }
      } else if (e instanceof Error) {
        msg = e.message;
      }
      setUploadError(msg);
    }
  }

  const policyDocs = documents?.filter((d) => d.document_type === 'policy') ?? [];

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-300">
          <ShieldCheck size={20} />
        </div>
        <div>
          <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Policies</h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">Upload policy documents for each enabled department.</p>
        </div>
      </div>

      {policyItem?.satisfied ? (
        <Alert variant="success" title="Policies complete">
          All enabled departments are covered by active ingested policies.
        </Alert>
      ) : (
        <Alert variant="warning" title="Policies missing">
          {policyItem?.details ?? 'Upload policies for each enabled department.'}
        </Alert>
      )}

      {readiness && (
        <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-800">
          <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">Department Coverage</h3>
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {Object.entries(readiness.department_coverage).map(([dept, covered]) => (
              <div
                key={dept}
                className="flex items-center gap-2 rounded-md bg-neutral-50 p-2 dark:bg-neutral-700"
              >
                {covered ? (
                  <CheckCircle2 size={14} className="text-success-500" />
                ) : (
                  <AlertCircle size={14} className="text-warning-500" />
                )}
                <span className="text-xs text-neutral-700 dark:text-neutral-300">
                  {DEPT_LABELS[dept] ?? dept}
                </span>
                {covered ? (
                  <span className="ml-auto text-[10px] font-medium text-success-600 dark:text-success-300">Covered</span>
                ) : (
                  <span className="ml-auto text-[10px] font-medium text-warning-600 dark:text-warning-300">Missing</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload form */}
      <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-800">
        <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">Upload Policy</h3>
        <div className="mt-3 space-y-3">
          <div>
            <label className="text-xs font-medium text-neutral-500 dark:text-neutral-400">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Employee Code of Conduct"
              className="mt-1 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-neutral-600 dark:bg-neutral-700 dark:text-neutral-100"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-neutral-500 dark:text-neutral-400">Department Scope</label>
            <select
              value={scopeKey}
              onChange={(e) => setScopeKey(e.target.value)}
              className="mt-1 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-500 focus:outline-none dark:border-neutral-600 dark:bg-neutral-700 dark:text-neutral-100"
            >
              <option value="shared">All Departments (Shared)</option>
              {Object.entries(DEPT_LABELS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-neutral-500 dark:text-neutral-400">File</label>
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(e) => { setFile(e.target.files?.[0] ?? null); }}
              className="mt-1 block w-full text-sm text-neutral-600 file:mr-4 file:rounded-md file:border-0 file:bg-primary-50 file:px-3 file:py-2 file:text-xs file:font-medium file:text-primary-700 hover:file:bg-primary-100 dark:text-neutral-400 dark:file:bg-primary-900 dark:file:text-primary-300"
            />
          </div>
          {uploadError && (
            <Alert variant="error" title="Upload failed">{uploadError}</Alert>
          )}
          <Button
            onClick={handleUpload}
            disabled={!file || !title.trim() || upload.isPending}
            isLoading={upload.isPending}
          >
            <span className="inline-flex items-center gap-1.5">
              <Upload size={14} />
              Upload Policy
            </span>
          </Button>
        </div>
      </div>

      {/* Existing policies */}
      {docsLoading ? (
        <Skeleton variant="rect" className="h-20 w-full" />
      ) : policyDocs.length > 0 ? (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">Existing Policies</h3>
          <div className="divide-y divide-neutral-100 rounded-lg border border-neutral-200 bg-white dark:divide-neutral-700 dark:border-neutral-700 dark:bg-neutral-800">
            {policyDocs.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{doc.title}</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">
                    {doc.department_scope.join(', ')} · {doc.ingestion_status}
                  </p>
                </div>
                <span
                  className={[
                    'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                    doc.is_active
                      ? 'bg-success-100 text-success-700 dark:bg-success-900 dark:text-success-300'
                      : 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400',
                  ].join(' ')}
                >
                  {doc.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
