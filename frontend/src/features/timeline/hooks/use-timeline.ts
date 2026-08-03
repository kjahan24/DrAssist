"use client";

import { useQuery } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import { getPatientTimeline } from "@/lib/mock/timeline";

// `getPatientTimeline` has no list-params shape to key on (it always
// returns one patient's *entire* event history — filtering happens
// client-side afterward, see `lib/mock/timeline.ts`'s own docstring), so
// this only ever needs `detail(patientId)`, never `list(params)`.
export const timelineKeys = createQueryKeys("timeline");

export function usePatientTimeline(patientId: string) {
  return useQuery({
    queryKey: timelineKeys.detail(patientId),
    queryFn: () => getPatientTimeline(patientId),
    enabled: Boolean(patientId),
  });
}
