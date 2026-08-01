// Generic TanStack Query key factory. Every future feature module's
// data-fetching hooks should build their keys from this instead of
// hand-rolling arrays, so cache invalidation stays consistent across all
// ~27 backend-module-mapped features instead of each one inventing its own
// shape.
//
// Usage (once a feature module exists):
//   export const patientKeys = createQueryKeys<PatientListFilters>("patients");
//   useQuery({ queryKey: patientKeys.detail(id), queryFn: () => getPatient(id) });
export function createQueryKeys<TFilters = Record<string, unknown>>(scope: string) {
  return {
    all: [scope] as const,
    lists: () => [scope, "list"] as const,
    list: (filters?: TFilters) => [scope, "list", filters ?? {}] as const,
    details: () => [scope, "detail"] as const,
    detail: (id: string) => [scope, "detail", id] as const,
  };
}
