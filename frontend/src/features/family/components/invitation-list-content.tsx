"use client";

import { useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import { UserPlus } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { DataTablePagination } from "@/components/shared/data-table/data-table-pagination";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { Button } from "@/components/ui/button";
import { FamilyEmptyState } from "@/features/family/components/family-empty-state";
import { FamilyFilters } from "@/features/family/components/family-filters";
import { FamilyMemberCard } from "@/features/family/components/family-member-card";
import { FamilySearch } from "@/features/family/components/family-search";
import { InvitationTable } from "@/features/family/components/invitation-table";
import { useInvitations } from "@/features/family/hooks/use-family-invitations";
import { useDebounce } from "@/hooks/use-debounce";
import type { AccessLevel, FamilyAccessStatus, Relationship } from "@/lib/mock/family-members";

const PAGE_SIZE = 10;

type SortField = "member_name" | "relationship" | "access_level" | "status" | "invited_at";

function resolveSortField(columnId: string): SortField {
  if (columnId === "recipient") return "member_name";
  if (columnId === "relationship") return "relationship";
  if (columnId === "access_level") return "access_level";
  if (columnId === "status") return "status";
  return "invited_at";
}

export function InvitationListContent() {
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<FamilyAccessStatus | "all">("all");
  const [accessLevel, setAccessLevel] = useState<AccessLevel | "all">("all");
  const [relationship, setRelationship] = useState<Relationship | "all">("all");
  const [sorting, setSorting] = useState<SortingState>([{ id: "invited_at", desc: true }]);
  const [pageIndex, setPageIndex] = useState(0);

  const debouncedSearch = useDebounce(searchInput, 300);
  const activeSort = sorting[0];

  const params = useMemo(
    () => ({
      search: debouncedSearch,
      status,
      accessLevel,
      relationship,
      sortBy: activeSort ? resolveSortField(activeSort.id) : ("invited_at" as const),
      sortDirection: activeSort?.desc ? ("desc" as const) : ("asc" as const),
      page: pageIndex + 1,
      pageSize: PAGE_SIZE,
    }),
    [debouncedSearch, status, accessLevel, relationship, activeSort, pageIndex],
  );

  const { data, isLoading, isFetching } = useInvitations(params);

  const hasAnyFilter =
    Boolean(debouncedSearch) || status !== "all" || accessLevel !== "all" || relationship !== "all";
  const showEmptyState = !isLoading && (data?.items.length ?? 0) === 0;

  function handleSortingChange(updater: SortingState | ((old: SortingState) => SortingState)) {
    setSorting((old) => (typeof updater === "function" ? updater(old) : updater));
    setPageIndex(0);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Invitation Management"
        description="Track, resend, or cancel family and caregiver invitations."
        actions={
          <Button asChild>
            <Link href="/dashboard/family/invitations/new">
              <UserPlus className="size-4" />
              New Invitation
            </Link>
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <FamilySearch
          value={searchInput}
          onChange={(value) => {
            setSearchInput(value);
            setPageIndex(0);
          }}
        />
        <FamilyFilters
          status={status}
          onStatusChange={(value) => {
            setStatus(value);
            setPageIndex(0);
          }}
          accessLevel={accessLevel}
          onAccessLevelChange={(value) => {
            setAccessLevel(value);
            setPageIndex(0);
          }}
          relationship={relationship}
          onRelationshipChange={(value) => {
            setRelationship(value);
            setPageIndex(0);
          }}
        />
      </div>

      {showEmptyState ? (
        <FamilyEmptyState variant={hasAnyFilter ? "no-results" : "empty"} />
      ) : (
        <>
          <InvitationTable
            invitations={data?.items ?? []}
            isLoading={isLoading || isFetching}
            sorting={sorting}
            onSortingChange={handleSortingChange}
          />

          <div className="grid gap-3 md:hidden">
            {isLoading
              ? Array.from({ length: 4 }).map((_, index) => <CardSkeleton key={index} />)
              : (data?.items ?? []).map((member) => (
                  <FamilyMemberCard key={member.family_access_id} member={member} />
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
