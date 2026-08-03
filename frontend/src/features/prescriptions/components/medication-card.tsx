import { ADMINISTRATION_ROUTE_OPTIONS } from "@/lib/mock/medications";
import type { PrescriptionItem } from "@/lib/mock/prescriptions";

function getRouteLabel(route: PrescriptionItem["route"]): string {
  return ADMINISTRATION_ROUTE_OPTIONS.find((option) => option.value === route)?.label ?? route;
}

// Read-only display of one prescribed medication — the "Medication
// List" detail section's building block, one card per item, surfacing
// every field the task explicitly asks for (Dosage, Frequency,
// Duration, Route, Quantity, Instructions, Refills).
export function MedicationCard({ item }: { item: PrescriptionItem }) {
  return (
    <div className="rounded-lg border p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-semibold">
          {item.medication_name}
          {item.generic_name && item.generic_name !== item.medication_name && (
            <span className="ml-1 font-normal text-muted-foreground">({item.generic_name})</span>
          )}
        </p>
        <p className="text-sm font-medium text-muted-foreground">{item.strength}</p>
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-muted-foreground">Dosage</dt>
          <dd>
            {item.dosage} {item.dosage_unit}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Frequency</dt>
          <dd>{item.frequency}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Route</dt>
          <dd>{getRouteLabel(item.route)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Duration</dt>
          <dd>
            {item.duration} {item.duration_unit}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Quantity</dt>
          <dd>{item.quantity}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Refills</dt>
          <dd>{item.refills}</dd>
        </div>
      </dl>
      {item.instructions && (
        <div className="mt-3 border-t pt-3">
          <dt className="text-xs text-muted-foreground">Instructions</dt>
          <dd className="mt-1 text-sm">{item.instructions}</dd>
        </div>
      )}
    </div>
  );
}
