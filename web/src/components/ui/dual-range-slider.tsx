'use client';

import * as SliderPrimitive from '@radix-ui/react-slider';
import * as React from 'react';

import { cn } from '@/lib/utils';

interface DualRangeSliderProps
  extends React.ComponentProps<typeof SliderPrimitive.Root> {
  labelPosition?: 'top' | 'bottom';
  label?: (value: number | undefined) => React.ReactNode;
}

const DualRangeSlider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  DualRangeSliderProps
>(({ className, label, labelPosition = 'top', ...props }, ref) => {
  const initialValue = Array.isArray(props.value)
    ? props.value
    : [props.min, props.max];

  return (
    <SliderPrimitive.Root
      ref={ref}
      className={cn(
        'relative flex w-full touch-none select-none items-center',
        className,
      )}
      {...props}
    >
      <SliderPrimitive.Track className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-muted/30 border border-border/10 shadow-[inset_0_1px_2px_rgba(0,0,0,0.1)] transition-colors">
        <SliderPrimitive.Range className="absolute h-full gradient-primary shadow-glow-sm transition-all duration-300" />
      </SliderPrimitive.Track>
      {initialValue.map((value, index) => (
        <React.Fragment key={index}>
          <SliderPrimitive.Thumb className="relative block h-4 w-4 rounded-full border-2 border-primary bg-background shadow-glow-sm ring-offset-background transition-all duration-300 hover:scale-110 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 cursor-pointer">
            {label && (
              <span
                className={cn(
                  'absolute flex w-full justify-center text-[10px] font-bold tracking-tight text-primary',
                  labelPosition === 'top' && '-top-7',
                  labelPosition === 'bottom' && 'top-4',
                )}
              >
                {label(value)}
              </span>
            )}
          </SliderPrimitive.Thumb>
        </React.Fragment>
      ))}
    </SliderPrimitive.Root>
  );
});
DualRangeSlider.displayName = 'DualRangeSlider';

type SingleSliderProps = Omit<
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>,
  'onChange' | 'value'
> & { onChange: (value: number) => void; value: number };

const SingleFormSlider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  SingleSliderProps
>(({ value, onChange, ...props }, ref) => {
  return (
    <DualRangeSlider
      ref={ref}
      value={[value]}
      onValueChange={(vals) => {
        onChange(vals[0]);
      }}
      {...props}
    />
  );
});

export { DualRangeSlider, SingleFormSlider };
