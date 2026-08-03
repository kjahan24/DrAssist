"use client";

import { useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import { UsersRound } from "lucide-react";

import { PageHeader } from "@/components/dashboard/page-header";
import { DataTablePagination } from "@/components/shared/data-table/data-table-pagination";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { OrganizationEmptyState } from "@/features/organization/components/organization-empty-state";
import { OrganizationFilters } from "@/features/organization/components/organization-filters";
import { OrganizationSearch } from "@/features/organization/components/organization-search";
import { OrganizationStatusBadge } from "@/features/organization/components/organization-status-badge";
import { MemberTable } from "@/features/organization/components/member-table";
import { useDepartments } from "@/features/organization/hooks/use-departments";
import { useMembers } from "@/features/organization/hooks/use-members";
import { useDebounce } from "@/hooks/use-debounce";
import {
  getMemberStatusLabel,
  MEMBER_STATUS_OPTIONS,
  type Member,
  type MemberStatus,
} from "@/lib/mock/members";

const PAGE_SIZE = 10;

type SortField = "full_name" | "role_name" | "department_name" | "status" | "last_active_at";

function resolveSortField(columnId: string): SortField {
  if (columnId === "name") return "full_name";
  if (columnId === "role_name") return "role_name";
  if (columnId === "department_name") return "department_name";
  if (columnId === "status") return "status";
  return "last_active_at";
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

const STATUS_TO_GENERIC: Record<Member["status"], "active" | "inactive"> = {
  active: "active",
  invited: "inactive",
  suspended: "inactive",
  deactivated: "inactive",
};

export function MemberListContent() {
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<MemberStatus | "all">("all");
  const [departmentId, setDepartmentId] = useState<string>("all");
  const [sorting, setSorting] = useState<SortingState>([{ id: "name", desc: false }]);
  const [pageIndex, setPageIndex] = useState(0);

  const debouncedSearch = useDebounce(searchInput, 300);
  const activeSort = sorting[0];
  const { data: departments } = useDepartments();

  const params = useMemo(
    () => ({
      search: debouncedSearch,
      status,
      departmentId,
      sortBy: activeSort ? resolveSortField(activeSort.id) : ("full_name" as const),
      sortDirection: activeSort?.desc ? ("desc" as const) : ("asc" as const),
      page: pageIndex + 1,
      pageSize: PAGE_SIZE,
    }),
    [debouncedSearch, status, departmentId, activeSort, pageIndex],
  );

  const { data, isLoading, isFetching } = useMembers(params);

  const hasAnyFilter = Boolean(debouncedSearch) || status !== "all" || departmentId !== "all";
  const showEmptyState = !isLoading && (data?.items.length ?? 0) === 0;

  function handleSortingChange(updater: SortingState | ((old: SortingState) => SortingState)) {
    setSorting((old) => (typeof updater === "function" ? updater(old) : updater));
    setPageIndex(0);
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Members" description="Everyone with access to your organization." />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <OrganizationSearch
          value={searchInput}
          onChange={(value) => {
            setSearchInput(value);
            setPageIndex(0);
          }}
          placeholder="Search by name, email, or role..."
        />
        <OrganizationFilters
          filters={[
            {
              label: "Status",
              value: status,
              allLabel: "All statuses",
              options: MEMBER_STATUS_OPTIONS,
              onChange: (value) => {
                setStatus(value as MemberStatus | "all");
                setPageIndex(0);
              },
            },
            {
              label: "Department",
              value: departmentId,
              allLabel: "All departments",
              className: "w-44",
              options: (departments ?? []).map((department) => ({
                label: department.name,
                value: department.department_id,
              })),
              onChange: (value) => {
                setDepartmentId(value);
                setPageIndex(0);
              },
            },
          ]}
        />
      </div>

      {showEmptyState ? (
        <OrganizationEmptyState
          icon={UsersRound}
          variant={hasAnyFilter ? "no-results" : "empty"}
          emptyTitle="No members yet"
          emptyDescription="Invite staff to your organization to see them here."
        />
      ) : (
        <>
          <MemberTable
            members={data?.items ?? []}
            isLoading={isLoading || isFetching}
            sorting={sorting}
            onSortingChange={handleSortingChange}
          />

          <div className="grid gap-3 md:hidden">
            {isLoading
              ? Array.from({ length: 4 }).map((_, index) => <CardSkeleton key={index} />)
              : (data?.items ?? []).map((member) => (
                  <Card key={member.member_id}>
                    <CardContent className="space-y-3 pt-6">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-3">
                          <Avatar className="size-9">
                            <AvatarFallback>{getInitials(member.full_name)}</AvatarFallback>
                          </Avatar>
                          <span className="text-sm font-medium">{member.full_name}</span>
                        </div>
                        <OrganizationStatusBadge
                          status={STATUS_TO_GENERIC[member.status]}
                          label={getMemberStatusLabel(member.status)}
                        />
                      </div>
                      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                        <div>
                          <dt className="text-xs text-muted-foreground">Role</dt>
                          <dd className="truncate">{member.role_name}</dd>
                        </div>
                        <div>
                          <dt className="text-xs text-muted-foreground">Department</dt>
                          <dd className="truncate">{member.department_name ?? "—"}</dd>
                        </div>
                        <div className="col-span-2">
                          <dt className="text-xs text-muted-foreground">Email</dt>
                          <dd className="truncate">{member.email}</dd>
                        </div>
                      </dl>
                    </CardContent>
                  </Card>
                ))}
          </div>

          <DataTablePagination
            pageIndex={pageIndex}
            pageSize={PAGE_SIZE}
            total={data?.total ?? 0}
            onPageChange={setPageIndex}
          />
        </>
      )}
    </div>
  );
}
