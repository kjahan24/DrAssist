import { Check, X } from "lucide-react";

import { PERMISSION_FIELDS, type FamilyMemberPermissions } from "@/lib/mock/family-members";
import { cn } from "@/lib/utils";

// The read-only counterpart to `PermissionToggleGroup` — used by the
// Family Member Details page's "Permissions Summary" section. There is
// no real backend "update permissions" use case for an existing grant
// (only `InviteCaregiver` sets them, at invite time — see
// `lib/mock/family-members.ts`'s own docstring), so this is display-only
// by design, not just by omission.
export function PermissionMatrix({ permissions }: { permissions: FamilyMemberPermissions }) {
  return (
    <ul className="grid gap-2 sm:grid-cols-2">
      {PERMISSION_FIELDS.map((field) => {
        const granted = permissions[field.key];
        return (
          <li
            key={field.key}
            className={cn(
              "flex items-center gap-2 rounded-md border px-3 py-2 text-sm",
              granted ? "border-emerald-200 dark:border-emerald-900" : "text-muted-foreground",
            )}
          >
            {granted ? (
              <Check
                className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400"
                aria-hidden="true"
              />
            ) : (
              <X className="size-4 shrink-0" aria-hidden="true" />
            )}
            <span>{field.label}</span>
            <span className="sr-only">{granted ? "granted" : "not granted"}</span>
          </li>
        );
      })}
    </ul>
  );
}
