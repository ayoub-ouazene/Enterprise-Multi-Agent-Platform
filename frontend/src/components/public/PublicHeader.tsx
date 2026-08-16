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

  // Transparent header only when NOT scrolled on landing page hero
  const isHero = transparent && !scrolled;

  return (
    <header
      className={clsx(
        'sticky top-0 z-50 transition-[background-color,border-color,box-shadow] duration-500',
        isHero
          ? 'border-b border-transparent bg-transparent'
          : 'border-b border-white/15 bg-slate-900/95 shadow-2xl shadow-black/20 backdrop-blur-2xl',
      )}
    >
      {/* Accent top strip */}
      {!isHero && (
        <div className="h-[3px] w-full bg-gradient-to-r from-violet-500 via-primary-500 to-cyan-500" aria-hidden="true" />
      )}

      <div className="app-container flex h-16 items-center justify-between">
        {/* Logo */}
        <Link to="/" className="group inline-flex items-center gap-3 rounded-xl px-1 py-1 transition hover:bg-white/8">
          <BrandMark className="aurora-breathe h-10 w-10" />
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden items-center gap-1 md:flex" aria-label="Public navigation">
          {navigation.map((item) => (
            <a
              key={item.hash}
              href={sectionHref(item.hash, location.pathname)}
              className="rounded-lg px-3 py-2 text-sm font-medium text-white/85 transition hover:bg-white/10 hover:text-white"
            >
              {item.label}
            </a>
          ))}
        </nav>

        {/* Desktop Actions */}
        <div className="hidden items-center gap-2 md:flex">
          <Link
            to="/login"
            className="rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
          >
            Sign in
          </Link>
          <Link
            to="/signup"
            className="group relative overflow-hidden rounded-lg bg-gradient-to-r from-primary-600 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-xl shadow-primary-600/30 transition hover:shadow-primary-500/40 hover:brightness-105 active:scale-[0.98]"
          >
            <span className="relative z-10">Create workspace</span>
          </Link>
        </div>

        {/* Mobile toggle */}
        <button
          type="button"
          className="flex h-11 w-11 items-center justify-center rounded-xl text-white/70 transition hover:bg-white/10 hover:text-white md:hidden"
          aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={menuOpen}
          aria-controls="public-mobile-navigation"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
        </button>
      </div>

      {/* Mobile nav panel */}
      <AnimatePresence>
        {menuOpen && (
          <motion.nav
            id="public-mobile-navigation"
            className="border-t border-white/15 bg-slate-900/98 px-4 py-4 text-white shadow-2xl backdrop-blur-2xl md:hidden"
            aria-label="Mobile public navigation"
            initial={reducedMotion ? false : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={reducedMotion ? undefined : { opacity: 0, height: 0 }}
            transition={{ duration: reducedMotion ? 0 : 0.25, ease: [0.2, 0, 0, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <div className="mx-auto flex max-w-7xl flex-col gap-1">
              {navigation.map((item) => (
                <a
                  key={item.hash}
                  href={sectionHref(item.hash, location.pathname)}
                  className="rounded-lg px-3 py-3 text-base font-medium text-white/85 transition hover:bg-white/10 hover:text-white"
                >
                  {item.label}
                </a>
              ))}
              <div className="mt-3 grid grid-cols-1 gap-2 border-t border-white/15 pt-4 min-[360px]:grid-cols-2">
          <Link
            to="/login"
            className="rounded-lg border border-white/30 px-4 py-3 text-center font-semibold text-white transition hover:bg-white/10"
          >
            Sign in
          </Link>
                <Link
                  to="/signup"
                  className="rounded-lg bg-gradient-to-r from-primary-600 to-violet-600 px-4 py-3 text-center font-semibold text-white shadow-xl shadow-primary-600/30 transition hover:shadow-primary-500/40 hover:brightness-105"
                >
                  Create workspace
                </Link>
              </div>
            </div>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
}

function sectionHref(hash: string, pathname: string) {
  return pathname === '/' ? `#${hash}` : `/#${hash}`;
}
