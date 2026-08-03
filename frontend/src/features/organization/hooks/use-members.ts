"use client";

import { useQuery } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import { getMember, listMembers, type MemberListParams } from "@/lib/mock/members";

export const memberKeys = createQueryKeys<MemberListParams>("members");

export function useMembers(params: MemberListParams) {
  return useQuery({
    queryKey: memberKeys.list(params),
    queryFn: () => listMembers(params),
  });
}

export function useMember(memberId: string) {
  return useQuery({
    queryKey: memberKeys.detail(memberId),
    queryFn: () => getMember(memberId),
    enabled: Boolean(memberId),
  });
}
