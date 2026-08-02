"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  type AppointmentFormInput,
  type AppointmentListParams,
  type AppointmentStatus,
  changeAppointmentStatus,
  createAppointment,
  getAppointment,
  listAppointments,
  updateAppointment,
} from "@/lib/mock/appointments";

// Same `createQueryKeys` factory every feature module uses — swapping the
// mock functions below for real `httpClient` calls later touches only
// this file.
export const appointmentKeys = createQueryKeys<AppointmentListParams>("appointments");

export function useAppointments(params: AppointmentListParams) {
  return useQuery({
    queryKey: appointmentKeys.list(params),
    queryFn: () => listAppointments(params),
  });
}

export function useAppointment(appointmentId: string) {
  return useQuery({
    queryKey: appointmentKeys.detail(appointmentId),
    queryFn: () => getAppointment(appointmentId),
    enabled: Boolean(appointmentId),
  });
}

export function useCreateAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: AppointmentFormInput) => createAppointment(input),
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.setQueryData(appointmentKeys.detail(appointment.appointment_id), appointment);
    },
  });
}

export function useUpdateAppointment(appointmentId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: AppointmentFormInput) => updateAppointment(appointmentId, input),
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.setQueryData(appointmentKeys.detail(appointmentId), appointment);
    },
  });
}

export function useChangeAppointmentStatus(appointmentId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ status, note }: { status: AppointmentStatus; note?: string }) =>
      changeAppointmentStatus(appointmentId, status, note),
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.setQueryData(appointmentKeys.detail(appointmentId), appointment);
    },
  });
}
