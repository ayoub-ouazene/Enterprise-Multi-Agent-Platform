import { useId, type ReactElement, type ReactNode, cloneElement } from 'react';

export function Tooltip({ label, children }: { label: string; children: ReactElement; }) {
  const id = useId();
  return (
    <span className="group/tooltip relative inline-flex">
      {cloneElement(children, { 'aria-describedby': id } as Record<string, string>)}
      <span
        id={id}
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-full z-dropdown mt-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-neutral-950 px-2 py-1 text-xs text-white opacity-0 shadow-sm transition-opacity duration-ui group-hover/tooltip:opacity-100 group-focus-within/tooltip:opacity-100 dark:bg-neutral-100 dark:text-neutral-950"
      >
        {label as ReactNode}
      </span>
    </span>
  );
}
