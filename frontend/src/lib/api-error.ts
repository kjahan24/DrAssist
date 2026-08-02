// Split out from `lib/api-client.ts` so consumers that only need the
// error *type* — `lib/query-client.ts`'s retry logic and
// `lib/auth/apply-server-errors.ts`'s field-error mapping — don't
// transitively import the live `httpClient` axios instance. JS modules
// execute in full on import, so importing `ApiError` from
// `lib/api-client.ts` used to also run that file's `axios.create(...)`
// and interceptor setup. `lib/query-client.ts` is loaded by the root
// `Providers` for every single page, so that meant every page in the
// app — including every frontend-mock-only module (Patients,
// Appointments, Visits, Clinical Notes, ...) — bundled a configured,
// network-capable client it was never supposed to reference at all.
// `lib/api-client.ts` still owns and re-exports `ApiError` so the real
// backend-integrated auth pages that need both it and `httpClient`
// together are unaffected.
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly errorCode: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
