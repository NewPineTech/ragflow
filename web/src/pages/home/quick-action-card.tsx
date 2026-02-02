import { cn } from '@/lib/utils';
import { ArrowRight, Sparkles } from 'lucide-react';
import React from 'react';

interface QuickActionCardProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  gradient?: boolean;
}

export const QuickActionCard = ({
  title,
  description,
  icon,
  onClick,
  gradient = false,
}: QuickActionCardProps) => {
  return (
    <button
      onClick={onClick}
      className={cn(
        'group relative flex flex-col p-6 rounded-xl border transition-all duration-300',
        'text-left w-full',
        gradient
          ? 'bg-gradient-to-br from-primary/10 to-accent/10 border-primary/20 hover:border-primary/40'
          : 'bg-card border-border hover:border-primary/20 hover:bg-card/80',
      )}
    >
      <div
        className={cn(
          'flex items-center justify-center w-12 h-12 rounded-lg mb-4 transition-transform group-hover:scale-105',
          gradient ? 'gradient-primary shadow-glow' : 'bg-muted',
        )}
      >
        {icon}
      </div>

      <h3 className="text-lg font-semibold text-foreground mb-2 flex items-center gap-2">
        {title}
        {gradient && (
          <Sparkles size={16} className="text-primary animate-pulse" />
        )}
      </h3>

      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
        {description}
      </p>

      <div className="flex items-center text-sm text-primary font-medium opacity-0 group-hover:opacity-100 transition-all transform translate-x-[-10px] group-hover:translate-x-0">
        Get started
        <ArrowRight
          size={14}
          className="ml-1 transition-transform group-hover:translate-x-1"
        />
      </div>
    </button>
  );
};
