import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { clsx } from 'clsx';

export const IconButton = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement>>(
  function IconButton({ className, type = 'button', ...props }, ref) {
    return (
      <button
        ref={ref}
        type={type}
        className={clsx(
          'inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-neutral-500 transition-colors duration-ui',
          'hover:bg-neutral-100 hover:text-neutral-900 disabled:pointer-events-none disabled:opacity-50',
          'dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-white',
          className,
        )}
        {...props}
      />
    );
  },
);
