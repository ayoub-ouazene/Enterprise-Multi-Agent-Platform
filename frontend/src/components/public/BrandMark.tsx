import { Link } from 'react-router-dom';
import { Network } from 'lucide-react';

export function BrandMark({ inverted = false }: { inverted?: boolean }) {
  return (
    <Link
      to="/"
      className="inline-flex items-center gap-2.5 rounded-lg"
      aria-label="TellUS AI home"
    >
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-600 text-white shadow-lg shadow-primary-600/20">
        <Network size={19} aria-hidden="true" />
      </span>
      <span className={`text-[17px] font-bold tracking-tight ${inverted ? 'text-white' : 'text-neutral-950 dark:text-white'}`}>
        TellUS <span className="text-primary-500">AI</span>
      </span>
    </Link>
  );
}
