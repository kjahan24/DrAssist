"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus } from "lucide-react";
import { useEffect } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { z } from "zod";

import { LoadingButton } from "@/components/auth/loading-button";
import { FormSelect } from "@/components/shared/forms/form-select";
import { FormTextarea } from "@/components/shared/forms/form-textarea";
import { Button } from "@/components/ui/button";
import { Form } from "@/components/ui/form";
import { DoctorCombobox } from "@/features/appointments/components/doctor-combobox";
import { PatientCombobox } from "@/features/appointments/components/patient-combobox";
import { VisitCombobox } from "@/features/clinical-notes/components/visit-combobox";
import { useClinicalNoteByVisit } from "@/features/clinical-notes/hooks/use-clinical-notes";
import { LabReportFormSection } from "@/features/lab-reports/components/lab-report-form-section";
import { LabTestItemEditor } from "@/features/lab-reports/components/lab-test-item-editor";
import { useVisit } from "@/features/visits/hooks/use-visits";
import {
  LAB_PRIORITY_OPTIONS,
  LAB_REPORT_CATEGORY_OPTIONS,
  type LabReportFormInput,
  type LabTestItem,
} from "@/lib/mock/lab-reports";

function generateItemId(): string {
  return `item-${Math.random().toString(36).slice(2, 10)}`;
}

const labTestItemSchema = z.object({
  item_id: z.string(),
  test_code: z.string(),
  test_name: z.string().min(1, "Test name is required"),
  specimen_type: z.string(),
  result_value: z.string(),
  result_unit: z.string(),
  reference_range: z.string(),
  abnormal_flag: z.enum(["normal", "low", "high", "critical", "abnormal"]),
  interpretation: z.string().nullable(),
}) satisfies z.ZodType<LabTestItem>;

const labReportFormSchema = z.object({
  patient_id: z.string().min(1, "Select a patient"),
  visit_id: z.string().min(1, "Select a visit"),
  doctor_id: z.string().min(1, "Select a doctor"),
  clinical_note_id: z.string().min(1, "This visit has no clinical note yet — create one first"),
  category: z.enum([
    "hematology",
    "chemistry",
    "microbiology",
    "immunology",
    "urinalysis",
    "pathology",
    "radiology",
    "other",
  ]),
  priority: z.enum(["routine", "urgent", "stat"]),
  clinical_information: z.string(),
  interpretation: z.string(),
  items: z.array(labTestItemSchema),
}) satisfies z.ZodType<LabReportFormInput>;

const EMPTY_DEFAULTS: LabReportFormInput = {
  patient_id: "",
  visit_id: "",
  doctor_id: "",
  clinical_note_id: "",
  category: "chemistry",
  priority: "routine",
  clinical_information: "",
  interpretation: "",
  items: [],
};

interface LabReportFormProps {
  defaultValues?: LabReportFormInput;
  onSubmit: (values: LabReportFormInput, status: "draft" | "final") => void;
  isSubmitting?: boolean;
}

// Shared by both the New Lab Report and Edit Lab Report pages (per this
// module's "Edit Lab Report: Reuse the same form" requirement).
// `PatientCombobox`/`DoctorCombobox` (`features/appointments/components/`)
// and `VisitCombobox` (`features/clinical-notes/components/`) are
// reused directly, same pattern as
// `features/soap-notes/components/soap-note-form.tsx`. Selecting a
// visit auto-fills patient/doctor and auto-resolves `clinical_note_id`
// from that visit's own clinical note, mirroring the real `LabOrder`
// entity, whose identity FKs are all derived from its parent
// `ClinicalNote` server-side.
export function LabReportForm({ defaultValues, onSubmit, isSubmitting }: LabReportFormProps) {
  const form = useForm<LabReportFormInput>({
    resolver: zodResolver(labReportFormSchema),
    defaultValues: defaultValues ?? EMPTY_DEFAULTS,
  });
  const { fields, append, remove } = useFieldArray({ control: form.control, name: "items" });

  const visitId = form.watch("visit_id");
  const { data: selectedVisit } = useVisit(visitId);
  const { data: linkedClinicalNote, isLoading: isLoadingClinicalNote } =
    useClinicalNoteByVisit(visitId);

  useEffect(() => {
    if (selectedVisit) {
      form.setValue("patient_id", selectedVisit.patient_id, { shouldValidate: true });
      form.setValue("doctor_id", selectedVisit.doctor_id, { shouldValidate: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedVisit?.visit_id]);

  useEffect(() => {
    form.setValue("clinical_note_id", linkedClinicalNote?.clinical_note_id ?? "", {
      shouldValidate: true,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visitId, linkedClinicalNote?.clinical_note_id]);

  function handleAddTest() {
    append({
      item_id: generateItemId(),
      test_code: "",
      test_name: "",
      specimen_type: "",
      result_value: "",
      result_unit: "",
      reference_range: "",
      abnormal_flag: "normal",
      interpretation: null,
    });
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((values) => onSubmit(values, "draft"))}
        className="space-y-6"
        noValidate
      >
        <LabReportFormSection title="Report Details">
          <VisitCombobox control={form.control} name="visit_id" />
          <PatientCombobox control={form.control} name="patient_id" />
          <DoctorCombobox control={form.control} name="doctor_id" />
          <FormSelect
            control={form.control}
            name="category"
            label="Report Category"
            options={LAB_REPORT_CATEGORY_OPTIONS}
          />
          <FormSelect
            control={form.control}
            name="priority"
            label="Priority"
            options={[...LAB_PRIORITY_OPTIONS]}
          />
          <div className="sm:col-span-2">
            {visitId && !isLoadingClinicalNote && !linkedClinicalNote && (
              <p className="text-[0.8rem] text-destructive">
                This visit has no clinical note yet — a lab report can only be attached to an
                existing clinical note. Create one first.
              </p>
            )}
            {linkedClinicalNote && (
              <p className="text-[0.8rem] text-muted-foreground">
                Linked to Clinical Note {linkedClinicalNote.note_number}.
              </p>
            )}
          </div>
        </LabReportFormSection>

        <LabReportFormSection title="Clinical Information">
          <div className="sm:col-span-2">
            <FormTextarea
              control={form.control}
              name="clinical_information"
              label="Clinical Information"
              rows={2}
            />
          </div>
          <div className="sm:col-span-2">
            <FormTextarea
              control={form.control}
              name="interpretation"
              label="Interpretation"
              rows={3}
            />
          </div>
        </LabReportFormSection>

        <fieldset className="space-y-4 rounded-lg border p-4 sm:p-6">
          <legend className="px-1 text-sm font-semibold">Test List</legend>
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm text-muted-foreground">Add one row per test in this panel.</p>
            <Button type="button" variant="outline" size="sm" onClick={handleAddTest}>
              <Plus className="size-4" />
              Add Test
            </Button>
          </div>
          {fields.length === 0 ? (
            <p className="text-sm text-muted-foreground">No tests added yet.</p>
          ) : (
            <div className="space-y-4">
              {fields.map((field, index) => (
                <LabTestItemEditor
                  key={field.id}
                  control={form.control}
                  index={index}
                  onRemove={() => remove(index)}
                />
              ))}
            </div>
          )}
        </fieldset>

        <div className="flex flex-wrap justify-end gap-3">
          <LoadingButton type="submit" variant="outline" loading={isSubmitting}>
            Save as Draft
          </LoadingButton>
          <LoadingButton
            type="button"
            loading={isSubmitting}
            onClick={form.handleSubmit((values) => onSubmit(values, "final"))}
          >
            Save as Final
          </LoadingButton>
        </div>
      </form>
    </Form>
  );
}
