import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { ApiError } from "@/lib/api-error";

interface PydanticValidationIssue {
  loc: (string | number)[];
  msg: string;
  type: string;
}

function isPydanticValidationIssues(details: unknown): details is PydanticValidationIssue[] {
  return (
    Array.isArray(details) &&
    details.every(
      (item) =>
        typeof item === "object" &&
        item !== null &&
        "loc" in item &&
        "msg" in item &&
        Array.isArray((item as PydanticValidationIssue).loc),
    )
  );
}

// A 422 from this backend carries `details: [{loc: ["body", "email"], msg,
// type}, ...]` (`app.middlewares.error_handler.handle_validation_error`,
// itself FastAPI/Pydantic's own `RequestValidationError.errors()` shape).
// This maps each issue onto the matching RHF field so backend validation
// renders inline, next to the field it's actually about, instead of only
// as a generic top-level message. Returns the count of fields it could
// map — callers fall back to a generic `ErrorAlert` for the remainder (or
// entirely, for non-422 errors, which have no `details` array at all).
export function applyServerErrors<TFieldValues extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<TFieldValues>,
  knownFields: readonly string[],
): number {
  if (!(error instanceof ApiError) || !isPydanticValidationIssues(error.details)) {
    return 0;
  }

  let applied = 0;
  for (const issue of error.details) {
    const fieldName = issue.loc[issue.loc.length - 1];
    if (typeof fieldName === "string" && knownFields.includes(fieldName)) {
      setError(fieldName as Path<TFieldValues>, { type: "server", message: issue.msg });
      applied += 1;
    }
  }
  return applied;
}
