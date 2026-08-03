"use client";

import { useMemo, useState } from "react";
import { CheckCheck, Settings } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { PageHeader } from "@/components/dashboard/page-header";
import { DataTablePagination } from "@/components/shared/data-table/data-table-pagination";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { NotificationEmptyState } from "@/features/notifications/components/notification-empty-state";
import { NotificationFilters } from "@/features/notifications/components/notification-filters";
import { NotificationList } from "@/features/notifications/components/notification-list";
import { NotificationLoading } from "@/features/notifications/components/notification-loading";
import { NotificationSearch } from "@/features/notifications/components/notification-search";
import {
  useMarkAllNotificationsAsRead,
  useNotifications,
} from "@/features/notifications/hooks/use-notifications";
import { useDebounce } from "@/hooks/use-debounce";
import type { NotificationCategory, NotificationPriority } from "@/lib/mock/notifications";

const PAGE_SIZE = 10;

type SortOption = "created_at-desc" | "created_at-asc" | "priority-desc";

const SORT_OPTIONS: { label: string; value: SortOption }[] = [
  { label: "Newest First", value: "created_at-desc" },
  { label: "Oldest First", value: "created_at-asc" },
  { label: "Priority", value: "priority-desc" },
];

function resolveSort(option: SortOption): {
  sortBy: "created_at" | "priority";
  sortDirection: "asc" | "desc";
} {
  if (option === "created_at-asc") return { sortBy: "created_at", sortDirection: "asc" };
  if (option === "priority-desc") return { sortBy: "priority", sortDirection: "desc" };
  return { sortBy: "created_at", sortDirection: "desc" };
}

export function NotificationListContent() {
  const [searchInput, setSearchInput] = useState("");
  const [category, setCategory] = useState<NotificationCategory | "all">("all");
  const [priority, setPriority] = useState<NotificationPriority | "all">("all");
  const [readStatus, setReadStatus] = useState<"all" | "unread" | "read">("all");
  const [sort, setSort] = useState<SortOption>("created_at-desc");
  const [pageIndex, setPageIndex] = useState(0);

  const debouncedSearch = useDebounce(searchInput, 300);
  const { sortBy, sortDirection } = resolveSort(sort);
  const markAllAsRead = useMarkAllNotificationsAsRead();

  const params = useMemo(
    () => ({
      search: debouncedSearch,
      category,
      priority,
      readStatus,
      sortBy,
      sortDirection,
      page: pageIndex + 1,
      pageSize: PAGE_SIZE,
    }),
    [debouncedSearch, category, priority, readStatus, sortBy, sortDirection, pageIndex],
  );

  const { data, isLoading, isFetching } = useNotifications(params);

  const hasAnyFilter =
    Boolean(debouncedSearch) || category !== "all" || priority !== "all" || readStatus !== "all";
  const showEmptyState = !isLoading && (data?.items.length ?? 0) === 0;

  function handleMarkAllAsRead() {
    markAllAsRead.mutate(undefined, {
      onSuccess: (count) => {
        toast.success(
          count > 0
            ? `Marked ${count} notification${count === 1 ? "" : "s"} as read.`
            : "Nothing to mark as read.",
        );
      },
    });
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notifications"
        description="Stay up to date with appointments, clinical activity, and account alerts."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              onClick={handleMarkAllAsRead}
              disabled={markAllAsRead.isPending}
            >
              <CheckCheck className="size-4" />
              Mark All as Read
            </Button>
            <Button variant="outline" asChild>
              <Link href="/dashboard/notifications/settings">
                <Settings className="size-4" />
                Settings
              </Link>
            </Button>
          </div>
        }
      />

      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <NotificationSearch
            value={searchInput}
            onChange={(value) => {
              setSearchInput(value);
              setPageIndex(0);
            }}
          />
          <Select value={sort} onValueChange={(value) => setSort(value as SortOption)}>
            <SelectTrigger className="w-40" aria-label="Sort notifications">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <NotificationFilters
          category={category}
          onCategoryChange={(value) => {
            setCategory(value);
            setPageIndex(0);
          }}
          priority={priority}
          onPriorityChange={(value) => {
            setPriority(value);
            setPageIndex(0);
          }}
          readStatus={readStatus}
          onReadStatusChange={(value) => {
            setReadStatus(value);
            setPageIndex(0);
          }}
        />
      </div>

      {isLoading ? (
        <NotificationLoading />
      ) : showEmptyState ? (
        <NotificationEmptyState variant={hasAnyFilter ? "no-results" : "empty"} />
      ) : (
        <>
          <NotificationList notifications={data?.items ?? []} />
          <DataTablePagination
            pageIndex={pageIndex}
            pageSize={PAGE_SIZE}
            total={data?.total ?? 0}
            onPageChange={setPageIndex}
          />
        </>
      )}

      {isFetching && !isLoading && (
        <p className="sr-only" role="status">
          Updating notifications…
        </p>
      )}
    </div>
  );
}
