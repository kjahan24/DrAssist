"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  type PatientFormInput,
  type PatientListParams,
  createPatient,
  getPatient,
  listPatients,
  updatePatient,
} from "@/lib/mock/patients";

// Built on the same `createQueryKeys` factory every feature module is
// expected to use (`lib/query-keys.ts`) — `list(filters)` and `detail(id)`
// already match the shape a real `/patients` API client would use, so
// swapping the mock functions below for real `httpClient` calls later
// touches only this file.
export const patientKeys = createQueryKeys<PatientListParams>("patients");

export function usePatients(params: PatientListParams) {
  return useQuery({
    queryKey: patientKeys.list(params),
    queryFn: () => listPatients(params),
  });
}

export function usePatient(patientId: string) {
  return useQuery({
    queryKey: patientKeys.detail(patientId),
    queryFn: () => getPatient(patientId),
    enabled: Boolean(patientId),
  });
}

export function useCreatePatient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: PatientFormInput) => createPatient(input),
    onSuccess: (patient) => {
      queryClient.invalidateQueries({ queryKey: patientKeys.lists() });
      queryClient.setQueryData(patientKeys.detail(patient.patient_id), patient);
    },
  });
}

export function useUpdatePatient(patientId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: PatientFormInput) => updatePatient(patientId, input),
    onSuccess: (patient) => {
      queryClient.invalidateQueries({ queryKey: patientKeys.lists() });
      queryClient.setQueryData(patientKeys.detail(patientId), patient);
    },
  });
}
