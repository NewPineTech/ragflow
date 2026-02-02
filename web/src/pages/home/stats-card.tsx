import { cn } from '@/lib/utils';
import React from 'react';

interface StatsCardProps {
  label: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon?: React.ReactNode;
}

export const HomeStatsCard = ({
  label,
  value,
  change,
  changeType = 'neutral',
  icon,
}: StatsCardProps) => {
  return (
    <div className="flex flex-col p-5 rounded-xl bg-card border border-border shadow-sm transition-all hover:shadow-md">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-muted-foreground">
          {label}
        </span>
        {icon && <div className="text-primary/70">{icon}</div>}
      </div>

      <div className="flex items-end gap-2">
        <span className="text-2xl font-bold text-foreground">{value}</span>
        {change && (
          <span
            className={cn(
              'text-xs font-medium mb-1',
              changeType === 'positive' && 'text-green-500',
              changeType === 'negative' && 'text-destructive',
              changeType === 'neutral' && 'text-muted-foreground',
            )}
          >
            {change}
          </span>
        )}
      </div>
    </div>
  );
};
