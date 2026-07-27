import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export function Breadcrumbs({ items }: { items: { label: string; href?: string }[] }) {
  return <nav aria-label="Breadcrumb"><ol className="flex flex-wrap items-center gap-1 text-sm text-neutral-500">{items.map((item, index) => <li key={`${item.label}-${index}`} className="flex items-center gap-1">{index > 0 && <ChevronRight size={14} aria-hidden="true" />}{item.href && index < items.length - 1 ? <Link to={item.href} className="hover:text-primary-600">{item.label}</Link> : <span aria-current={index === items.length - 1 ? 'page' : undefined} className={index === items.length - 1 ? 'font-medium text-neutral-800 dark:text-neutral-200' : ''}>{item.label}</span>}</li>)}</ol></nav>;
}
