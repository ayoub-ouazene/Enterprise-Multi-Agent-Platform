import { useState } from 'react';
import { Users, Sparkles } from 'lucide-react';
import type { OnboardingStatusDetailed, ImportValidateResponse } from '../../api/types';
import { useValidateImport, useConfirmImport, useImportTemplate } from '../../api/hooks/useOnboarding';
import { useImportPolling } from '../hooks/useImportPolling';
import { ImportFileUploader } from '../components/ImportFileUploader';
import { ValidationSummary } from '../components/ValidationSummary';
import { Skeleton } from '../../components/layout/Skeleton';
import { Alert } from '../../components/ui/Alert';

interface EmployeesStepProps {
  status: OnboardingStatusDetailed;
}

export function EmployeesStep({ status }: EmployeesStepProps) {
  const [, setFile] = useState<File | null>(null);
  const [validationResult, setValidationResult] = useState<ImportValidateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const validateMutation = useValidateImport();
  const confirmMutation = useConfirmImport();
  const { data: template } = useImportTemplate('employees');

  const validationJobId = validationResult?.import_job_id ?? null;
  const { completed: importCompleted } = useImportPolling(validationJobId);

  const employeeItem = status.items.find((i) => i.requirement === 'employees');

  async function handleFileSelect(selectedFile: File) {
    setFile(selectedFile);
    setError(null);
    setValidationResult(null);
    try {
      const result = await validateMutation.mutateAsync({ importType: 'employees', file: selectedFile });
      setValidationResult(result);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Validation failed';
      setError(msg);
      setFile(null);
    }
  }

  async function handleConfirm() {
    if (!validationResult) return;
    setError(null);
    try {
      await confirmMutation.mutateAsync(validationResult.import_job_id);
      setValidationResult(null);
      setFile(null);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Import failed';
      setError(msg);
    }
  }

  const templateUrl = template
    ? `data:text/csv;charset=utf-8,${encodeURIComponent(template.csv_header)}`
    : undefined;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-300">
          <Users size={20} />
        </div>
        <div>
          <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Employees</h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">Import your team via CSV or XLSX.</p>
        </div>
      </div>

      {employeeItem?.satisfied ? (
        <Alert variant="success" title="Employees imported">
          {employeeItem.details}
        </Alert>
      ) : (
        <Alert variant="info" title="At least one employee required">
          Upload a spreadsheet with your employee data to continue.
        </Alert>
      )}

      {validateMutation.isPending && (
        <div className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-800">
          <Skeleton variant="circle" className="h-8 w-8" />
          <div>
            <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Validating file...</p>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">Checking rows and data format</p>
          </div>
        </div>
      )}

      {validationResult && !confirmMutation.isPending && !importCompleted ? (
        <ValidationSummary
          result={validationResult}
          onConfirm={handleConfirm}
          onCancel={() => { setValidationResult(null); setFile(null); }}
          confirming={confirmMutation.isPending || validateMutation.isPending}
        />
      ) : confirmMutation.isSuccess || importCompleted ? (
        <div className="flex items-center gap-3 rounded-lg border border-success-200 bg-success-50 p-4 dark:border-success-800 dark:bg-success-900/20">
          <Sparkles size={18} className="text-success-600 dark:text-success-300" />
          <p className="text-sm text-success-800 dark:text-success-200">Import completed successfully.</p>
        </div>
      ) : (
        <ImportFileUploader
          importType="employees"
          templateUrl={templateUrl}
          onFileSelect={handleFileSelect}
          isLoading={validateMutation.isPending}
          error={error}
          onClearError={() => setError(null)}
        />
      )}

      {template?.columns && (
        <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-800">
          <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">Expected Columns</h3>
          <ul className="mt-2 grid grid-cols-2 gap-1 text-xs text-neutral-600 dark:text-neutral-400 sm:grid-cols-3">
            {template.columns.map((col) => (
              <li key={col.name} className="flex items-center gap-1.5">
                <span className={col.required ? 'text-danger-500' : 'text-neutral-400'}>*</span>
                {col.name}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
