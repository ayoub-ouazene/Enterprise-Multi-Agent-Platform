import { CheckCircle2, AlertTriangle, XCircle, FileSpreadsheet } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import type { ImportValidateResponse } from '../../api/types';

interface ValidationSummaryProps {
  result: ImportValidateResponse;
  onConfirm: () => void;
  onCancel: () => void;
  confirming?: boolean;
}

export function ValidationSummary({ result, onConfirm, onCancel, confirming }: ValidationSummaryProps) {
  const { total_rows, valid_rows, invalid_rows, can_confirm, import_type } = result;
  const allValid = valid_rows === total_rows && total_rows > 0;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-800">
        <div className="flex items-center gap-3">
          <div className={[
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-full',
            allValid ? 'bg-success-100 text-success-600 dark:bg-success-900 dark:text-success-300' : 'bg-warning-100 text-warning-600 dark:bg-warning-900 dark:text-warning-300',
          ].join(' ')}>
            {allValid ? <CheckCircle2 size={20} /> : <AlertTriangle size={20} />}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
              {import_type} — Validation Results
            </h3>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              {result.original_filename} · {valid_rows} valid / {total_rows} total rows
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-2 text-center">
          <div className="rounded-md bg-neutral-50 p-2 dark:bg-neutral-700">
            <p className="text-lg font-bold text-neutral-900 dark:text-neutral-100">{valid_rows}</p>
            <p className="text-[10px] uppercase tracking-wide text-neutral-500 dark:text-neutral-400">Valid</p>
          </div>
          <div className="rounded-md bg-neutral-50 p-2 dark:bg-neutral-700">
            <p className="text-lg font-bold text-neutral-900 dark:text-neutral-100">{invalid_rows}</p>
            <p className="text-[10px] uppercase tracking-wide text-neutral-500 dark:text-neutral-400">Invalid</p>
          </div>
          <div className="rounded-md bg-neutral-50 p-2 dark:bg-neutral-700">
            <p className="text-lg font-bold text-neutral-900 dark:text-neutral-100">{total_rows}</p>
            <p className="text-[10px] uppercase tracking-wide text-neutral-500 dark:text-neutral-400">Total</p>
          </div>
        </div>
      </div>

      {/* Row-level errors */}
      {invalid_rows > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 flex items-center gap-2">
            <XCircle size={14} className="text-danger-500" />
            Row Errors
          </h4>
          <div className="max-h-64 overflow-y-auto rounded-md border border-neutral-200 dark:border-neutral-700">
            <table className="min-w-full text-sm">
              <thead className="sticky top-0 bg-neutral-50 dark:bg-neutral-800">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400">Row</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400">Errors</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100 dark:divide-neutral-700">
                {result.rows
                  .filter((r) => r.status !== 'valid')
                  .map((row) => (
                    <tr key={row.row_number} className="bg-danger-50/50 dark:bg-danger-900/20">
                      <td className="px-3 py-2 text-neutral-700 dark:text-neutral-300">{row.row_number}</td>
                      <td className="px-3 py-2">
                        <ul className="list-disc pl-4 text-danger-700 dark:text-danger-300">
                          {row.errors.map((err, i) => (
                            <li key={i}>{err}</li>
                          ))}
                        </ul>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          {!can_confirm && (
            <p className="text-xs text-danger-600 dark:text-danger-400">
              Fix errors in your file and re-upload. This import type requires all rows to be valid.
            </p>
          )}
        </div>
      )}

      {/* Safe preview of valid rows */}
      {valid_rows > 0 && (
        <SafePreviewTable rows={result.rows.filter((r) => r.status === 'valid')} />
      )}

      <div className="flex flex-wrap items-center justify-end gap-3 pt-2">
        <p className="mr-auto text-xs text-neutral-500">{result.atomic ? 'Atomic import: no rows are applied if confirmation fails.' : 'Only backend-approved valid rows are applied.'}</p>
        <Button variant="ghost" onClick={onCancel} disabled={confirming}>
          Cancel
        </Button>
        <Button onClick={onConfirm} disabled={!can_confirm || confirming} isLoading={confirming}>
          {invalid_rows > 0 && can_confirm ? 'Import valid rows' : 'Confirm import'}
        </Button>
      </div>
    </div>
  );
}

function SafePreviewTable({ rows }: { rows: ImportValidateResponse['rows'] }) {
  if (rows.length === 0) return null;

  const allowed = new Set(['email', 'employee_code', 'department', 'job_title', 'employment_status', 'manager_email', 'password_provided', 'password_valid', 'department_type', 'name', 'is_active']);
  const columns = Object.keys(rows[0]?.preview ?? {}).filter((column) => allowed.has(column));

  return (
    <div>
      <h4 className="mb-2 text-sm font-semibold text-neutral-800 dark:text-neutral-200 flex items-center gap-2">
        <FileSpreadsheet size={14} />
        Preview (first {Math.min(rows.length, 5)} rows)
      </h4>
      <div className="max-h-48 overflow-x-auto rounded-md border border-neutral-200 dark:border-neutral-700">
        <table className="min-w-full text-xs">
          <thead className="sticky top-0 bg-neutral-50 dark:bg-neutral-800">
            <tr>
              {columns.map((c) => (
                <th key={c} className="px-2 py-1.5 text-left font-medium text-neutral-500 dark:text-neutral-400 capitalize">
                  {c.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100 dark:divide-neutral-700">
            {rows.slice(0, 5).map((row) => (
              <tr key={row.row_number}>
                {columns.map((c) => (
                  <td key={c} className="px-2 py-1.5 text-neutral-700 dark:text-neutral-300">
                    {typeof row.preview?.[c] === 'boolean' ? (row.preview[c] ? 'Yes' : 'No') : String((row.preview?.[c] ?? '') as string).slice(0, 40)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
