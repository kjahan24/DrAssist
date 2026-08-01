import { create } from "zustand";

import type { AuthenticatedPrincipal } from "@/types";

interface AuthState {
  principal: AuthenticatedPrincipal | null;
  isAuthenticated: boolean;
  setPrincipal: (principal: AuthenticatedPrincipal) => void;
  clear: () => void;
}

// Client-side mirror of the caller's identity, hydrated once a session
// exists. Never the source of truth for authorization — every request is
// still authorized server-side; this only drives UI (nav visibility,
// avatar, permission-gated controls). See `hooks/use-auth.ts` for the
// consumer-facing API.
export const useAuthStore = create<AuthState>((set) => ({
  principal: null,
  isAuthenticated: false,
  setPrincipal: (principal) => set({ principal, isAuthenticated: true }),
  clear: () => set({ principal: null, isAuthenticated: false }),
}));
