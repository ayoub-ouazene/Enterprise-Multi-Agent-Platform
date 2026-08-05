import { useRef, useEffect, useState, type ReactNode } from 'react';

export interface SpotlightCursorProps {
  children: ReactNode;
  className?: string;
  size?: number;
  color?: string;
  innerColor?: string;
}

export function SpotlightCursor({
  children,
  className = '',
  size = 400,
  color = '99, 102, 241',
  innerColor = '168, 85, 247',
}: SpotlightCursorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ x: -999, y: -999 });
  const targetRef = useRef({ x: -999, y: -999 });
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      targetRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    };

    const handleLeave = () => {
      targetRef.current = { x: -999, y: -999 };
    };

    const animate = () => {
      setPos((prev) => ({
        x: prev.x + (targetRef.current.x - prev.x) * 0.12,
        y: prev.y + (targetRef.current.y - prev.y) * 0.12,
      }));
      rafRef.current = requestAnimationFrame(animate);
    };

    container.addEventListener('mousemove', handleMove);
    container.addEventListener('mouseleave', handleLeave);
    rafRef.current = requestAnimationFrame(animate);

    return () => {
      container.removeEventListener('mousemove', handleMove);
      container.removeEventListener('mouseleave', handleLeave);
      cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return (
    <div ref={containerRef} className={`relative overflow-hidden ${className}`}>
      <div
        className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 rounded-full opacity-40 blur-3xl transition-opacity duration-500"
        style={{
          left: pos.x,
          top: pos.y,
          width: size,
          height: size,
          background: `radial-gradient(circle, rgba(${innerColor}, 0.35) 0%, rgba(${color}, 0.15) 50%, transparent 70%)`,
        }}
      />
      <div
        className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 rounded-full opacity-25 blur-2xl"
        style={{
          left: pos.x,
          top: pos.y,
          width: size * 0.6,
          height: size * 0.6,
          background: `radial-gradient(circle, rgba(${color}, 0.4) 0%, transparent 70%)`,
        }}
      />
      {children}
    </div>
  );
}
