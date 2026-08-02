import { ContentContainer } from "@/components/dashboard/content-container";
import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";

interface AppShellProps {
  children: React.ReactNode;
  defaultSidebarOpen?: boolean;
}

// The complete authenticated application shell — every `/dashboard/*`
// page renders inside this via `(dashboard)/layout.tsx`. Marketing pages
// have their own, separate `(marketing)/layout.tsx` and never touch this
// component, so there's no path by which a public page could accidentally
// render the sidebar/topbar.
export function AppShell({ children, defaultSidebarOpen = true }: AppShellProps) {
  return (
    <SidebarProvider defaultOpen={defaultSidebarOpen}>
      <AppSidebar />
      <SidebarInset>
        <AppHeader />
        <ContentContainer>{children}</ContentContainer>
      </SidebarInset>
    </SidebarProvider>
  );
}
