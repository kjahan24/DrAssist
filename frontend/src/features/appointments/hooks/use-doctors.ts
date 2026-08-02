"use client";

import { useQuery } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import { type DoctorListParams, getDoctor, listDoctors } from "@/lib/mock/doctors";

export const doctorKeys = createQueryKeys<DoctorListParams>("doctors");

export function useDoctors(params: DoctorListParams = {}) {
  return useQuery({
    queryKey: doctorKeys.list(params),
    queryFn: () => listDoctors(params),
  });
}

export function useDoctor(doctorId: string) {
  return useQuery({
    queryKey: doctorKeys.detail(doctorId),
    queryFn: () => getDoctor(doctorId),
    enabled: Boolean(doctorId),
  });
}
