import { cn } from "@/lib/utils";
import { getAbnormalFlagLabel, type LabTestItem } from "@/lib/mock/lab-reports";

const FLAG_TEXT_CLASS: Record<LabTestItem["abnormal_flag"], string> = {
  normal: "text-muted-foreground",
  low: "text-amber-600 dark:text-amber-400",
  high: "text-amber-600 dark:text-amber-400",
  abnormal: "text-amber-600 dark:text-amber-400",
  critical: "text-destructive",
};

// A per-test visual range comparison — the "Reference Ranges" section's
// building block, one card per test item. Distinct from `LabResultTable`
// by design: that's a compact tabular scan of every result at once,
// this focuses on the single clinical question "is this result within
// range" for one test at a time, which reads more clearly as a card
// than as another table column.
export function ReferenceRangeCard({ item }: { item: LabTestItem }) {
  return (
    <div className="rounded-lg border p-4">
      <p className="text-sm font-medium">{item.test_name}</p>
      <p className={cn("mt-1 text-lg font-semibold", FLAG_TEXT_CLASS[item.abnormal_flag])}>
        {item.result_value || "—"}
        {item.result_unit && <span className="ml-1 text-sm font-normal">{item.result_unit}</span>}
      </p>
      <dl className="mt-2 space-y-1 text-xs text-muted-foreground">
        <div className="flex justify-between gap-2">
          <dt>Reference range</dt>
          <dd>{item.reference_range || "Not specified"}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt>Flag</dt>
          <dd>{getAbnormalFlagLabel(item.abnormal_flag)}</dd>
        </div>
      </dl>
    </div>
  );
}
