import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { clsx } from 'clsx';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { BrandMark } from './BrandMark';

const navigation = [
  { label: 'Product', hash: 'product' },
  { label: 'Solutions', hash: 'departments' },
  { label: 'Security', hash: 'security' },
];

export function PublicHeader({ transparent = false }: { transparent?: boolean }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => setMenuOpen(false), [location.pathname, location.hash]);

  const dark = transparent && !scrolled;
  const sectionHref = (hash: string) =>
    location.pathname === '/' ? `#${hash}` : `/#${hash}`;

  return (
    <header
      className={clsx(
        'sticky top-0 z-50 border-b transition-[background-color,border-color,box-shadow] duration-300',
        dark
          ? 'border-transparent bg-neutral-950/70 text-white backdrop-blur-md'
          : 'border-neutral-200/80 bg-white/90 text-neutral-900 shadow-sm backdrop-blur-xl dark:border-neutral-800 dark:bg-neutral-950/90 dark:text-white',
      )}
    >
      <div className="app-container flex h-16 items-center justify-between">
        <BrandMark inverted={dark} />
        <nav className="hidden items-center gap-1 md:flex" aria-label="Public navigation">
          {navigation.map((item) => (
            <a
              key={item.hash}
              href={sectionHref(item.hash)}
              className={clsx(
                'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                dark
                  ? 'text-neutral-300 hover:bg-white/10 hover:text-white'
                  : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-950 dark:text-neutral-300 dark:hover:bg-neutral-800 dark:hover:text-white',
              )}
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="hidden items-center gap-2 md:flex">
          <Link
            to="/login"
            className={clsx(
              'rounded-lg px-4 py-2 text-sm font-semibold transition-colors',
              dark ? 'text-white hover:bg-white/10' : 'text-neutral-700 hover:bg-neutral-100 dark:text-neutral-200 dark:hover:bg-neutral-800',
            )}
          >
            Sign in
          </Link>
          <Link
            to="/signup"
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-[background-color,box-shadow,transform] duration-ui ease-productive hover:bg-primary-500 hover:shadow-md motion-safe:active:scale-[0.98]"
          >
            Create workspace
          </Link>
        </div>
        <button
          type="button"
          className={clsx(
            'flex h-11 w-11 items-center justify-center rounded-lg md:hidden',
            dark ? 'text-white hover:bg-white/10' : 'text-neutral-700 hover:bg-neutral-100 dark:text-neutral-200 dark:hover:bg-neutral-800',
          )}
          aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={menuOpen}
          aria-controls="public-mobile-navigation"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
        </button>
      </div>
      <AnimatePresence>
        {menuOpen && (
          <motion.nav
            id="public-mobile-navigation"
            className="border-t border-neutral-200 bg-white px-4 py-4 text-neutral-900 shadow-lg dark:border-neutral-800 dark:bg-neutral-950 dark:text-white md:hidden"
            aria-label="Mobile public navigation"
            initial={reducedMotion ? false : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={reducedMotion ? undefined : { opacity: 0, height: 0 }}
            transition={{ duration: reducedMotion ? 0 : 0.25, ease: [0.2, 0, 0, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <div className="mx-auto flex max-w-7xl flex-col gap-1">
              {navigation.map((item) => (
                <a key={item.hash} href={sectionHref(item.hash)} className="rounded-lg px-3 py-3 text-base font-medium hover:bg-neutral-100 dark:hover:bg-neutral-800">
                  {item.label}
                </a>
              ))}
              <div className="mt-3 grid grid-cols-1 gap-2 border-t border-neutral-200 pt-4 dark:border-neutral-800 min-[360px]:grid-cols-2">
                <Link to="/login" className="rounded-lg border border-neutral-300 px-4 py-3 text-center font-semibold dark:border-neutral-700">Sign in</Link>
                <Link to="/signup" className="rounded-lg bg-primary-600 px-4 py-3 text-center font-semibold text-white">Create workspace</Link>
              </div>
            </div>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
}
