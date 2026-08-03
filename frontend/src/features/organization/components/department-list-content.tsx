"use client";

import { useState } from "react";
import { Building } from "lucide-react";

import { PageHeader } from "@/components/dashboard/page-header";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { DepartmentCard } from "@/features/organization/components/department-card";
import { OrganizationEmptyState } from "@/features/organization/components/organization-empty-state";
import { OrganizationFilters } from "@/features/organization/components/organization-filters";
import { OrganizationSearch } from "@/features/organization/components/organization-search";
import { useDepartments } from "@/features/organization/hooks/use-departments";
import { useDebounce } from "@/hooks/use-debounce";
import { DEPARTMENT_STATUS_OPTIONS, type DepartmentStatus } from "@/lib/mock/departments";

export function DepartmentListContent() {
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<DepartmentStatus | "all">("all");
  const debouncedSearch = useDebounce(searchInput, 300);

  const { data: departments, isLoading } = useDepartments({ search: debouncedSearch, status });

  const hasAnyFilter = Boolean(debouncedSearch) || status !== "all";
  const showEmptyState = !isLoading && (departments?.length ?? 0) === 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Departments"
        description="Clinical and administrative departments in your organization."
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <OrganizationSearch
          value={searchInput}
          onChange={setSearchInput}
          placeholder="Search by department or head..."
        />
        <OrganizationFilters
          filters={[
            {
              label: "Status",
              value: status,
              allLabel: "All statuses",
              options: DEPARTMENT_STATUS_OPTIONS,
              onChange: (value) => setStatus(value as DepartmentStatus | "all"),
            },
          ]}
        />
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <CardSkeleton key={index} />
          ))}
        </div>
      ) : showEmptyState ? (
        <OrganizationEmptyState
          icon={Building}
          variant={hasAnyFilter ? "no-results" : "empty"}
          emptyTitle="No departments yet"
          emptyDescription="Departments you create will appear here."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(departments ?? []).map((department) => (
            <DepartmentCard key={department.department_id} department={department} />
          ))}
        </div>
      )}
    </div>
  );
}
