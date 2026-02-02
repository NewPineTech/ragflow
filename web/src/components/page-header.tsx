import { cn } from '@/lib/utils';
import { PropsWithChildren } from 'react';

interface IProps {
  className?: string;
}

export function PageHeader({ children, className }: PropsWithChildren<IProps>) {
  return (
    <header
      className={cn(
        'flex justify-between items-center bg-bg-base p-5',
        className,
      )}
    >
      {children}
    </header>
  );
}
