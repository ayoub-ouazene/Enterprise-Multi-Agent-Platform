import { create } from 'zustand';

export type Theme = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

type ThemeStore = {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
  cycle: () => void;
  init: () => void;
};

export const THEME_STORAGE_KEY = 'tellus.theme';
let stopSystemListener: (() => void) | null = null;

function getSavedTheme(): Theme | null {
  try {
    const raw = localStorage.getItem(THEME_STORAGE_KEY) ?? localStorage.getItem('theme');
    if (raw === 'light' || raw === 'dark' || raw === 'system') return raw;
  } catch {
    // Storage can be unavailable in privacy-restricted browser contexts.
  }
  return null;
}

function getSystemTheme(): ResolvedTheme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function resolve(theme: Theme): ResolvedTheme {
  return theme === 'system' ? getSystemTheme() : theme;
}

function apply(theme: ResolvedTheme): void {
  const root = document.documentElement;
  root.classList.toggle('dark', theme === 'dark');
  root.style.colorScheme = theme;
  root.dataset.theme = theme;
}

export const useThemeStore = create<ThemeStore>((set, get) => ({
  theme: 'system',
  resolvedTheme: 'light',

  setTheme: (theme) => {
    const resolvedTheme = resolve(theme);
    set({ theme, resolvedTheme });
    apply(resolvedTheme);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
      localStorage.removeItem('theme');
    } catch {
      // The in-memory theme still works when persistent storage is unavailable.
    }
  },

  cycle: () => {
    const next: Record<Theme, Theme> = { light: 'dark', dark: 'system', system: 'light' };
    get().setTheme(next[get().theme]);
  },

  init: () => {
    const theme = getSavedTheme() ?? 'system';
    get().setTheme(theme);

    stopSystemListener?.();
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      if (get().theme !== 'system') return;
      const resolvedTheme = getSystemTheme();
      set({ resolvedTheme });
      apply(resolvedTheme);
    };
    query.addEventListener?.('change', handleChange);
    stopSystemListener = () => query.removeEventListener?.('change', handleChange);
  },
}));
