import { Skeleton } from "@/components/ui/skeleton";

export default function RootLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Skeleton className="h-8 w-8 rounded-full" />
    </div>
  );
}
