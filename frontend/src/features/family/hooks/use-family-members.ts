"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  getFamilyMember,
  listFamilyMembers,
  revokeFamilyMember,
  type FamilyMemberListParams,
} from "@/lib/mock/family-members";

// Same `createQueryKeys` factory every feature module uses — swapping
// the mock functions below for real `httpClient` calls later touches
// only this file.
export const familyMemberKeys = createQueryKeys<FamilyMemberListParams>("family-members");

export function useFamilyMembers(params: FamilyMemberListParams) {
  return useQuery({
    queryKey: familyMemberKeys.list(params),
    queryFn: () => listFamilyMembers(params),
  });
}

export function useFamilyMember(familyAccessId: string) {
  return useQuery({
    queryKey: familyMemberKeys.detail(familyAccessId),
    queryFn: () => getFamilyMember(familyAccessId),
    enabled: Boolean(familyAccessId),
  });
}

export function useRevokeFamilyMember(familyAccessId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => revokeFamilyMember(familyAccessId),
    onSuccess: (member) => {
      queryClient.invalidateQueries({ queryKey: familyMemberKeys.lists() });
      queryClient.setQueryData(familyMemberKeys.detail(familyAccessId), member);
    },
  });
}
