import type { Metadata } from "next";

import { DepartmentListContent } from "@/features/organization/components/department-list-content";

export const metadata: Metadata = { title: "Departments" };

export default function OrganizationDepartmentsPage() {
  return <DepartmentListContent />;
}
