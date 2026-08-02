"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  type VisitFormInput,
  type VisitListParams,
  createVisit,
  getVisit,
  listVisits,
  updateVisit,
} from "@/lib/mock/visits";

// Same `createQueryKeys` factory every feature module uses — swapping the
// mock functions below for real `httpClient` calls later touches only
// this file.
export const visitKeys = createQueryKeys<VisitListParams>("visits");

export function useVisits(params: VisitListParams) {
  return useQuery({
    queryKey: visitKeys.list(params),
    queryFn: () => listVisits(params),
  });
}

export function useVisit(visitId: string) {
  return useQuery({
    queryKey: visitKeys.detail(visitId),
    queryFn: () => getVisit(visitId),
    enabled: Boolean(visitId),
  });
}

export function useCreateVisit() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: VisitFormInput) => createVisit(input),
    onSuccess: (visit) => {
      queryClient.invalidateQueries({ queryKey: visitKeys.lists() });
      queryClient.setQueryData(visitKeys.detail(visit.visit_id), visit);
    },
  });
}

export function useUpdateVisit(visitId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: VisitFormInput) => updateVisit(visitId, input),
    onSuccess: (visit) => {
      queryClient.invalidateQueries({ queryKey: visitKeys.lists() });
      queryClient.setQueryData(visitKeys.detail(visitId), visit);
    },
  });
}
