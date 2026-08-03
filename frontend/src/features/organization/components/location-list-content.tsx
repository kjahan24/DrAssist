"use client";

import { useState } from "react";
import { MapPinned } from "lucide-react";

import { PageHeader } from "@/components/dashboard/page-header";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { LocationCard } from "@/features/organization/components/location-card";
import { OrganizationEmptyState } from "@/features/organization/components/organization-empty-state";
import { OrganizationFilters } from "@/features/organization/components/organization-filters";
import { OrganizationSearch } from "@/features/organization/components/organization-search";
import { useLocations } from "@/features/organization/hooks/use-locations";
import { useDebounce } from "@/hooks/use-debounce";
import { LOCATION_STATUS_OPTIONS, type LocationStatus } from "@/lib/mock/locations";

export function LocationListContent() {
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<LocationStatus | "all">("all");
  const debouncedSearch = useDebounce(searchInput, 300);

  const { data: locations, isLoading } = useLocations({ search: debouncedSearch, status });

  const hasAnyFilter = Boolean(debouncedSearch) || status !== "all";
  const showEmptyState = !isLoading && (locations?.length ?? 0) === 0;

  return (
    <div className="space-y-6">
      <PageHeader title="Locations" description="Facilities operated by your organization." />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <OrganizationSearch
          value={searchInput}
          onChange={setSearchInput}
          placeholder="Search by facility or city..."
        />
        <OrganizationFilters
          filters={[
            {
              label: "Status",
              value: status,
              allLabel: "All statuses",
              options: LOCATION_STATUS_OPTIONS,
              onChange: (value) => setStatus(value as LocationStatus | "all"),
            },
          ]}
        />
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <CardSkeleton key={index} />
          ))}
        </div>
      ) : showEmptyState ? (
        <OrganizationEmptyState
          icon={MapPinned}
          variant={hasAnyFilter ? "no-results" : "empty"}
          emptyTitle="No locations yet"
          emptyDescription="Facilities you add will appear here."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(locations ?? []).map((location) => (
            <LocationCard key={location.location_id} location={location} />
          ))}
        </div>
      )}
    </div>
  );
}
