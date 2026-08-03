import type { Metadata } from "next";

import { LocationListContent } from "@/features/organization/components/location-list-content";

export const metadata: Metadata = { title: "Locations" };

export default function OrganizationLocationsPage() {
  return <LocationListContent />;
}
