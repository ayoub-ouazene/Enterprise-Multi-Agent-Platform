export enum DepartmentType {
  CUSTOMER_SUPPORT = 'customer_support',
  HR = 'hr',
  IT = 'it',
  FINANCE = 'finance',
  PROCUREMENT = 'procurement',
}

export interface DepartmentMeta {
  type: DepartmentType;
  label: string;
  slug: string;
  color: string;
  lightColor: string;
  darkColor: string;
  icon: string;
}

export const DEPARTMENT_REGISTRY: Record<DepartmentType, DepartmentMeta> = {
  [DepartmentType.CUSTOMER_SUPPORT]: {
    type: DepartmentType.CUSTOMER_SUPPORT,
    label: 'Customer Support',
    slug: 'customer-support',
    color: '#F59E0B',
    lightColor: '#FEF3C7',
    darkColor: '#92400E',
    icon: 'Headphones',
  },
  [DepartmentType.HR]: {
    type: DepartmentType.HR,
    label: 'Human Resources',
    slug: 'human-resources',
    color: '#10B981',
    lightColor: '#D1FAE5',
    darkColor: '#065F46',
    icon: 'Users',
  },
  [DepartmentType.IT]: {
    type: DepartmentType.IT,
    label: 'Information Technology',
    slug: 'information-technology',
    color: '#3B82F6',
    lightColor: '#DBEAFE',
    darkColor: '#1E40AF',
    icon: 'Monitor',
  },
  [DepartmentType.FINANCE]: {
    type: DepartmentType.FINANCE,
    label: 'Finance',
    slug: 'finance',
    color: '#8B5CF6',
    lightColor: '#EDE9FE',
    darkColor: '#5B21B6',
    icon: 'Landmark',
  },
  [DepartmentType.PROCUREMENT]: {
    type: DepartmentType.PROCUREMENT,
    label: 'Procurement',
    slug: 'procurement',
    color: '#EC4899',
    lightColor: '#FCE7F3',
    darkColor: '#831843',
    icon: 'ShoppingCart',
  },
};

export function getDepartmentMeta(type: string): DepartmentMeta | undefined {
  return DEPARTMENT_REGISTRY[type as DepartmentType];
}

export function getDepartmentLabel(type: string): string {
  return getDepartmentMeta(type)?.label ?? type;
}

export function getDepartmentSlug(type: string): string {
  return getDepartmentMeta(type)?.slug ?? type;
}

export function slugToDepartmentType(slug: string): DepartmentType | undefined {
  for (const [, meta] of Object.entries(DEPARTMENT_REGISTRY)) {
    if (meta.slug === slug) return meta.type;
  }
  return undefined;
}
