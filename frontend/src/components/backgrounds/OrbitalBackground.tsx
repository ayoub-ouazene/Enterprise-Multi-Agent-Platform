import { memo, useRef, useEffect } from 'react';

interface OrbitalBackgroundProps {
  orbCount?: number;
  className?: string;
  colors?: string[];
  speed?: number;
}

interface Orb {
  x: number;
  y: number;
  radius: number;
  baseRadius: number;
  vx: number;
  vy: number;
  color: string;
  phase: number;
  floatSpeed: number;
  floatAmp: number;
}

export const OrbitalBackground = memo(function OrbitalBackground({
  orbCount = 5,
  className = '',
  colors = [
    'rgba(59, 130, 246, 0.35)',
    'rgba(139, 92, 246, 0.30)',
    'rgba(6, 182, 212, 0.25)',
    'rgba(99, 102, 241, 0.30)',
    'rgba(236, 72, 153, 0.20)',
  ],
  speed = 0.3,
}: OrbitalBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const orbsRef = useRef<Orb[]>([]);
  const timeRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let w = 0;
    let h = 0;

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas!.clientWidth;
      h = canvas!.clientHeight;
      canvas!.width = w * dpr;
      canvas!.height = h * dpr;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);

      if (orbsRef.current.length === 0) {
        orbsRef.current = Array.from({ length: orbCount }, (_, i) => {
          const baseR = Math.min(w, h) * (0.15 + Math.random() * 0.25);
          return {
            x: Math.random() * w,
            y: Math.random() * h,
            radius: baseR,
            baseRadius: baseR,
            vx: (Math.random() - 0.5) * speed,
            vy: (Math.random() - 0.5) * speed * 0.6,
            color: colors[i % colors.length],
            phase: Math.random() * Math.PI * 2,
            floatSpeed: 0.0005 + Math.random() * 0.001,
            floatAmp: 0.08 + Math.random() * 0.12,
          };
        });
      }
    }

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    function draw() {
      ctx!.clearRect(0, 0, w, h);
      timeRef.current += 1;
      const t = timeRef.current;

      const orbs = orbsRef.current;
      for (const orb of orbs) {
        orb.x += orb.vx;
        orb.y += orb.vy;

        if (orb.x < -orb.radius) orb.x = w + orb.radius;
        if (orb.x > w + orb.radius) orb.x = -orb.radius;
        if (orb.y < -orb.radius) orb.y = h + orb.radius;
        if (orb.y > h + orb.radius) orb.y = -orb.radius;

        const breath = 1 + Math.sin(t * orb.floatSpeed + orb.phase) * orb.floatAmp;
        orb.radius = orb.baseRadius * breath;

        const gradient = ctx!.createRadialGradient(
          orb.x, orb.y, 0,
          orb.x, orb.y, orb.radius
        );
        gradient.addColorStop(0, orb.color);
        gradient.addColorStop(0.5, orb.color.replace(/[\d.]+\)$/, '0.1)'));
        gradient.addColorStop(1, 'rgba(0,0,0,0)');

        ctx!.fillStyle = gradient;
        ctx!.beginPath();
        ctx!.arc(orb.x, orb.y, orb.radius, 0, Math.PI * 2);
        ctx!.fill();
      }

      animRef.current = requestAnimationFrame(draw);
    }

    animRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animRef.current);
      ro.disconnect();
    };
  }, [orbCount, colors, speed]);

  return (
    <canvas
      ref={canvasRef}
      className={`pointer-events-none absolute inset-0 ${className}`}
      style={{ width: '100%', height: '100%', display: 'block' }}
    />
  );
});
