"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { familyMemberKeys } from "@/features/family/hooks/use-family-members";
import {
  cancelInvitation,
  createInvitation,
  getInvitation,
  listInvitations,
  resendInvitation,
  type CreateInvitationInput,
  type InvitationListParams,
} from "@/lib/mock/family-invitations";
import { createQueryKeys } from "@/lib/query-keys";

// Invitations and family members share exactly one underlying mock array
// (see `lib/mock/family-invitations.ts`'s own docstring) — this hook file
// mirrors that by invalidating/updating `familyMemberKeys` cache entries
// too, so a mutation made from the Invitations page is immediately
// reflected on the main `/dashboard/family` list without a manual
// refetch.
export const familyInvitationKeys = createQueryKeys<InvitationListParams>("family-invitations");

export function useInvitations(params: InvitationListParams) {
  return useQuery({
    queryKey: familyInvitationKeys.list(params),
    queryFn: () => listInvitations(params),
  });
}

export function useInvitation(familyAccessId: string) {
  return useQuery({
    queryKey: familyInvitationKeys.detail(familyAccessId),
    queryFn: () => getInvitation(familyAccessId),
    enabled: Boolean(familyAccessId),
  });
}

export function useCreateInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateInvitationInput) => createInvitation(input),
    onSuccess: (member) => {
      queryClient.invalidateQueries({ queryKey: familyInvitationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: familyMemberKeys.lists() });
      queryClient.setQueryData(familyInvitationKeys.detail(member.family_access_id), member);
      queryClient.setQueryData(familyMemberKeys.detail(member.family_access_id), member);
    },
  });
}

export function useResendInvitation(familyAccessId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => resendInvitation(familyAccessId),
    onSuccess: (member) => {
      queryClient.invalidateQueries({ queryKey: familyInvitationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: familyMemberKeys.lists() });
      queryClient.setQueryData(familyInvitationKeys.detail(familyAccessId), member);
      queryClient.setQueryData(familyMemberKeys.detail(familyAccessId), member);
    },
  });
}

export function useCancelInvitation(familyAccessId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => cancelInvitation(familyAccessId),
    onSuccess: (member) => {
      queryClient.invalidateQueries({ queryKey: familyInvitationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: familyMemberKeys.lists() });
      queryClient.setQueryData(familyInvitationKeys.detail(familyAccessId), member);
      queryClient.setQueryData(familyMemberKeys.detail(familyAccessId), member);
    },
  });
}
