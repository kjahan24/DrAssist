"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  archiveNotification,
  deleteNotification,
  getNotification,
  listNotifications,
  markAllNotificationsAsRead,
  markNotificationAsRead,
  markNotificationAsUnread,
  type NotificationListParams,
} from "@/lib/mock/notifications";

// Same `createQueryKeys` factory every feature module uses — swapping
// the mock functions below for real `httpClient` calls later touches
// only this file.
export const notificationKeys = createQueryKeys<NotificationListParams>("notifications");

export function useNotifications(params: NotificationListParams) {
  return useQuery({
    queryKey: notificationKeys.list(params),
    queryFn: () => listNotifications(params),
  });
}

export function useNotification(notificationId: string) {
  return useQuery({
    queryKey: notificationKeys.detail(notificationId),
    queryFn: () => getNotification(notificationId),
    enabled: Boolean(notificationId),
  });
}

export function useMarkNotificationAsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationId: string) => markNotificationAsRead(notificationId),
    onSuccess: (notification) => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.lists() });
      queryClient.setQueryData(notificationKeys.detail(notification.notification_id), notification);
    },
  });
}

export function useMarkNotificationAsUnread() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationId: string) => markNotificationAsUnread(notificationId),
    onSuccess: (notification) => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.lists() });
      queryClient.setQueryData(notificationKeys.detail(notification.notification_id), notification);
    },
  });
}

export function useMarkAllNotificationsAsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => markAllNotificationsAsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.lists() });
    },
  });
}

export function useArchiveNotification() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationId: string) => archiveNotification(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.lists() });
    },
  });
}

export function useDeleteNotification() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationId: string) => deleteNotification(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.lists() });
    },
  });
}
