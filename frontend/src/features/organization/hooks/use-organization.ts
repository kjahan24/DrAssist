"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  getOrganization,
  updateLogo,
  updateOrganization,
  type OrganizationFormInput,
} from "@/lib/mock/organization";

// A single-record resource — `detail("current")` is the only key this
// ever needs, same reasoning as `profileKeys`.
export const organizationKeys = createQueryKeys("organization");

export function useOrganization() {
  return useQuery({
    queryKey: organizationKeys.detail("current"),
    queryFn: () => getOrganization(),
  });
}

export function useUpdateOrganization() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: OrganizationFormInput) => updateOrganization(input),
    onSuccess: (organization) => {
      queryClient.setQueryData(organizationKeys.detail("current"), organization);
    },
  });
}

export function useUpdateLogo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (logoUrl: string | null) => updateLogo(logoUrl),
    onSuccess: (organization) => {
      queryClient.setQueryData(organizationKeys.detail("current"), organization);
    },
  });
}
