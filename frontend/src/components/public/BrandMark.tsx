import { Link } from 'react-router-dom';
import { clsx } from 'clsx';
import logo from '../../assets/logo.png';

export function BrandMark({ tabIndex, className, inverted }: { inverted?: boolean; tabIndex?: number; className?: string }) {
  return (
    <Link
      to="/"
      className="inline-flex items-center gap-2.5 rounded-lg"
      aria-label="Orchestra home"
      tabIndex={tabIndex}
    >
      <img src={logo} alt="" className={clsx('h-9 w-9', className)} aria-hidden="true" />
      <span className={`text-[17px] font-bold tracking-tight ${inverted ? 'text-neutral-900 dark:text-white' : 'text-white'}`}>
        Orchestra
      </span>
    </Link>
  );
}
