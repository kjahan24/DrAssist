"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  getUserPreferences,
  updateUserPreferences,
  type UserPreferences,
} from "@/lib/mock/settings";

export const preferencesKeys = createQueryKeys("preferences");

export function useUserPreferences() {
  return useQuery({
    queryKey: preferencesKeys.detail("current"),
    queryFn: () => getUserPreferences(),
  });
}

export function useUpdateUserPreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: UserPreferences) => updateUserPreferences(input),
    onSuccess: (preferences) => {
      queryClient.setQueryData(preferencesKeys.detail("current"), preferences);
    },
  });
}
