"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { LoadingButton } from "@/components/auth/loading-button";
import { Form } from "@/components/ui/form";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DoctorCombobox } from "@/features/appointments/components/doctor-combobox";
import { PatientCombobox } from "@/features/appointments/components/patient-combobox";
import { useClinicalNoteByVisit } from "@/features/clinical-notes/hooks/use-clinical-notes";
import { VisitCombobox } from "@/features/clinical-notes/components/visit-combobox";
import { SoapNoteEditor } from "@/features/soap-notes/components/soap-note-editor";
import { SoapNoteFormSection } from "@/features/soap-notes/components/soap-note-form-section";
import { SoapNotePreview } from "@/features/soap-notes/components/soap-note-preview";
import { useVisit } from "@/features/visits/hooks/use-visits";
import type { SOAPNoteFormInput, SOAPNoteStatus } from "@/lib/mock/soap-notes";

const soapNoteFormSchema = z.object({
  patient_id: z.string().min(1, "Select a patient"),
  visit_id: z.string().min(1, "Select a visit"),
  doctor_id: z.string().min(1, "Select a doctor"),
  clinical_note_id: z.string().min(1, "This visit has no clinical note yet — create one first"),
  subjective: z.string(),
  objective: z.string(),
  assessment: z.string(),
  plan: z.string(),
}) satisfies z.ZodType<SOAPNoteFormInput>;

const EMPTY_DEFAULTS: SOAPNoteFormInput = {
  patient_id: "",
  visit_id: "",
  doctor_id: "",
  clinical_note_id: "",
  subjective: "",
  objective: "",
  assessment: "",
  plan: "",
};

interface SoapNoteFormProps {
  defaultValues?: SOAPNoteFormInput;
  onSubmit: (values: SOAPNoteFormInput, status: SOAPNoteStatus) => void;
  isSubmitting?: boolean;
}

// Shared by both the New SOAP Note and Edit SOAP Note pages (per this
// module's "Edit SOAP Note: Reuse the same editor and form"
// requirement). `PatientCombobox`/`DoctorCombobox`
// (`features/appointments/components/`) and `VisitCombobox`
// (`features/clinical-notes/components/`) are reused directly — all
// three are generic, business-logic-free selectors already built for
// earlier modules. Selecting a visit auto-fills patient/doctor from it
// (same pattern as `features/clinical-notes/components/clinical-note-form.tsx`)
// and additionally auto-resolves `clinical_note_id` from that visit's
// own clinical note — mirroring the real `SOAPNote` entity, whose
// identity FKs are all derived from its parent `ClinicalNote`
// server-side, never independently supplied (see
// `lib/mock/soap-notes.ts`'s docstring).
export function SoapNoteForm({ defaultValues, onSubmit, isSubmitting }: SoapNoteFormProps) {
  const form = useForm<SOAPNoteFormInput>({
    resolver: zodResolver(soapNoteFormSchema),
    defaultValues: defaultValues ?? EMPTY_DEFAULTS,
  });

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

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((values) => onSubmit(values, "draft"))}
        className="space-y-6"
        noValidate
      >
        <SoapNoteFormSection title="Note Details">
          <VisitCombobox control={form.control} name="visit_id" />
          <PatientCombobox control={form.control} name="patient_id" />
          <DoctorCombobox control={form.control} name="doctor_id" />
          <div className="sm:col-span-2">
            {visitId && !isLoadingClinicalNote && !linkedClinicalNote && (
              <p className="text-[0.8rem] text-destructive">
                This visit has no clinical note yet — a SOAP note can only be attached to an
                existing clinical note. Create one first.
              </p>
            )}
            {linkedClinicalNote && (
              <p className="text-[0.8rem] text-muted-foreground">
                Linked to Clinical Note {linkedClinicalNote.note_number}.
              </p>
            )}
          </div>
        </SoapNoteFormSection>

        <SoapNoteFormSection title="Clinical Content" description="Subjective through plan.">
          <div className="sm:col-span-2">
            <Tabs defaultValue="edit">
              <TabsList>
                <TabsTrigger value="edit">Edit</TabsTrigger>
                <TabsTrigger value="preview">Preview</TabsTrigger>
              </TabsList>
              <TabsContent value="edit">
                <SoapNoteEditor control={form.control} watch={form.watch} />
              </TabsContent>
              <TabsContent value="preview">
                <SoapNotePreview
                  fields={[
                    { label: "Subjective", value: form.watch("subjective") },
                    { label: "Objective", value: form.watch("objective") },
                    { label: "Assessment", value: form.watch("assessment") },
                    { label: "Plan", value: form.watch("plan") },
                  ]}
                />
              </TabsContent>
            </Tabs>
          </div>
        </SoapNoteFormSection>

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
