export const designTokens = {
  layout: {
    headerHeight: '4rem',
    sidebarExpanded: '17rem',
    sidebarCollapsed: '5rem',
    pageMaxWidth: '80rem',
  },
  radius: { control: '0.5rem', card: '0.875rem', overlay: '1rem', pill: '9999px' },
  breakpoints: { sm: 640, md: 768, lg: 1024, xl: 1280 },
  zIndex: { header: 30, dropdown: 40, overlay: 50, toast: 60, skipLink: 100 },
  motion: {
    fast: 0.14,
    standard: 0.2,
    panel: 0.26,
    easing: [0.2, 0, 0, 1] as const,
  },
} as const;
