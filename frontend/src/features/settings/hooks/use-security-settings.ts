"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  changePassword,
  getSecurityOverview,
  listActiveSessions,
  listLoginHistory,
  listTrustedDevices,
  revokeSession,
  setSessionTrusted,
  setTwoFactorEnabled,
  type ChangePasswordInput,
} from "@/lib/mock/settings";

export const securityKeys = createQueryKeys("security");
const sessionKeys = {
  active: ["security", "sessions", "active"] as const,
  history: ["security", "sessions", "history"] as const,
  trusted: ["security", "sessions", "trusted"] as const,
};

export function useSecurityOverview() {
  return useQuery({
    queryKey: securityKeys.detail("current"),
    queryFn: () => getSecurityOverview(),
  });
}

export function useSetTwoFactorEnabled() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (enabled: boolean) => setTwoFactorEnabled(enabled),
    onSuccess: (overview) => {
      queryClient.setQueryData(securityKeys.detail("current"), overview);
    },
  });
}

export function useChangePassword() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: ChangePasswordInput) => changePassword(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: securityKeys.detail("current") });
    },
  });
}

export function useActiveSessions() {
  return useQuery({ queryKey: sessionKeys.active, queryFn: () => listActiveSessions() });
}

export function useLoginHistory() {
  return useQuery({ queryKey: sessionKeys.history, queryFn: () => listLoginHistory() });
}

export function useTrustedDevices() {
  return useQuery({ queryKey: sessionKeys.trusted, queryFn: () => listTrustedDevices() });
}

function invalidateAllSessionQueries(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: sessionKeys.active });
  queryClient.invalidateQueries({ queryKey: sessionKeys.history });
  queryClient.invalidateQueries({ queryKey: sessionKeys.trusted });
}

export function useRevokeSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) => revokeSession(sessionId),
    onSuccess: () => invalidateAllSessionQueries(queryClient),
  });
}

export function useSetSessionTrusted() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, trusted }: { sessionId: string; trusted: boolean }) =>
      setSessionTrusted(sessionId, trusted),
    onSuccess: () => invalidateAllSessionQueries(queryClient),
  });
}
