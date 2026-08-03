"use client";

import { useQuery } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import { type MedicationListParams, getMedication, listMedications } from "@/lib/mock/medications";

export const medicationKeys = createQueryKeys<MedicationListParams>("medications");

export function useMedications(params: MedicationListParams = {}) {
  return useQuery({
    queryKey: medicationKeys.list(params),
    queryFn: () => listMedications(params),
  });
}

export function useMedication(medicationId: string) {
  return useQuery({
    queryKey: medicationKeys.detail(medicationId),
    queryFn: () => getMedication(medicationId),
    enabled: Boolean(medicationId),
  });
}
