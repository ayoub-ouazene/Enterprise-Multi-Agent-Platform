import { create } from 'zustand';

export type Theme = 'light' | 'dark';

type ThemeStore = {
  theme: Theme;
  toggle: () => void;
  init: () => void;
};

const STORAGE_KEY = 'theme';

function getSavedTheme(): Theme | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === 'light' || raw === 'dark') return raw;
  } catch {}
  return null;
}

function getSystemTheme(): Theme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function apply(theme: Theme): void {
  const root = document.documentElement;
  if (theme === 'dark') {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
}

export const useThemeStore = create<ThemeStore>((set, get) => ({
  theme: 'light',

  toggle: () => {
    const next = get().theme === 'light' ? 'dark' : 'light';
    set({ theme: next });
    apply(next);
    try { localStorage.setItem(STORAGE_KEY, next); } catch {}
  },

  init: () => {
    const saved = getSavedTheme();
    const theme = saved ?? getSystemTheme();
    set({ theme });
    apply(theme);
  },
}));
