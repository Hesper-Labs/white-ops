import { cn } from '../../lib/utils';

interface BadgeProps {
  variant: 'success' | 'warning' | 'error' | 'info' | 'default' | 'primary';
  children: React.ReactNode;
  dot?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

const variantStyles: Record<BadgeProps['variant'], string> = {
  success: 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800',
  warning: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800',
  error: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800',
  info: 'bg-neutral-100 text-neutral-700 border-neutral-300 dark:bg-neutral-700 dark:text-neutral-300 dark:border-neutral-600',
  default: 'bg-neutral-50 text-neutral-600 border-neutral-200 dark:bg-neutral-800 dark:text-neutral-300 dark:border-neutral-700',
  primary: 'bg-neutral-900 text-white border-neutral-900 dark:bg-white dark:text-neutral-900 dark:border-white',
};

const dotStyles: Record<BadgeProps['variant'], string> = {
  success: 'bg-green-500',
  warning: 'bg-amber-500',
  error: 'bg-red-500',
  info: 'bg-neutral-500',
  default: 'bg-neutral-400',
  primary: 'bg-white dark:bg-neutral-900',
};

export function Badge({ variant, children, dot, size = 'md', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-0.5 text-xs',
        variantStyles[variant],
        className,
      )}
    >
      {dot && (
        <span className={cn('rounded-full flex-shrink-0', size === 'sm' ? 'h-1.5 w-1.5' : 'h-2 w-2', dotStyles[variant])} />
      )}
      {children}
    </span>
  );
}
