import { Card, CardContent } from '../../components/ui/Card';

interface DecisionPackageViewProps {
  package: Record<string, unknown>;
}

export function DecisionPackageView({ package: pkg }: DecisionPackageViewProps) {
  if (!pkg || Object.keys(pkg).length === 0) {
    return (
      <p className="text-sm italic text-neutral-500 dark:text-neutral-400">
        No additional context provided.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {Object.entries(pkg).map(([key, value]) => (
        <Card key={key} className="p-3">
          <CardContent className="text-sm">
            <span className="block text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              {formatKey(key)}
            </span>
            <span className="mt-1 block text-neutral-900 dark:text-neutral-100">
              {renderValue(value)}
            </span>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function formatKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .replace(/^\w/, (c) => c.toUpperCase());
}

function renderValue(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
