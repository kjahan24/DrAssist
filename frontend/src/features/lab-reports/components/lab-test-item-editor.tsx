"use client";

import { Trash2 } from "lucide-react";
import type { Control } from "react-hook-form";

import { FormInput } from "@/components/shared/forms/form-input";
import { FormSelect } from "@/components/shared/forms/form-select";
import { Button } from "@/components/ui/button";
import { ABNORMAL_FLAG_OPTIONS, type LabReportFormInput } from "@/lib/mock/lab-reports";

interface LabTestItemEditorProps {
  control: Control<LabReportFormInput>;
  index: number;
  onRemove: () => void;
}

// One row of the dynamic "Test list" — combines what the real backend
// splits across two aggregates (`LabOrderItem`'s test_name/test_code/
// specimen_type and `LabResultItem`'s result_value/result_unit/
// reference_range/abnormal_flag) into one editable card, since this
// module's Create form asks for one unified "Test list" + "Result
// editor" + "Reference range editor" per test — see
// `lib/mock/lab-reports.ts`'s docstring for the full reasoning.
export function LabTestItemEditor({ control, index, onRemove }: LabTestItemEditorProps) {
  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">Test {index + 1}</p>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-8 text-destructive hover:text-destructive"
          aria-label={`Remove test ${index + 1}`}
          onClick={onRemove}
        >
          <Trash2 className="size-4" aria-hidden="true" />
        </Button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormInput control={control} name={`items.${index}.test_name`} label="Test Name" />
        <FormInput control={control} name={`items.${index}.test_code`} label="Test Code" />
        <FormInput control={control} name={`items.${index}.specimen_type`} label="Specimen Type" />
        <FormSelect
          control={control}
          name={`items.${index}.abnormal_flag`}
          label="Flag"
          options={[...ABNORMAL_FLAG_OPTIONS]}
        />
        <FormInput control={control} name={`items.${index}.result_value`} label="Result Value" />
        <FormInput control={control} name={`items.${index}.result_unit`} label="Unit" />
        <div className="sm:col-span-2">
          <FormInput
            control={control}
            name={`items.${index}.reference_range`}
            label="Reference Range"
            placeholder="e.g. 70-100 mg/dL"
          />
        </div>
      </div>
    </div>
  );
}
