import { memo, useRef, useEffect } from 'react';

interface FloatingGeometryProps {
  className?: string;
  shapeCount?: number;
  colors?: string[];
}

interface Shape {
  x: number;
  y: number;
  size: number;
  rotation: number;
  rotationSpeed: number;
  floatSpeed: number;
  floatOffset: number;
  floatAmp: number;
  opacity: number;
  type: 'triangle' | 'diamond' | 'hexagon';
  color: string;
}

export const FloatingGeometry = memo(function FloatingGeometry({
  className = '',
  shapeCount = 12,
  colors = [
    'rgba(99, 102, 241, 0.2)',
    'rgba(59, 130, 246, 0.15)',
    'rgba(139, 92, 246, 0.15)',
    'rgba(6, 182, 212, 0.12)',
  ],
}: FloatingGeometryProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const shapesRef = useRef<Shape[]>([]);
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

      if (shapesRef.current.length === 0) {
        const types: Shape['type'][] = ['triangle', 'diamond', 'hexagon'];
        shapesRef.current = Array.from({ length: shapeCount }, () => ({
          x: Math.random() * w,
          y: Math.random() * h,
          size: 8 + Math.random() * 20,
          rotation: Math.random() * Math.PI * 2,
          rotationSpeed: (Math.random() - 0.5) * 0.004,
          floatSpeed: 0.0003 + Math.random() * 0.0008,
          floatOffset: Math.random() * Math.PI * 2,
          floatAmp: 10 + Math.random() * 30,
          opacity: 0.3 + Math.random() * 0.4,
          type: types[Math.floor(Math.random() * types.length)],
          color: colors[Math.floor(Math.random() * colors.length)],
        }));
      }
    }

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    function drawShape(shape: Shape) {
      ctx!.save();
      const floatY = shape.y + Math.sin(timeRef.current * shape.floatSpeed + shape.floatOffset) * shape.floatAmp;
      ctx!.translate(shape.x, floatY);
      ctx!.rotate(shape.rotation);
      ctx!.fillStyle = shape.color;
      ctx!.strokeStyle = shape.color;

      switch (shape.type) {
        case 'triangle': {
          ctx!.beginPath();
          ctx!.moveTo(0, -shape.size);
          ctx!.lineTo(shape.size * 0.866, shape.size * 0.5);
          ctx!.lineTo(-shape.size * 0.866, shape.size * 0.5);
          ctx!.closePath();
          ctx!.stroke();
          break;
        }
        case 'diamond': {
          ctx!.beginPath();
          ctx!.moveTo(0, -shape.size);
          ctx!.lineTo(shape.size * 0.6, 0);
          ctx!.lineTo(0, shape.size);
          ctx!.lineTo(-shape.size * 0.6, 0);
          ctx!.closePath();
          ctx!.stroke();
          break;
        }
        case 'hexagon': {
          ctx!.beginPath();
          for (let i = 0; i < 6; i++) {
            const angle = (Math.PI / 3) * i - Math.PI / 2;
            const px = Math.cos(angle) * shape.size;
            const py = Math.sin(angle) * shape.size;
            if (i === 0) ctx!.moveTo(px, py);
            else ctx!.lineTo(px, py);
          }
          ctx!.closePath();
          ctx!.stroke();
          break;
        }
      }
      ctx!.restore();
    }

    function draw() {
      ctx!.clearRect(0, 0, w, h);
      timeRef.current += 1;

      for (const shape of shapesRef.current) {
        shape.rotation += shape.rotationSpeed;

        // Drift slowly
        shape.x += Math.sin(timeRef.current * 0.0002 + shape.floatOffset) * 0.15;
        shape.y += Math.cos(timeRef.current * 0.00015 + shape.floatOffset) * 0.1;

        // Wrap
        if (shape.x < -50) shape.x = w + 50;
        if (shape.x > w + 50) shape.x = -50;
        if (shape.y < -50) shape.y = h + 50;
        if (shape.y > h + 50) shape.y = -50;

        drawShape(shape);
      }

      animRef.current = requestAnimationFrame(draw);
    }

    animRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animRef.current);
      ro.disconnect();
    };
  }, [shapeCount, colors]);

  return (
    <canvas
      ref={canvasRef}
      className={`pointer-events-none absolute inset-0 ${className}`}
      style={{ width: '100%', height: '100%', display: 'block' }}
    />
  );
});
