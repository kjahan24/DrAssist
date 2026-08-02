import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";

interface DoctorDashboardHeaderProps {
  doctorName?: string;
  organizationName?: string;
  isLoading?: boolean;
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

// The greeting and date are computed from the actual current time — not
// mock data. Only `doctorName`/`organizationName` come from the mock
// profile service: the real `AuthenticatedPrincipal` only carries
// identity + permissions, no display name or organization name, and no
// backend endpoint to look either up exists yet (see
// `lib/mock/doctor-dashboard.ts`).
//
// The <h1> is always rendered with real text, loading or not — it's the
// page's only heading, so it can never be swapped out for a skeleton the
// way a section's body content can. Only the doctor's name (appended once
// known) and the subtitle line progressively enhance in.
export function DoctorDashboardHeader({
  doctorName,
  organizationName,
  isLoading,
}: DoctorDashboardHeaderProps) {
  const greeting = getGreeting();
  const title = doctorName ? `${greeting}, ${doctorName}` : greeting;

  return (
    <div className="space-y-1">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
      {isLoading || !organizationName ? (
        <Skeleton className="h-4 w-48" />
      ) : (
        <p className="text-sm text-muted-foreground">
          {organizationName} · {formatDate(new Date(), "EEEE, MMMM d, yyyy")}
        </p>
      )}
    </div>
  );
}
