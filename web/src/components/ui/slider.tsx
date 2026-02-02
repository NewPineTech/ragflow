'use client';

import * as SliderPrimitive from '@radix-ui/react-slider';
import * as React from 'react';

import { cn } from '@/lib/utils';

const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>
>(({ className, ...props }, ref) => (
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
    <SliderPrimitive.Thumb className="block h-5 w-5 rounded-full border-2 border-primary bg-background shadow-glow-sm ring-offset-background transition-all duration-300 hover:scale-110 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 cursor-pointer" />
  </SliderPrimitive.Root>
));
Slider.displayName = SliderPrimitive.Root.displayName;

type SliderProps = Omit<
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>,
  'onChange' | 'value'
> & { onChange: (value: number) => void; value: number };

const FormSlider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  SliderProps
>(({ onChange, value, ...props }, ref) => (
  <Slider
    ref={ref}
    {...props}
    value={[value]}
    onValueChange={(vals) => {
      onChange(vals[0]);
    }}
  ></Slider>
));

Slider.displayName = SliderPrimitive.Root.displayName;

export { FormSlider, Slider };
