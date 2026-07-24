import { useRef, useState, useCallback } from 'react';
import { Upload, FileSpreadsheet, AlertTriangle, XCircle } from 'lucide-react';
import { Alert } from '../../components/ui/Alert';

const MAX_FILE_SIZE_MB = 25;
const ACCEPTED_TYPES = [
  'text/csv',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.ms-excel',
];

interface ImportFileUploaderProps {
  importType: string;
  templateUrl?: string;
  onFileSelect: (file: File) => void;
  isLoading?: boolean;
  error?: string | null;
  onClearError?: () => void;
}

export function ImportFileUploader({
  importType,
  templateUrl,
  onFileSelect,
  isLoading,
  error,
  onClearError,
}: ImportFileUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  const validateFile = useCallback((file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type) && !file.name.toLowerCase().endsWith('.csv')) {
      return 'Please upload a CSV or XLSX file';
    }
    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      return `File exceeds ${MAX_FILE_SIZE_MB}MB limit`;
    }
    return null;
  }, []);

  const handleFile = useCallback(
    (file: File) => {
      setFileError(null);
      onClearError?.();
      const err = validateFile(file);
      if (err) {
        setFileError(err);
        return;
      }
      onFileSelect(file);
    },
    [validateFile, onFileSelect, onClearError]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFile(file);
      }
      // Clear input so same file can be re-selected
      e.target.value = '';
    },
    [handleFile]
  );

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
        className={[
          'flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors cursor-pointer',
          'hover:border-primary-400 hover:bg-primary-50/50 dark:hover:border-primary-600 dark:hover:bg-primary-900/20',
          dragOver ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30' : 'border-neutral-300 bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-800/50',
        ].join(' ')}
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-300">
          <Upload size={24} />
        </div>
        <p className="mt-3 text-sm font-medium text-neutral-900 dark:text-neutral-100">
          Drop your {importType} file here, or click to browse
        </p>
        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
          CSV or XLSX up to {MAX_FILE_SIZE_MB}MB
        </p>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx"
        className="sr-only"
        onChange={handleChange}
        disabled={isLoading}
        aria-label="Upload import file"
      />

      {templateUrl && (
        <div className="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
          <FileSpreadsheet size={14} />
          <a
            href={templateUrl}
            download
            className="underline hover:text-primary-600 dark:hover:text-primary-400"
            onClick={(e) => e.stopPropagation()}
          >
            Download template
          </a>
        </div>
      )}

      {(fileError || error) && (
        <Alert variant="error" title="Upload error">
          <div className="flex items-start gap-2">
            <AlertTriangle size={14} className="mt-0.5 shrink-0" />
            <p>{fileError || error}</p>
          </div>
          {(fileError || error) && (
            <button
              onClick={() => { setFileError(null); onClearError?.(); }}
              className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-danger-700 hover:underline dark:text-danger-300"
            >
              <XCircle size={12} /> Dismiss
            </button>
          )}
        </Alert>
      )}
    </div>
  );
}
