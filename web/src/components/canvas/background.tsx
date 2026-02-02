import { Background } from '@xyflow/react';

export function AgentBackground() {
  return (
    <Background
      color="hsl(var(--foreground) / 0.1)"
      bgColor="hsl(var(--bg-canvas))"
      className="rounded-lg"
    />
  );
}
