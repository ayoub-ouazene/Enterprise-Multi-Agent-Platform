import { Monitor, Moon, Sun } from 'lucide-react';
import { useThemeStore } from '../../lib/theme-store';

export function ThemeToggle() {
  const { theme, cycle } = useThemeStore();
  const next = theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light';
  const Icon = theme === 'light' ? Sun : theme === 'dark' ? Moon : Monitor;

  return (
    <button
      onClick={cycle}
      className="rounded-lg p-2 text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-800 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-neutral-100"
      aria-label={`Theme: ${theme}. Switch to ${next} mode`}
      title={`Theme: ${theme}`}
    >
      <Icon size={18} aria-hidden="true" />
    </button>
  );
}
