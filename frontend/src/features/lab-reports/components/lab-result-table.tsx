import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getAbnormalFlagLabel, type AbnormalFlag, type LabTestItem } from "@/lib/mock/lab-reports";

const FLAG_VARIANT: Record<AbnormalFlag, "default" | "secondary" | "destructive" | "outline"> = {
  normal: "secondary",
  low: "outline",
  high: "outline",
  abnormal: "outline",
  critical: "destructive",
};

// A compact tabular view of every test item's result — the "Test
// Results" section's building block. Deliberately built on the plain
// `Table` primitives (not the shared `DataTable`) since this renders a
// small, fixed, in-memory list scoped to one report, not a
// paginated/remote dataset.
export function LabResultTable({ items }: { items: LabTestItem[] }) {
  return (
    <div className="overflow-x-auto rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Test</TableHead>
            <TableHead>Result</TableHead>
            <TableHead>Unit</TableHead>
            <TableHead>Flag</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.item_id}>
              <TableCell className="font-medium">{item.test_name}</TableCell>
              <TableCell>{item.result_value || "—"}</TableCell>
              <TableCell>{item.result_unit || "—"}</TableCell>
              <TableCell>
                <Badge variant={FLAG_VARIANT[item.abnormal_flag]}>
                  {getAbnormalFlagLabel(item.abnormal_flag)}
                </Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
