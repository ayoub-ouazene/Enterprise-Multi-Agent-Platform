import { describe, expect, it } from 'vitest';
import { accessibleMotionDuration } from './accessibility';

describe('public reduced-motion support', () => {
  it('removes animation duration when reduced motion is requested', () => {
    expect(accessibleMotionDuration(true, 0.55)).toBe(0);
    expect(accessibleMotionDuration(false, 0.55)).toBe(0.55);
  });
});
