import { Link } from 'react-router-dom';
import { BrandMark } from './BrandMark';

export function PublicFooter() {
  return (
    <footer className="relative z-10 bg-neutral-950">
      {/* Gradient divider separating the page content from the footer */}
      <div className="h-px w-full bg-gradient-to-r from-transparent via-primary-500/50 to-transparent" aria-hidden="true" />
      <div className="app-container py-14">
        <div className="flex flex-col gap-10 md:flex-row md:items-start md:justify-between">
          <div className="max-w-sm">
            <div className="inline-flex items-center gap-3 rounded-xl px-1.5 py-1.5 transition-colors duration-300 hover:bg-white/5">
              <BrandMark className="h-11 w-11" />
            </div>
            <p className="mt-4 max-w-sm text-sm leading-6 text-neutral-400">
              Coordinated enterprise requests with company control at every step.
            </p>
          </div>
          <nav className="flex flex-col gap-x-10 gap-y-4 text-sm font-medium text-neutral-300 sm:flex-row sm:items-center" aria-label="Footer navigation">
            <a href="/#product" className="transition-colors duration-ui hover:text-white">Product</a>
            <a href="/#security" className="transition-colors duration-ui hover:text-white">Security</a>
            <a href="/#workflow" className="transition-colors duration-ui hover:text-white">How it works</a>
            <Link to="/login" className="transition-colors duration-ui hover:text-white">Sign in</Link>
            <Link
              to="/signup"
              className="inline-flex w-fit items-center rounded-lg bg-gradient-to-r from-primary-600 to-violet-600 px-4 py-2 font-semibold text-white shadow-lg shadow-primary-600/20 transition hover:brightness-105"
            >
              Create workspace
            </Link>
          </nav>
        </div>
        <div className="mt-12 border-t border-white/10 pt-6 text-sm text-neutral-500">
          © {new Date().getFullYear()} Orchestra. Enterprise multi-agent platform.
        </div>
      </div>
    </footer>
  );
}
