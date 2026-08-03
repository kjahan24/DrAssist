"use client";

import { useQuery } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import { listLocations, type LocationListParams } from "@/lib/mock/locations";

export const locationKeys = createQueryKeys<LocationListParams>("locations");

export function useLocations(params: LocationListParams = {}) {
  return useQuery({
    queryKey: locationKeys.list(params),
    queryFn: () => listLocations(params),
  });
}
