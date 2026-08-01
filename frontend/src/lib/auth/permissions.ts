import type { AuthenticatedPrincipal } from "@/types";

// Mirrors the backend's RBAC model: `AuthenticatedPrincipalDTO.permissions`
// (`app.modules.authentication.application.dto`) is a flat set of
// permission codes resolved server-side from the caller's assigned roles —
// the frontend never computes permissions itself, only checks membership.
export function hasPermission(
  principal: AuthenticatedPrincipal | null,
  permissionCode: string,
): boolean {
  if (!principal) return false;
  return principal.permissions.includes(permissionCode);
}

export function hasAnyPermission(
  principal: AuthenticatedPrincipal | null,
  permissionCodes: string[],
): boolean {
  return permissionCodes.some((code) => hasPermission(principal, code));
}
