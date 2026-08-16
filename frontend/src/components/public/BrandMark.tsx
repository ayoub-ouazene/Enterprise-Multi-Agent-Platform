import { clsx } from 'clsx';
import logo from '../../assets/logo.png';

/**
 * Brand mark (logo + wordmark). Returns a plain container — callers are
 * responsible for wrapping it in a Link so nested anchors are avoided
 * (PublicHeader and Header wrap it; standalone usages add their own link).
 */
export function BrandMark({ tabIndex, className, inverted }: { inverted?: boolean; tabIndex?: number; className?: string }) {
  return (
    <span
      className="inline-flex items-center gap-2.5 rounded-lg"
      tabIndex={tabIndex}
    >
      <img src={logo} alt="Orchestra" className={clsx('h-9 w-9 shrink-0', className)} />
      <span className={`text-[17px] font-bold tracking-tight ${inverted ? 'text-neutral-900 dark:text-white' : 'text-white'}`}>
        Orchestra
      </span>
    </span>
  );
}
