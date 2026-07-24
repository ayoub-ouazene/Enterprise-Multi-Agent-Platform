import { useState } from 'react';
import { Package, Database, Info } from 'lucide-react';
import { ImportFileUploader } from '../components/ImportFileUploader';
import { ValidationSummary } from '../components/ValidationSummary';
import { useValidateImport, useConfirmImport, useImportTemplate } from '../../api/hooks/useOnboarding';
import { useImportPolling } from '../hooks/useImportPolling';
import type { ImportValidateResponse } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';

type OptionalImportType = 'assets' | 'software_catalog' | 'budgets' | 'suppliers' | 'company_holidays' | 'staffing_rules';

interface ImportCard {
  id: OptionalImportType;
  label: string;
  description: string;
}

const OPTIONAL_IMPORTS: ImportCard[] = [
  { id: 'assets', label: 'Asset Inventory', description: 'Import IT assets, equipment, and locations.' },
  { id: 'software_catalog', label: 'Software Catalog', description: 'Software and license management.' },
  { id: 'budgets', label: 'Budgets', description: 'Financial budgets and plans.' },
  { id: 'suppliers', label: 'Suppliers', description: 'Vendor and supplier directory.' },
  { id: 'company_holidays', label: 'Company Holidays', description: 'Paid and unpaid holiday calendar.' },
  { id: 'staffing_rules', label: 'Staffing Rules', description: 'Minimum headcount rules by department.' },
];

export function OptionalDataStep() {
  const [activeImport, setActiveImport] = useState<OptionalImportType | null>(null);
  const [, setFileMap] = useState<Record<string, File>>({});
  const [resultMap, setResultMap] = useState<Record<string, ImportValidateResponse>>({});
  const [errorMap, setErrorMap] = useState<Record<string, string>>({});

  const validateMutation = useValidateImport();
  const confirmMutation = useConfirmImport();
  const { data: template } = useImportTemplate(activeImport ?? '');

  const activeJobId = activeImport ? resultMap[activeImport]?.import_job_id ?? null : null;
  const { completed: importCompleted } = useImportPolling(activeJobId);

  async function handleFileSelect(importType: OptionalImportType, file: File) {
    setFileMap((prev) => ({ ...prev, [importType]: file }));
    setErrorMap((prev) => ({ ...prev, [importType]: '' }));
    setResultMap((prev) => ({ ...prev, [importType]: undefined as unknown as ImportValidateResponse }));
    try {
      const result = await validateMutation.mutateAsync({ importType, file });
      setResultMap((prev) => ({ ...prev, [importType]: result }));
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Validation failed';
      setErrorMap((prev) => ({ ...prev, [importType]: msg }));
    }
  }

  async function handleConfirm(importType: OptionalImportType) {
    const result = resultMap[importType];
    if (!result) return;
    try {
      await confirmMutation.mutateAsync(result.import_job_id);
      setResultMap((prev) => ({ ...prev, [importType]: undefined as unknown as ImportValidateResponse }));
      setFileMap((prev) => ({ ...prev, [importType]: undefined as unknown as File }));
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Import failed';
      setErrorMap((prev) => ({ ...prev, [importType]: msg }));
    }
  }

  const templateUrl = template
    ? `data:text/csv;charset=utf-8,${encodeURIComponent(template.csv_header)}`
    : undefined;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-300">
          <Database size={20} />
        </div>
        <div>
          <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Optional Data</h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            Import additional data to enrich your company setup. These steps are optional.
          </p>
        </div>
      </div>

      <div className="rounded-md bg-info-50 p-3 text-xs text-info-800 dark:bg-info-900/30 dark:text-info-200 flex items-start gap-2">
        <Info size={14} className="mt-0.5 shrink-0" />
        <p>You can skip this step and import these later from the Admin panel.</p>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {OPTIONAL_IMPORTS.map((card) => {
          const isActive = activeImport === card.id;
          const hasResult = !!resultMap[card.id];
          const isCompleted = importCompleted && activeImport === card.id;
          return (
            <div
              key={card.id}
              className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-800"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300">
                    <Package size={16} />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{card.label}</h3>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">{card.description}</p>
                  </div>
                </div>
                {!isActive && !hasResult && (
                  <Button size="sm" variant="secondary" onClick={() => setActiveImport(card.id)}>
                    Import
                  </Button>
                )}
              </div>

              {isActive && (
                <div className="mt-4 border-t border-neutral-100 pt-4 dark:border-neutral-700">
                  {hasResult ? (
                    <ValidationSummary
                      result={resultMap[card.id]}
                      onConfirm={() => handleConfirm(card.id)}
                      onCancel={() => {
                        setActiveImport(null);
                        setResultMap((prev) => ({ ...prev, [card.id]: undefined as unknown as ImportValidateResponse }));
                      }}
                      confirming={confirmMutation.isPending}
                    />
                  ) : isCompleted ? (
                    <Alert variant="success" title="Import completed">Data imported successfully.</Alert>
                  ) : (
                    <ImportFileUploader
                      importType={card.id}
                      templateUrl={templateUrl}
                      onFileSelect={(file) => handleFileSelect(card.id, file)}
                      isLoading={validateMutation.isPending}
                      error={errorMap[card.id]}
                      onClearError={() => setErrorMap((prev) => ({ ...prev, [card.id]: '' }))}
                    />
                  )}
                  <div className="mt-3 flex justify-end">
                    <Button variant="ghost" size="sm" onClick={() => setActiveImport(null)}>
                      Close
                    </Button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
