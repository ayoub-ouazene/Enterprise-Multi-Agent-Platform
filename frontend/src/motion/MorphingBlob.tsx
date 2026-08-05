import { motion } from 'framer-motion';
import { memo } from 'react';

export interface MorphingBlobProps {
  className?: string;
  color?: string;
  secondaryColor?: string;
  size?: number;
  duration?: number;
  style?: React.CSSProperties;
  blur?: number;
}

function cleanHex(color: string) {
  return color.replace('#', '');
}

function makePaths(size: number) {
  const s = size;
  const p1 = `M${s * 0.5},${s * 0.1} C${s * 0.8},${s * 0.05} ${s * 0.95},${s * 0.25} ${s * 0.9},${s * 0.5} C${s * 0.85},${s * 0.8} ${s * 0.6},${s * 0.95} ${s * 0.35},${s * 0.9} C${s * 0.1},${s * 0.85} ${s * 0.05},${s * 0.55} ${s * 0.15},${s * 0.3} C${s * 0.25},${s * 0.08} ${s * 0.35},${s * 0.12} ${s * 0.5},${s * 0.1} Z`;
  const p2 = `M${s * 0.45},${s * 0.15} C${s * 0.7},${s * 0.08} ${s * 0.92},${s * 0.35} ${s * 0.85},${s * 0.55} C${s * 0.78},${s * 0.75} ${s * 0.55},${s * 0.92} ${s * 0.3},${s * 0.88} C${s * 0.08},${s * 0.82} ${s * 0.02},${s * 0.5} ${s * 0.12},${s * 0.28} C${s * 0.22},${s * 0.06} ${s * 0.3},${s * 0.18} ${s * 0.45},${s * 0.15} Z`;
  const p3 = `M${s * 0.52},${s * 0.08} C${s * 0.75},${s * 0.02} ${s * 0.98},${s * 0.22} ${s * 0.92},${s * 0.48} C${s * 0.88},${s * 0.7} ${s * 0.65},${s * 0.98} ${s * 0.38},${s * 0.92} C${s * 0.12},${s * 0.88} ${s * 0.02},${s * 0.52} ${s * 0.1},${s * 0.32} C${s * 0.18},${s * 0.12} ${s * 0.38},${s * 0.1} ${s * 0.52},${s * 0.08} Z`;
  const p4 = `M${s * 0.48},${s * 0.12} C${s * 0.72},${s * 0.06} ${s * 0.96},${s * 0.28} ${s * 0.88},${s * 0.52} C${s * 0.82},${s * 0.75} ${s * 0.58},${s * 0.92} ${s * 0.32},${s * 0.86} C${s * 0.1},${s * 0.8} ${s * 0.04},${s * 0.48} ${s * 0.14},${s * 0.26} C${s * 0.24},${s * 0.1} ${s * 0.32},${s * 0.14} ${s * 0.48},${s * 0.12} Z`;
  return [p1, p2, p3, p4, p1];
}

export const MorphingBlob = memo(function MorphingBlob({
  className = '',
  color = '#3b82f6',
  secondaryColor = '#8b5cf6',
  size = 400,
  duration = 20,
  style,
  blur = 60,
}: MorphingBlobProps) {
  const d = size;
  const gradId = `bg-${cleanHex(color)}-${cleanHex(secondaryColor)}`;
  const filterId = `bf-${cleanHex(color)}`;
  const paths = makePaths(d);

  return (
    <svg
      viewBox={`0 0 ${d} ${d}`}
      className={`pointer-events-none ${className}`}
      style={{ width: d, height: d, ...style }}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={color} stopOpacity="0.5" />
          <stop offset="100%" stopColor={secondaryColor} stopOpacity="0.2" />
        </linearGradient>
        <filter id={filterId}>
          <feGaussianBlur stdDeviation={blur} result="blur" />
        </filter>
      </defs>
      <motion.path
        fill={`url(#${gradId})`}
        filter={`url(#${filterId})`}
        animate={{ d: paths }}
        transition={{
          duration,
          ease: 'easeInOut',
          repeat: Infinity,
          repeatType: 'loop',
        }}
      />
    </svg>
  );
});
