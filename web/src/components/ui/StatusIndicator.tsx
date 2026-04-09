import { cn } from '../../lib/utils';

interface StatusIndicatorProps {
  status: 'online' | 'offline' | 'busy' | 'error' | 'idle' | 'maintenance';
  label?: string;
  pulse?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const statusColors: Record<StatusIndicatorProps['status'], string> = {
  online: 'bg-green-500',
  offline: 'bg-neutral-400 dark:bg-neutral-500',
  busy: 'bg-amber-500',
  error: 'bg-red-500',
  idle: 'bg-yellow-400',
  maintenance: 'bg-blue-500',
};

const statusLabels: Record<StatusIndicatorProps['status'], string> = {
  online: 'Online',
  offline: 'Offline',
  busy: 'Busy',
  error: 'Error',
  idle: 'Idle',
  maintenance: 'Maintenance',
};

const sizeStyles: Record<NonNullable<StatusIndicatorProps['size']>, string> = {
  sm: 'h-2 w-2',
  md: 'h-2.5 w-2.5',
  lg: 'h-3 w-3',
};

export function StatusIndicator({ status, label, pulse, size = 'md' }: StatusIndicatorProps) {
  const shouldPulse = pulse ?? (status === 'online' || status === 'busy');

  return (
    <span className="inline-flex items-center gap-2">
      <span className="relative flex-shrink-0">
        <span className={cn('block rounded-full', sizeStyles[size], statusColors[status])} />
        {shouldPulse && (
          <span
            className={cn(
              'absolute inset-0 rounded-full animate-ping opacity-75',
              statusColors[status],
            )}
          />
        )}
      </span>
      {label !== undefined ? (
        <span className="text-xs text-neutral-600 dark:text-neutral-400">{label}</span>
      ) : (
        <span className="text-xs text-neutral-600 dark:text-neutral-400">{statusLabels[status]}</span>
      )}
    </span>
  );
}
