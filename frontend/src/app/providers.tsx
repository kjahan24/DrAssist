"use client";

import { useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { ThemeProvider } from "next-themes";
import { NextIntlClientProvider } from "next-intl";

import { ConfirmDialogProvider } from "@/components/shared/modals/confirm-dialog-provider";
import { Toaster } from "@/components/ui/sonner";
import { createQueryClient } from "@/lib/query-client";
import messages from "@/messages/en.json";

export function Providers({ children }: { children: React.ReactNode }) {
  // useState (not useMemo/module-level) guarantees exactly one QueryClient
  // per browser session and none shared across server-rendered requests —
  // see `lib/query-client.ts`.
  const [queryClient] = useState(() => createQueryClient());

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <NextIntlClientProvider locale="en" messages={messages} timeZone="UTC">
        <QueryClientProvider client={queryClient}>
          {children}
          <ConfirmDialogProvider />
          <Toaster richColors position="top-right" />
          {process.env.NODE_ENV === "development" && <ReactQueryDevtools initialIsOpen={false} />}
        </QueryClientProvider>
      </NextIntlClientProvider>
    </ThemeProvider>
  );
}
