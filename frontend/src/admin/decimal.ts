export function formatDecimalMoney(currency: string, value: string): string {
  const normalized = value.trim();
  const negative = normalized.startsWith('-');
  const [rawWhole, rawFraction = ''] = normalized.replace(/^[+-]/, '').split('.');
  const whole = (rawWhole || '0').replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  const fraction = `${rawFraction}00`.slice(0, 2);
  return `${currency.toUpperCase()} ${negative ? '-' : ''}${whole}.${fraction}`;
}

export function decimalLessThan(left: string, right: string): boolean {
  const normalize = (value: string) => {
    const [whole, fraction = ''] = value.split('.');
    return BigInt(`${whole || '0'}${`${fraction}00`.slice(0, 2)}`);
  };
  return normalize(left) < normalize(right);
}
