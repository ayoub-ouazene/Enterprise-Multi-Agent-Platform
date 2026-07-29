import { Link } from 'react-router-dom';
import { BrandMark } from './BrandMark';

export function PublicFooter() {
  return (
    <footer className="relative border-t border-neutral-200 bg-white py-10 dark:border-neutral-800 dark:bg-neutral-950">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary-500/30 to-transparent" aria-hidden="true" />
      <div className="app-container flex flex-col gap-8 md:flex-row md:items-center md:justify-between">
        <div>
          <BrandMark />
          <p className="mt-3 max-w-sm text-sm leading-6 text-neutral-500 dark:text-neutral-400">
            Coordinated enterprise requests with company control at every step.
          </p>
        </div>
        <nav className="flex flex-wrap gap-x-6 gap-y-3 text-sm font-medium text-neutral-600 dark:text-neutral-300" aria-label="Footer navigation">
          <a href="/#product" className="transition-colors duration-ui hover:text-primary-600">Product</a>
          <a href="/#security" className="transition-colors duration-ui hover:text-primary-600">Security</a>
          <a href="/#workflow" className="transition-colors duration-ui hover:text-primary-600">How it works</a>
          <Link to="/login" className="transition-colors duration-ui hover:text-primary-600">Sign in</Link>
          <Link to="/signup" className="transition-colors duration-ui hover:text-primary-600">Create workspace</Link>
        </nav>
      </div>
      <div className="app-container mt-8 border-t border-neutral-200 pt-6 text-sm text-neutral-500 dark:border-neutral-800 dark:text-neutral-500">
        © {new Date().getFullYear()} Orchestra. Enterprise multi-agent platform.
      </div>
    </footer>
  );
}
