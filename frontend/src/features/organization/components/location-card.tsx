import { Clock, Mail, MapPin, Phone, Star } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { OrganizationStatusBadge } from "@/features/organization/components/organization-status-badge";
import { formatTime } from "@/lib/format";
import type { Location } from "@/lib/mock/locations";

function formatDayHours(entry: Location["operating_hours"][number]): string {
  if (!entry.open_time || !entry.close_time) return "Closed";
  return `${formatTime(entry.open_time)} – ${formatTime(entry.close_time)}`;
}

function getTodayHours(location: Location): string {
  const todayName = new Date().toLocaleDateString("en-US", { weekday: "long" });
  const today = location.operating_hours.find((entry) => entry.day === todayName);
  return today ? formatDayHours(today) : "—";
}

export function LocationCard({ location }: { location: Location }) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold">{location.facility_name}</p>
            {location.is_primary && (
              <Badge variant="outline" className="gap-1">
                <Star className="size-3" aria-hidden="true" />
                Primary
              </Badge>
            )}
          </div>
          <OrganizationStatusBadge status={location.status} />
        </div>

        <div className="space-y-1.5 text-sm text-muted-foreground">
          <p className="flex items-start gap-2">
            <MapPin className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <span>
              {location.address}, {location.city}, {location.state} {location.postal_code}
            </span>
          </p>
          <p className="flex items-center gap-2">
            <Phone className="size-4 shrink-0" aria-hidden="true" />
            {location.phone}
          </p>
          {location.email && (
            <p className="flex items-center gap-2">
              <Mail className="size-4 shrink-0" aria-hidden="true" />
              {location.email}
            </p>
          )}
        </div>

        <details className="text-sm">
          <summary className="flex cursor-pointer items-center gap-2 text-muted-foreground marker:content-none">
            <Clock className="size-4 shrink-0" aria-hidden="true" />
            <span>
              Today: <span className="text-foreground">{getTodayHours(location)}</span>
            </span>
          </summary>
          <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 pl-6 text-xs">
            {location.operating_hours.map((entry) => (
              <div key={entry.day} className="contents">
                <dt className="text-muted-foreground">{entry.day}</dt>
                <dd>{formatDayHours(entry)}</dd>
              </div>
            ))}
          </dl>
        </details>
      </CardContent>
    </Card>
  );
}
