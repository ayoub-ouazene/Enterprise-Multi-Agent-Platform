import { Link } from 'react-router-dom';
import logo from '../../assets/logo.svg';

export function BrandMark({ inverted = false }: { inverted?: boolean }) {
  return (
    <Link
      to="/"
      className="inline-flex items-center gap-2.5 rounded-lg"
      aria-label="Orchestra home"
    >
      <img src={logo} alt="" className="h-9 w-9" aria-hidden="true" />
      <span className={`text-[17px] font-bold tracking-tight ${inverted ? 'text-white' : 'text-neutral-950 dark:text-white'}`}>
        Orchestra
      </span>
    </Link>
  );
}
