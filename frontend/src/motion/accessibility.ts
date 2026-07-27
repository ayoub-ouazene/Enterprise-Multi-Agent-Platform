export function accessibleMotionDuration(
  reducedMotion: boolean | null,
  duration: number,
): number {
  return reducedMotion ? 0 : duration;
}
