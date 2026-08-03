"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import { getProfile, updateAvatar, updateProfile, type ProfileFormInput } from "@/lib/mock/profile";

// A single-record resource — `detail("current")` is the only key this
// ever needs, same reasoning as `notificationPreferenceKeys`.
export const profileKeys = createQueryKeys("profile");

export function useProfile() {
  return useQuery({
    queryKey: profileKeys.detail("current"),
    queryFn: () => getProfile(),
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: ProfileFormInput) => updateProfile(input),
    onSuccess: (profile) => {
      queryClient.setQueryData(profileKeys.detail("current"), profile);
    },
  });
}

export function useUpdateAvatar() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (avatarUrl: string | null) => updateAvatar(avatarUrl),
    onSuccess: (profile) => {
      queryClient.setQueryData(profileKeys.detail("current"), profile);
    },
  });
}
