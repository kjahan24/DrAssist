import { cn } from "@/lib/utils";

export function ContentContainer({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("flex flex-1 flex-col gap-4 p-4 md:p-6", className)}>{children}</div>;
}
