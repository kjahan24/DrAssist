"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  type PrescriptionFormInput,
  type PrescriptionListParams,
  type PrescriptionStatus,
  createPrescription,
  getPrescription,
  listPrescriptions,
  updatePrescription,
} from "@/lib/mock/prescriptions";

// Same `createQueryKeys` factory every feature module uses — swapping
// the mock functions below for real `httpClient` calls later touches
// only this file.
export const prescriptionKeys = createQueryKeys<PrescriptionListParams>("prescriptions");

export function usePrescriptions(params: PrescriptionListParams) {
  return useQuery({
    queryKey: prescriptionKeys.list(params),
    queryFn: () => listPrescriptions(params),
  });
}

export function usePrescription(prescriptionId: string) {
  return useQuery({
    queryKey: prescriptionKeys.detail(prescriptionId),
    queryFn: () => getPrescription(prescriptionId),
    enabled: Boolean(prescriptionId),
  });
}

export function useCreatePrescription() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ input, status }: { input: PrescriptionFormInput; status: PrescriptionStatus }) =>
      createPrescription(input, status),
    onSuccess: (prescription) => {
      queryClient.invalidateQueries({ queryKey: prescriptionKeys.lists() });
      queryClient.setQueryData(prescriptionKeys.detail(prescription.prescription_id), prescription);
    },
  });
}

export function useUpdatePrescription(prescriptionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ input, status }: { input: PrescriptionFormInput; status: PrescriptionStatus }) =>
      updatePrescription(prescriptionId, input, status),
    onSuccess: (prescription) => {
      queryClient.invalidateQueries({ queryKey: prescriptionKeys.lists() });
      queryClient.setQueryData(prescriptionKeys.detail(prescriptionId), prescription);
    },
  });
}
