import { Badge } from "@/components/ui/badge";

type GenericStatus = "active" | "inactive" | "under_maintenance";

const STATUS_LABEL: Record<GenericStatus, string> = {
  active: "Active",
  inactive: "Inactive",
  under_maintenance: "Under Maintenance",
};

const STATUS_VARIANT: Record<GenericStatus, "default" | "outline" | "secondary" | "destructive"> = {
  active: "default",
  inactive: "secondary",
  under_maintenance: "destructive",
};

interface OrganizationStatusBadgeProps {
  status: GenericStatus;
  label?: string;
}

// Shared across every status vocabulary in this module — the
// Organization itself (`is_active: boolean`, mapped to "active"/
// "inactive" by the caller), Departments (`DepartmentStatus`), and
// Locations (`LocationStatus`, which adds "under_maintenance") all
// reduce to this same three-value shape, so one badge covers all three
// rather than three near-identical components.
export function OrganizationStatusBadge({ status, label }: OrganizationStatusBadgeProps) {
  return <Badge variant={STATUS_VARIANT[status]}>{label ?? STATUS_LABEL[status]}</Badge>;
}
