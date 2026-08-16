interface AnimatedBackgroundProps {
  children?: React.ReactNode;
  className?: string;
  variant?: 'gradient' | 'mesh' | 'particles' | 'grid' | 'aurora';
  intensity?: 'subtle' | 'medium' | 'strong';
}

import { MeshGradient } from '../../motion/MeshGradient';
import { ParticleField } from '../../motion/ParticleField';
import { NoiseTexture } from './NoiseTexture';
import { clsx } from 'clsx';

export function AnimatedBackground({
  children,
  className = '',
  variant = 'gradient',
}: AnimatedBackgroundProps) {

  return (
    <div className={clsx('relative min-h-full overflow-hidden', className)}>
      {/* Background layer */}
      <div className="absolute inset-0 z-0">
        {variant === 'gradient' && (
          <div
            className="absolute inset-0"
            style={{
              background: 'radial-gradient(ellipse at 20% 20%, rgba(99,102,241,0.12), transparent 50%), radial-gradient(ellipse at 80% 80%, rgba(59,130,246,0.08), transparent 50%), radial-gradient(ellipse at 50% 50%, rgba(139,92,246,0.06), transparent 60%)',
            }}
          />
        )}
        {variant === 'mesh' && (
          <MeshGradient
            colors={['#6366f1', '#3b82f6', '#8b5cf6', '#06b6d4']}
            speed={0.3}
            className="opacity-40"
          />
        )}
        {variant === 'particles' && (
          <ParticleField
            particleCount={40}
            color="148, 163, 184"
            speed={0.2}
          />
        )}
        {variant === 'grid' && (
          <div className="dot-grid absolute inset-0 opacity-30 dark:opacity-20" />
        )}
        {variant === 'aurora' && <AuroraBackground />}

        {/* Overlay for better contrast — fades the aurora near the bottom so the page footer stays distinct */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-neutral-950/80 dark:to-neutral-950/85" />
      </div>

      {/* Noise texture overlay */}
      <NoiseTexture opacity={0.02} className="z-[1]" />

      {/* Content */}
      <div className="relative z-10">{children}</div>
    </div>
  );
}

function AuroraBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden">
      {/* Animated gradient blobs */}
      <div
        className="absolute -top-[40%] -left-[20%] h-[600px] w-[600px] rounded-full opacity-20 blur-[100px]"
        style={{
          background: 'conic-gradient(from 0deg, #6366f1, #3b82f6, #8b5cf6, #6366f1)',
          animation: 'aurora-1 8s ease-in-out infinite',
        }}
      />
      <div
        className="absolute -bottom-[40%] -right-[20%] h-[500px] w-[500px] rounded-full opacity-15 blur-[100px]"
        style={{
          background: 'conic-gradient(from 180deg, #3b82f6, #06b6d4, #6366f1, #3b82f6)',
          animation: 'aurora-2 12s ease-in-out infinite',
        }}
      />
      <div
        className="absolute top-[40%] left-[30%] h-[400px] w-[400px] rounded-full opacity-10 blur-[80px]"
        style={{
          background: '#8b5cf6',
          animation: 'aurora-3 10s ease-in-out infinite',
        }}
      />
      <style>{`
        @keyframes aurora-1 {
          0%, 100% { transform: rotate(0deg) scale(1); }
          50% { transform: rotate(180deg) scale(1.2); }
        }
        @keyframes aurora-2 {
          0%, 100% { transform: rotate(180deg) scale(1); }
          50% { transform: rotate(360deg) scale(1.3); }
        }
        @keyframes aurora-3 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(50px, -30px) scale(1.1); }
          66% { transform: translate(-30px, 40px) scale(0.9); }
        }
      `}</style>
    </div>
  );
}
