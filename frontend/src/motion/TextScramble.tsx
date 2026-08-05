import { useRef, useEffect, useState, memo } from 'react';

const CHARS = '!<>-_\\/[]{}—=+*^?#________';

export interface TextScrambleProps {
  text: string;
  className?: string;
  as?: 'span' | 'p' | 'h1' | 'h2' | 'h3' | 'h4' | 'div';
  speed?: number;
  trigger?: boolean;
  delay?: number;
  onComplete?: () => void;
  children?: React.ReactNode;
}

export const TextScramble = memo(function TextScramble({
  text,
  className = '',
  as: Tag = 'span',
  speed = 1,
  trigger = true,
  delay = 0,
  onComplete,
  children,
}: TextScrambleProps) {
  const [display, setDisplay] = useState('');
  const hasRun = useRef(false);

  useEffect(() => {
    if (!trigger || hasRun.current) return;
    hasRun.current = true;

    let frame = 0;
    let queue: { from: string; to: string; start: number; end: number; char?: string }[] = [];
    const length = text.length;
    const framesPerChar = Math.max(2, Math.floor(12 / speed));

    for (let i = 0; i < length; i++) {
      const from = text[i];
      const to = text[i];
      const start = i * framesPerChar + delay * 60;
      const end = start + framesPerChar;
      queue.push({ from, to, start, end });
    }

    let raf: number;
    const update = () => {
      let output = '';
      let complete = 0;
      for (let i = 0; i < queue.length; i++) {
        const { from, to, start, end } = queue[i];
        let char = queue[i].char;

        if (frame >= end) {
          complete++;
          output += to;
        } else if (frame >= start) {
          if (!char || Math.random() < 0.28) {
            char = CHARS[Math.floor(Math.random() * CHARS.length)];
            queue[i].char = char;
          }
          output += char;
        } else {
          output += from === ' ' ? ' ' : '';
        }
      }

      setDisplay(output);
      frame++;
      if (complete === queue.length) {
        onComplete?.();
        return;
      }
      raf = requestAnimationFrame(update);
    };

    raf = requestAnimationFrame(update);
    return () => cancelAnimationFrame(raf);
  }, [trigger, text, speed, delay, onComplete]);

  return (
    <Tag className={`inline-block ${className}`}>
      {display || (trigger ? '' : text)}
      {children}
    </Tag>
  );
});
