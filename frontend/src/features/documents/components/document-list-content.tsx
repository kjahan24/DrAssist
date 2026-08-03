"use client";

import { useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import { LayoutGrid, List, Upload } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { DataTablePagination } from "@/components/shared/data-table/data-table-pagination";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DocumentCard } from "@/features/documents/components/document-card";
import { DocumentEmptyState } from "@/features/documents/components/document-empty-state";
import { DocumentFilters } from "@/features/documents/components/document-filters";
import { DocumentGrid } from "@/features/documents/components/document-grid";
import { DocumentSearch } from "@/features/documents/components/document-search";
import { DocumentTable } from "@/features/documents/components/document-table";
import { useDocuments } from "@/features/documents/hooks/use-documents";
import { useDebounce } from "@/hooks/use-debounce";
import type { DocumentCategory, DocumentStatus } from "@/lib/mock/documents";

const PAGE_SIZE = 12;

type SortField =
  "title" | "category" | "status" | "uploaded_at" | "patient_name" | "file_size_bytes";

function resolveSortField(columnId: string): SortField {
  if (columnId === "patient") return "patient_name";
  if (columnId === "category") return "category";
  if (columnId === "status") return "status";
  if (columnId === "file_size") return "file_size_bytes";
  if (columnId === "uploaded_at") return "uploaded_at";
  return "title";
}

export function DocumentListContent() {
  const [view, setView] = useState<"list" | "grid">("list");
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<DocumentStatus | "all">("all");
  const [category, setCategory] = useState<DocumentCategory | "all">("all");
  const [sorting, setSorting] = useState<SortingState>([{ id: "uploaded_at", desc: true }]);
  const [pageIndex, setPageIndex] = useState(0);

  const debouncedSearch = useDebounce(searchInput, 300);
  const activeSort = sorting[0];

  const params = useMemo(
    () => ({
      search: debouncedSearch,
      status,
      category,
      sortBy: activeSort ? resolveSortField(activeSort.id) : ("uploaded_at" as const),
      sortDirection: activeSort?.desc ? ("desc" as const) : ("asc" as const),
      page: pageIndex + 1,
      pageSize: PAGE_SIZE,
    }),
    [debouncedSearch, status, category, activeSort, pageIndex],
  );

  const { data, isLoading, isFetching } = useDocuments(params);

  const hasAnyFilter = Boolean(debouncedSearch) || status !== "all" || category !== "all";
  const showEmptyState = !isLoading && (data?.items.length ?? 0) === 0;

  function handleSortingChange(updater: SortingState | ((old: SortingState) => SortingState)) {
    setSorting((old) => (typeof updater === "function" ? updater(old) : updater));
    setPageIndex(0);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Documents"
        description="Manage patient medical documents and files."
        actions={
          <Button asChild>
            <Link href="/dashboard/documents/upload">
              <Upload className="size-4" />
              Upload Document
            </Link>
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <DocumentSearch
          value={searchInput}
          onChange={(value) => {
            setSearchInput(value);
            setPageIndex(0);
          }}
        />
        <div className="flex flex-wrap items-center gap-2">
          <DocumentFilters
            status={status}
            onStatusChange={(value) => {
              setStatus(value);
              setPageIndex(0);
            }}
            category={category}
            onCategoryChange={(value) => {
              setCategory(value);
              setPageIndex(0);
            }}
          />
          <Tabs value={view} onValueChange={(value) => setView(value as "list" | "grid")}>
            <TabsList>
              <TabsTrigger value="list" aria-label="List view">
                <List className="size-4" />
                <span className="hidden sm:inline">List</span>
              </TabsTrigger>
              <TabsTrigger value="grid" aria-label="Grid view">
                <LayoutGrid className="size-4" />
                <span className="hidden sm:inline">Grid</span>
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      {showEmptyState ? (
        <DocumentEmptyState variant={hasAnyFilter ? "no-results" : "empty"} />
      ) : view === "grid" ? (
        <>
          <DocumentGrid documents={data?.items ?? []} isLoading={isLoading || isFetching} />
          <DataTablePagination
            pageIndex={pageIndex}
            pageSize={PAGE_SIZE}
            total={data?.total ?? 0}
            onPageChange={setPageIndex}
          />
        </>
      ) : (
        <>
          <DocumentTable
            documents={data?.items ?? []}
            isLoading={isLoading || isFetching}
            sorting={sorting}
            onSortingChange={handleSortingChange}
          />

          <div className="grid gap-3 md:hidden">
            {isLoading
              ? Array.from({ length: 4 }).map((_, index) => <CardSkeleton key={index} />)
              : (data?.items ?? []).map((document) => (
                  <DocumentCard key={document.document_id} document={document} />
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
