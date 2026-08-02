import { DoctorDashboardContent } from "@/features/dashboard/components/doctor-dashboard-content";

export const metadata = { title: "Dashboard" };

// The doctor's operational overview — not the EMR. All data on this page
// comes from `lib/mock/doctor-dashboard.ts` via
// `features/dashboard/hooks/use-doctor-dashboard.ts` (TanStack Query),
// the same architecture real endpoints will use later — see that mock
// file's own docstring for the swap-out contract.
export default function DashboardPage() {
  return <DoctorDashboardContent />;
}
