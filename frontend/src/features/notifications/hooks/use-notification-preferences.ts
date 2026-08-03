"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  getNotificationPreferences,
  updateNotificationPreferences,
  type NotificationPreferences,
} from "@/lib/mock/notifications";

// A single-row settings resource — `detail("current")` is the only key
// this ever needs, matching how every other module keys its own
// singleton reads (there is no "list" of preference sets).
export const notificationPreferenceKeys = createQueryKeys("notification-preferences");

export function useNotificationPreferences() {
  return useQuery({
    queryKey: notificationPreferenceKeys.detail("current"),
    queryFn: () => getNotificationPreferences(),
  });
}

export function useUpdateNotificationPreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: NotificationPreferences) => updateNotificationPreferences(input),
    onSuccess: (preferences) => {
      queryClient.setQueryData(notificationPreferenceKeys.detail("current"), preferences);
    },
  });
}
