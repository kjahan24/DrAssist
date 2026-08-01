"use client";

import { ResponsiveContainer } from "recharts";

import { cn } from "@/lib/utils";

interface ChartContainerProps {
  children: React.ReactElement;
  height?: number;
  className?: string;
}

// Every chart wrapper in this directory renders inside one of these —
// keeps the ResponsiveContainer height/margin convention consistent
// instead of each chart picking its own.
export function ChartContainer({ children, height = 300, className }: ChartContainerProps) {
  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}
