"use client";

import { Plus, Trash2 } from "lucide-react";
import type { Control, UseFormSetValue } from "react-hook-form";
import { useFieldArray } from "react-hook-form";

import { FormInput } from "@/components/shared/forms/form-input";
import { FormSelect } from "@/components/shared/forms/form-select";
import { FormTextarea } from "@/components/shared/forms/form-textarea";
import { Button } from "@/components/ui/button";
import { MedicationSelector } from "@/features/prescriptions/components/medication-selector";
import { ADMINISTRATION_ROUTE_OPTIONS, type MedicationCatalogEntry } from "@/lib/mock/medications";
import type { PrescriptionFormInput } from "@/lib/mock/prescriptions";

function generateItemId(): string {
  return `rxitem-${Math.random().toString(36).slice(2, 10)}`;
}

function emptyItem(): PrescriptionFormInput["items"][number] {
  return {
    prescription_item_id: generateItemId(),
    medication_name: "",
    generic_name: "",
    strength: "",
    dosage: "",
    dosage_unit: "",
    frequency: "",
    route: "oral",
    duration: "",
    duration_unit: "",
    quantity: "",
    instructions: "",
    refills: "0",
  };
}

interface MedicationRepeaterProps {
  control: Control<PrescriptionFormInput>;
  setValue: UseFormSetValue<PrescriptionFormInput>;
}

// The dynamic "Medication repeater" this module's Create form asks
// for — add/remove rows via `useFieldArray`, each row a full editable
// set of fields (Medication Name, Strength, Dosage, Route, Frequency,
// Duration, Quantity, Instructions, Refills) plus a `MedicationSelector`
// that can autofill several of them at once from the mock catalog.
export function MedicationRepeater({ control, setValue }: MedicationRepeaterProps) {
  const { fields, append, remove } = useFieldArray({ control, name: "items" });

  function handleSelectMedication(index: number, medication: MedicationCatalogEntry) {
    setValue(`items.${index}.medication_name`, medication.medication_name, { shouldDirty: true });
    setValue(`items.${index}.generic_name`, medication.generic_name ?? "", { shouldDirty: true });
    setValue(`items.${index}.strength`, medication.common_strengths[0] ?? "", {
      shouldDirty: true,
    });
    setValue(`items.${index}.route`, medication.default_route, { shouldDirty: true });
    setValue(`items.${index}.dosage_unit`, medication.default_dosage_unit, { shouldDirty: true });
    setValue(`items.${index}.frequency`, medication.default_frequency, { shouldDirty: true });
  }

  return (
    <fieldset className="space-y-4 rounded-lg border p-4 sm:p-6">
      <legend className="px-1 text-sm font-semibold">Medications</legend>
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">Add one row per prescribed medication.</p>
        <Button type="button" variant="outline" size="sm" onClick={() => append(emptyItem())}>
          <Plus className="size-4" />
          Add Medication
        </Button>
      </div>
      {fields.length === 0 ? (
        <p className="text-sm text-muted-foreground">No medications added yet.</p>
      ) : (
        <div className="space-y-4">
          {fields.map((field, index) => (
            <div key={field.id} className="space-y-4 rounded-lg border p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold">Medication {index + 1}</p>
                <div className="flex items-center gap-2">
                  <MedicationSelector
                    onSelect={(medication) => handleSelectMedication(index, medication)}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="size-8 text-destructive hover:text-destructive"
                    aria-label={`Remove medication ${index + 1}`}
                    onClick={() => remove(index)}
                  >
                    <Trash2 className="size-4" aria-hidden="true" />
                  </Button>
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormInput
                  control={control}
                  name={`items.${index}.medication_name`}
                  label="Medication Name"
                />
                <FormInput
                  control={control}
                  name={`items.${index}.generic_name`}
                  label="Generic Name"
                />
                <FormInput
                  control={control}
                  name={`items.${index}.strength`}
                  label="Strength"
                  placeholder="e.g. 10 mg"
                />
                <FormSelect
                  control={control}
                  name={`items.${index}.route`}
                  label="Route"
                  options={[...ADMINISTRATION_ROUTE_OPTIONS]}
                />
                <FormInput
                  control={control}
                  name={`items.${index}.dosage`}
                  label="Dosage"
                  placeholder="e.g. 1 tablet"
                />
                <FormInput
                  control={control}
                  name={`items.${index}.dosage_unit`}
                  label="Dosage Unit"
                  placeholder="e.g. tablet"
                />
                <FormInput
                  control={control}
                  name={`items.${index}.frequency`}
                  label="Frequency"
                  placeholder="e.g. Once daily"
                />
                <div className="grid grid-cols-2 gap-4">
                  <FormInput
                    control={control}
                    name={`items.${index}.duration`}
                    label="Duration"
                    placeholder="e.g. 30"
                  />
                  <FormInput
                    control={control}
                    name={`items.${index}.duration_unit`}
                    label="Duration Unit"
                    placeholder="e.g. days"
                  />
                </div>
                <FormInput control={control} name={`items.${index}.quantity`} label="Quantity" />
                <FormInput
                  control={control}
                  name={`items.${index}.refills`}
                  label="Refills"
                  type="number"
                />
                <div className="sm:col-span-2">
                  <FormTextarea
                    control={control}
                    name={`items.${index}.instructions`}
                    label="Instructions"
                    rows={2}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </fieldset>
  );
}
