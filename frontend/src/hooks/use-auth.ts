"use client";

import { useRouter } from "next/navigation";

import { hasAnyPermission, hasPermission } from "@/lib/auth/permissions";
import { tokenStorage } from "@/lib/auth/token-storage";
import { useAuthStore } from "@/store/auth-store";

export function useAuth() {
  const router = useRouter();
  const principal = useAuthStore((state) => state.principal);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const clear = useAuthStore((state) => state.clear);

  function logout(): void {
    tokenStorage.clear();
    clear();
    router.push("/login");
  }

  function can(permissionCode: string): boolean {
    return hasPermission(principal, permissionCode);
  }

  function canAny(permissionCodes: string[]): boolean {
    return hasAnyPermission(principal, permissionCodes);
  }

  return { principal, isAuthenticated, logout, can, canAny };
}
