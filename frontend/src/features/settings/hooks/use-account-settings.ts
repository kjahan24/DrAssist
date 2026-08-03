"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  getAccountSettings,
  updateAccountSettings,
  type AccountSettings,
} from "@/lib/mock/settings";

export const accountSettingsKeys = createQueryKeys("account-settings");

export function useAccountSettings() {
  return useQuery({
    queryKey: accountSettingsKeys.detail("current"),
    queryFn: () => getAccountSettings(),
  });
}

export function useUpdateAccountSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: AccountSettings) => updateAccountSettings(input),
    onSuccess: (settings) => {
      queryClient.setQueryData(accountSettingsKeys.detail("current"), settings);
    },
  });
}
