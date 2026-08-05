import { memo, useRef, useEffect } from 'react';

interface GridLightProps {
  className?: string;
  lineColor?: string;
  highlightColor?: string;
  speed?: number;
  gridSize?: number;
}

export const GridLight = memo(function GridLight({
  className = '',
  lineColor = 'rgba(148, 163, 184, 0.06)',
  highlightColor = 'rgba(99, 102, 241, 0.12)',
  speed = 0.4,
  gridSize = 60,
}: GridLightProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const scanlinesRef = useRef<{ y: number; speed: number; width: number; opacity: number }[]>([]);

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

      if (scanlinesRef.current.length === 0) {
        scanlinesRef.current = Array.from({ length: 3 }, () => ({
          y: Math.random() * h,
          speed: 0.3 + Math.random() * 0.5,
          width: 40 + Math.random() * 80,
          opacity: 0.3 + Math.random() * 0.4,
        }));
      }
    }

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    function draw() {
      ctx!.clearRect(0, 0, w, h);

      // Draw grid
      ctx!.strokeStyle = lineColor;
      ctx!.lineWidth = 1;

      for (let x = 0; x <= w; x += gridSize) {
        ctx!.beginPath();
        ctx!.moveTo(x, 0);
        ctx!.lineTo(x, h);
        ctx!.stroke();
      }
      for (let y = 0; y <= h; y += gridSize) {
        ctx!.beginPath();
        ctx!.moveTo(0, y);
        ctx!.lineTo(w, y);
        ctx!.stroke();
      }

      // Draw scanning highlights
      for (const line of scanlinesRef.current) {
        line.y += line.speed * speed;
        if (line.y > h + line.width) {
          line.y = -line.width;
          line.speed = 0.3 + Math.random() * 0.5;
        }

        const gradient = ctx!.createLinearGradient(0, line.y - line.width / 2, 0, line.y + line.width / 2);
        gradient.addColorStop(0, 'rgba(0,0,0,0)');
        gradient.addColorStop(0.5, highlightColor.replace(/[\d.]+\)$/, `${line.opacity})`));
        gradient.addColorStop(1, 'rgba(0,0,0,0)');

        ctx!.fillStyle = gradient;
        ctx!.fillRect(0, line.y - line.width / 2, w, line.width);

        // Draw intersection glows
        for (let gx = 0; gx <= w; gx += gridSize) {
          const dist = Math.abs(line.y - Math.round(line.y / gridSize) * gridSize);
          if (dist < line.width / 2) {
            const glowOpacity = (1 - dist / (line.width / 2)) * line.opacity * 0.5;
            const gridY = Math.round(line.y / gridSize) * gridSize;
            const glowGradient = ctx!.createRadialGradient(gx, gridY, 0, gx, gridY, gridSize * 0.6);
            glowGradient.addColorStop(0, highlightColor.replace(/[\d.]+\)$/, `${glowOpacity})`));
            glowGradient.addColorStop(1, 'rgba(0,0,0,0)');
            ctx!.fillStyle = glowGradient;
            ctx!.beginPath();
            ctx!.arc(gx, gridY, gridSize * 0.6, 0, Math.PI * 2);
            ctx!.fill();
          }
        }
      }

      animRef.current = requestAnimationFrame(draw);
    }

    animRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animRef.current);
      ro.disconnect();
    };
  }, [lineColor, highlightColor, speed, gridSize]);

  return (
    <canvas
      ref={canvasRef}
      className={`pointer-events-none absolute inset-0 ${className}`}
      style={{ width: '100%', height: '100%', display: 'block' }}
    />
  );
});
