"use client";

import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { PERMISSION_FIELDS, type FamilyMemberPermissions } from "@/lib/mock/family-members";

interface PermissionToggleGroupProps {
  permissions: FamilyMemberPermissions;
  onChange: (permissions: FamilyMemberPermissions) => void;
  disabled?: boolean;
}

// The editable counterpart to `PermissionMatrix` — used by
// `FamilyInvitationForm`'s "Custom Permissions" mode, where the invited
// member's per-area access can be adjusted individually away from their
// access level's default set (see `getDefaultPermissions()` in
// `lib/mock/family-members.ts`).
export function PermissionToggleGroup({
  permissions,
  onChange,
  disabled,
}: PermissionToggleGroupProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {PERMISSION_FIELDS.map((field) => {
        const inputId = `permission-${field.key}`;
        return (
          <div
            key={field.key}
            className="flex items-center justify-between gap-3 rounded-md border p-3"
          >
            <Label htmlFor={inputId} className="text-sm font-normal">
              {field.label}
            </Label>
            <Switch
              id={inputId}
              checked={permissions[field.key]}
              disabled={disabled}
              onCheckedChange={(checked) => onChange({ ...permissions, [field.key]: checked })}
            />
          </div>
        );
      })}
    </div>
  );
}
