import { cookies } from "next/headers";

import { AppShell } from "@/components/dashboard/app-shell";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  // Reading the sidebar's own persisted cookie server-side so the first
  // paint already matches the user's last collapsed/expanded state,
  // instead of always opening and then flashing shut on hydration.
  const cookieStore = await cookies();
  const defaultOpen = cookieStore.get("sidebar_state")?.value !== "false";

  return <AppShell defaultSidebarOpen={defaultOpen}>{children}</AppShell>;
}
