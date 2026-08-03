import { UsersRound } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { OrganizationStatusBadge } from "@/features/organization/components/organization-status-badge";
import type { Department } from "@/lib/mock/departments";

// The task's own "Display" wording (not "Columns", like Members) implies
// a card grid rather than a data table — `/dashboard/organization/departments`
// renders a grid of these.
export function DepartmentCard({ department }: { department: Department }) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-semibold">{department.name}</p>
          <OrganizationStatusBadge status={department.status} />
        </div>
        {department.description && (
          <p className="text-sm text-muted-foreground">{department.description}</p>
        )}
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Head of Department</dt>
            <dd className="truncate">{department.head_of_department_name ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Members</dt>
            <dd className="flex items-center gap-1.5">
              <UsersRound className="size-3.5 text-muted-foreground" aria-hidden="true" />
              {department.member_count}
            </dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
