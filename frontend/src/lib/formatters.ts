const rtf = typeof Intl !== 'undefined' && Intl.RelativeTimeFormat
  ? new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
  : null;

const dateFmt = typeof Intl !== 'undefined' && Intl.DateTimeFormat
  ? new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  : null;

const dateTimeFmt = typeof Intl !== 'undefined' && Intl.DateTimeFormat
  ? new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  : null;

const dayMs = 86_400_000;
const minuteMs = 60_000;

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (dateFmt) return dateFmt.format(d);
  return d.toLocaleDateString();
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (dateTimeFmt) return dateTimeFmt.format(d);
  return d.toLocaleString();
}

export function relativeTime(iso: string): string {
  if (!rtf) return formatDate(iso);
  const d = new Date(iso).getTime();
  const now = Date.now();
  const diff = Math.round((d - now) / minuteMs);

  const hrs = Math.round(diff / 60);
  const days = Math.round(hrs / 24);
  const weeks = Math.round(days / 7);
  const months = Math.round(days / 30);
  const years = Math.round(days / 365);

  if (Math.abs(years) >= 1) return rtf.format(years, 'year');
  if (Math.abs(months) >= 1) return rtf.format(months, 'month');
  if (Math.abs(weeks) >= 1) return rtf.format(weeks, 'week');
  if (Math.abs(days) >= 1) return rtf.format(days, 'day');
  if (Math.abs(hrs) >= 1) return rtf.format(hrs, 'hour');
  return rtf.format(diff, 'minute');
}

export function groupByDate<T extends { created_at: string }>(items: T[]): { label: string; items: T[] }[] {
  const groups: Map<string, T[]> = new Map();
  const now = Date.now();

  for (const item of items) {
    const d = new Date(item.created_at);
    const key = dateKey(d, now);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(item);
  }

  const result: { label: string; items: T[] }[] = [];
  for (const [label, arr] of groups) {
    result.push({ label, items: arr.reverse() });
  }
  return result;
}

function dateKey(d: Date, now: number): string {
  const today = new Date(now);
  const yd = new Date(now - dayMs);

  const sameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();

  if (sameDay(d, today)) return 'Today';
  if (sameDay(d, yd)) return 'Yesterday';
  if (dateFmt) return dateFmt.format(d);
  return d.toLocaleDateString();
}
