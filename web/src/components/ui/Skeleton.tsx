import { cn } from '../../lib/utils';

interface SkeletonProps {
  variant?: 'text' | 'circle' | 'rect' | 'card';
  width?: string | number;
  height?: string | number;
  count?: number;
  className?: string;
}

function SkeletonItem({ variant = 'text', width, height, className }: Omit<SkeletonProps, 'count'>) {
  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === 'number' ? `${width}px` : width;
  if (height) style.height = typeof height === 'number' ? `${height}px` : height;

  return (
    <div
      className={cn(
        'animate-pulse bg-neutral-200 dark:bg-neutral-700',
        variant === 'text' && 'h-4 rounded',
        variant === 'circle' && 'rounded-full',
        variant === 'rect' && 'rounded-lg',
        variant === 'card' && 'rounded-xl h-32',
        !width && variant === 'text' && 'w-full',
        !width && variant === 'circle' && 'w-10 h-10',
        !width && variant === 'rect' && 'w-full h-20',
        !width && variant === 'card' && 'w-full',
        className,
      )}
      style={style}
    />
  );
}

export function Skeleton({ count = 1, ...props }: SkeletonProps) {
  if (count === 1) return <SkeletonItem {...props} />;

  return (
    <div className="space-y-3">
      {Array.from({ length: count }, (_, i) => (
        <SkeletonItem key={i} {...props} />
      ))}
    </div>
  );
}
