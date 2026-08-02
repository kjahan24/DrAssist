"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { LoadingButton } from "@/components/auth/loading-button";
import { FormInput } from "@/components/shared/forms/form-input";
import { FormSelect } from "@/components/shared/forms/form-select";
import { Form } from "@/components/ui/form";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DoctorCombobox } from "@/features/appointments/components/doctor-combobox";
import { PatientCombobox } from "@/features/appointments/components/patient-combobox";
import { ClinicalNoteEditor } from "@/features/clinical-notes/components/clinical-note-editor";
import { ClinicalNoteFormSection } from "@/features/clinical-notes/components/clinical-note-form-section";
import { ClinicalNotePreview } from "@/features/clinical-notes/components/clinical-note-preview";
import { VisitCombobox } from "@/features/clinical-notes/components/visit-combobox";
import { useVisit } from "@/features/visits/hooks/use-visits";
import { CLINICAL_NOTE_TYPE_OPTIONS, type ClinicalNoteFormInput } from "@/lib/mock/clinical-notes";

const clinicalNoteFormSchema = z.object({
  patient_id: z.string().min(1, "Select a patient"),
  visit_id: z.string().min(1, "Select a visit"),
  doctor_id: z.string().min(1, "Select a doctor"),
  note_type: z.enum(["initial", "follow_up", "emergency", "consultation", "discharge"]),
  encounter_datetime: z.string().min(1, "Encounter date & time is required"),
  chief_complaint_summary: z.string(),
  history_summary: z.string(),
  examination_summary: z.string(),
  assessment_summary: z.string(),
  plan_summary: z.string(),
}) satisfies z.ZodType<ClinicalNoteFormInput>;

const EMPTY_DEFAULTS: ClinicalNoteFormInput = {
  patient_id: "",
  visit_id: "",
  doctor_id: "",
  note_type: "consultation",
  encounter_datetime: "",
  chief_complaint_summary: "",
  history_summary: "",
  examination_summary: "",
  assessment_summary: "",
  plan_summary: "",
};

interface ClinicalNoteFormProps {
  defaultValues?: ClinicalNoteFormInput;
  onSubmit: (values: ClinicalNoteFormInput, action: "draft" | "sign") => void;
  isSubmitting?: boolean;
  // Only true when editing an already-draft note — see
  // `ClinicalNoteEditContent`. Creating a note always produces a Draft
  // (matching the real `CreateClinicalNoteRequest`, which has no status
  // field at all), so the Create page never offers "Save & Sign".
  allowSign?: boolean;
}

// Shared by both the New Clinical Note and Edit Clinical Note pages (per
// this module's "Edit Clinical Note: Reuse the same editor and form"
// requirement). `PatientCombobox`/`DoctorCombobox` are reused directly
// from `features/appointments/components/` — same reasoning as
// `features/visits/components/visit-form.tsx`'s identical reuse.
// Selecting a visit auto-fills patient/doctor from that visit (a
// clinical note is fundamentally "notes about this visit"), while still
// letting the user change either afterward if needed.
export function ClinicalNoteForm({
  defaultValues,
  onSubmit,
  isSubmitting,
  allowSign = false,
}: ClinicalNoteFormProps) {
  const form = useForm<ClinicalNoteFormInput>({
    resolver: zodResolver(clinicalNoteFormSchema),
    defaultValues: defaultValues ?? EMPTY_DEFAULTS,
  });

  const visitId = form.watch("visit_id");
  const { data: selectedVisit } = useVisit(visitId);

  useEffect(() => {
    if (selectedVisit) {
      form.setValue("patient_id", selectedVisit.patient_id, { shouldValidate: true });
      form.setValue("doctor_id", selectedVisit.doctor_id, { shouldValidate: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedVisit?.visit_id]);

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((values) => onSubmit(values, "draft"))}
        className="space-y-6"
        noValidate
      >
        <ClinicalNoteFormSection title="Note Details">
          <VisitCombobox control={form.control} name="visit_id" />
          <PatientCombobox control={form.control} name="patient_id" />
          <DoctorCombobox control={form.control} name="doctor_id" />
          <FormSelect
            control={form.control}
            name="note_type"
            label="Note Type"
            options={CLINICAL_NOTE_TYPE_OPTIONS}
          />
          <FormInput
            control={form.control}
            name="encounter_datetime"
            label="Encounter Date & Time"
            type="datetime-local"
          />
        </ClinicalNoteFormSection>

        <ClinicalNoteFormSection
          title="Clinical Content"
          description="Chief complaint through plan."
        >
          <div className="sm:col-span-2">
            <Tabs defaultValue="edit">
              <TabsList>
                <TabsTrigger value="edit">Edit</TabsTrigger>
                <TabsTrigger value="preview">Preview</TabsTrigger>
              </TabsList>
              <TabsContent value="edit">
                <ClinicalNoteEditor
                  control={form.control}
                  watch={form.watch}
                  setValue={form.setValue}
                />
              </TabsContent>
              <TabsContent value="preview">
                <ClinicalNotePreview
                  fields={[
                    { label: "Chief Complaint", value: form.watch("chief_complaint_summary") },
                    { label: "History of Present Illness", value: form.watch("history_summary") },
                    { label: "Examination Findings", value: form.watch("examination_summary") },
                    { label: "Assessment", value: form.watch("assessment_summary") },
                    { label: "Plan", value: form.watch("plan_summary") },
                  ]}
                />
              </TabsContent>
            </Tabs>
          </div>
        </ClinicalNoteFormSection>

        <div className="flex flex-wrap justify-end gap-3">
          <LoadingButton type="submit" variant="outline" loading={isSubmitting}>
            Save as Draft
          </LoadingButton>
          {allowSign && (
            <LoadingButton
              type="button"
              loading={isSubmitting}
              onClick={form.handleSubmit((values) => onSubmit(values, "sign"))}
            >
              Save &amp; Sign
            </LoadingButton>
          )}
        </div>
      </form>
    </Form>
  );
}
