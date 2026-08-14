import { Link } from 'react-router-dom';
import logo from '../../assets/logo.png';

export function BrandMark({ tabIndex }: { inverted?: boolean; tabIndex?: number }) {
  return (
    <Link
      to="/"
      className="inline-flex items-center gap-2.5 rounded-lg"
      aria-label="Orchestra home"
      tabIndex={tabIndex}
    >
      <img src={logo} alt="" className="h-9 w-9" aria-hidden="true" />
      <span className="text-[17px] font-bold tracking-tight text-white">
        Orchestra
      </span>
    </Link>
  );
}
