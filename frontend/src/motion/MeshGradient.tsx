import { memo, useRef, useEffect } from 'react';

interface MeshGradientProps {
  className?: string;
  /** Array of CSS colors for the gradient blobs */
  colors?: string[];
  /** Speed of the animation (default: 1) */
  speed?: number;
  /** Number of gradient blobs (default: 3) */
  blobCount?: number;
}

export const MeshGradient = memo(function MeshGradient({
  className = '',
  colors = ['#3b82f6', '#8b5cf6', '#06b6d4', '#6366f1'],
  speed = 1,
  blobCount = 3,
}: MeshGradientProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const blobsRef = useRef<{ x: number; y: number; r: number; dx: number; dy: number; color: string }[]>([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let w = 0;
    let h = 0;

    function resize() {
      w = canvas!.clientWidth;
      h = canvas!.clientHeight;
      canvas!.width = w * window.devicePixelRatio;
      canvas!.height = h * window.devicePixelRatio;
      ctx!.scale(window.devicePixelRatio, window.devicePixelRatio);

      // Initialize blobs on first resize
      if (blobsRef.current.length === 0) {
        for (let i = 0; i < blobCount; i++) {
          blobsRef.current.push({
            x: Math.random() * w,
            y: Math.random() * h,
            r: Math.min(w, h) * (0.3 + Math.random() * 0.4),
            dx: (Math.random() - 0.5) * speed * 0.5,
            dy: (Math.random() - 0.5) * speed * 0.5,
            color: colors[i % colors.length],
          });
        }
      }
    }

    resize();
    window.addEventListener('resize', resize);

    function draw() {
      ctx!.clearRect(0, 0, w, h);

      // Draw mesh gradient
      for (let i = 0; i < blobsRef.current.length; i++) {
        const blob = blobsRef.current[i];

        // Move blob
        blob.x += blob.dx;
        blob.y += blob.dy;

        // Bounce off edges
        if (blob.x < -blob.r) blob.dx = Math.abs(blob.dx);
        if (blob.x > w + blob.r) blob.dx = -Math.abs(blob.dx);
        if (blob.y < -blob.r) blob.dy = Math.abs(blob.dy);
        if (blob.y > h + blob.r) blob.dy = -Math.abs(blob.dy);

        // Create radial gradient for each blob
        const gradient = ctx!.createRadialGradient(
          blob.x, blob.y, 0,
          blob.x, blob.y, blob.r
        );
        
        // Parse color and add alpha
        const color = blob.color;
        gradient.addColorStop(0, color + '40'); // 25% opacity
        gradient.addColorStop(0.5, color + '20'); // 12% opacity
        gradient.addColorStop(1, color + '00'); // 0% opacity

        ctx!.fillStyle = gradient;
        ctx!.fillRect(0, 0, w, h);
      }

      animRef.current = requestAnimationFrame(draw);
    }

    animRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener('resize', resize);
    };
  }, [colors, speed, blobCount]);

  return (
    <canvas
      ref={canvasRef}
      className={`absolute inset-0 w-full h-full ${className}`}
      style={{ display: 'block' }}
    />
  );
});
