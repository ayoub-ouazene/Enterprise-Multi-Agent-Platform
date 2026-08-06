/**
 * Inline SVG orchestra mark — 3 bars rising like a conductor's podium / sound equalizer.
 * Always 30x30. Colors adapt via className or fill props.
 */
import { clsx } from 'clsx';

interface OrchestraMarkProps {
  className?: string;
  /** Override fill for the bars (default: currentColor) */
  fill?: string;
  size?: number;
}

export function OrchestraMark({ className, fill, size = 30 }: OrchestraMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={clsx('shrink-0', className)}
      aria-hidden="true"
    >
      {/* Gradient defs */}
      <defs>
        <linearGradient id="orchestra-gradient" x1="0" y1="30" x2="30" y2="0" gradientUnits="userSpaceOnUse">
          <stop stopColor="#6366f1" />
          <stop offset="0.5" stopColor="#3b82f6" />
          <stop offset="1" stopColor="#06b6d4" />
        </linearGradient>
        <linearGradient id="orchestra-gradient-dark" x1="0" y1="30" x2="30" y2="0" gradientUnits="userSpaceOnUse">
          <stop stopColor="#818cf8" />
          <stop offset="0.5" stopColor="#60a5fa" />
          <stop offset="1" stopColor="#22d3ee" />
        </linearGradient>
      </defs>

      {/* Rounded square bg */}
      <rect width="30" height="30" rx="7.5" fill={fill || 'url(#orchestra-gradient)'} />

      {/* Three rising bars */}
      <rect x="7" y="17" width="4" height="7" rx="2" fill="white" opacity="0.95" />
      <rect x="13" y="11" width="4" height="13" rx="2" fill="white" opacity="0.85" />
      <rect x="19" y="6" width="4" height="18" rx="2" fill="white" opacity="0.7" />
    </svg>
  );
}
