"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { LoadingButton } from "@/components/auth/loading-button";
import { FormInput } from "@/components/shared/forms/form-input";
import { FormTextarea } from "@/components/shared/forms/form-textarea";
import { Form } from "@/components/ui/form";
import { DoctorCombobox } from "@/features/appointments/components/doctor-combobox";
import { PatientCombobox } from "@/features/appointments/components/patient-combobox";
import { VisitCombobox } from "@/features/clinical-notes/components/visit-combobox";
import { useClinicalNoteByVisit } from "@/features/clinical-notes/hooks/use-clinical-notes";
import { MedicationRepeater } from "@/features/prescriptions/components/medication-repeater";
import { PrescriptionFormSection } from "@/features/prescriptions/components/prescription-form-section";
import { useVisit } from "@/features/visits/hooks/use-visits";
import type {
  PrescriptionFormInput,
  PrescriptionItemFormInput,
  PrescriptionStatus,
} from "@/lib/mock/prescriptions";

const prescriptionItemSchema = z.object({
  prescription_item_id: z.string(),
  medication_name: z.string().min(1, "Medication name is required"),
  generic_name: z.string(),
  strength: z.string(),
  dosage: z.string(),
  dosage_unit: z.string(),
  frequency: z.string(),
  route: z.enum([
    "oral",
    "iv",
    "im",
    "sc",
    "topical",
    "inhalation",
    "ophthalmic",
    "otic",
    "nasal",
    "rectal",
    "vaginal",
    "other",
  ]),
  duration: z.string(),
  duration_unit: z.string(),
  quantity: z.string(),
  instructions: z.string(),
  refills: z.string(),
}) satisfies z.ZodType<PrescriptionItemFormInput>;

const prescriptionFormSchema = z.object({
  patient_id: z.string().min(1, "Select a patient"),
  visit_id: z.string().min(1, "Select a visit"),
  doctor_id: z.string().min(1, "Select a doctor"),
  clinical_note_id: z.string().min(1, "This visit has no clinical note yet — create one first"),
  prescription_date: z.string().min(1, "Prescription date is required"),
  notes: z.string(),
  items: z.array(prescriptionItemSchema),
}) satisfies z.ZodType<PrescriptionFormInput>;

const EMPTY_DEFAULTS: PrescriptionFormInput = {
  patient_id: "",
  visit_id: "",
  doctor_id: "",
  clinical_note_id: "",
  prescription_date: "",
  notes: "",
  items: [],
};

interface PrescriptionFormProps {
  defaultValues?: PrescriptionFormInput;
  onSubmit: (values: PrescriptionFormInput, status: PrescriptionStatus) => void;
  isSubmitting?: boolean;
}

// Shared by both the New Prescription and Edit Prescription pages (per
// this module's "Edit Prescription: Reuse the same form" requirement).
// `PatientCombobox`/`DoctorCombobox`/`VisitCombobox` are reused
// directly, same pattern as `features/lab-reports/components/lab-report-form.tsx`.
// Selecting a visit auto-fills patient/doctor and auto-resolves
// `clinical_note_id` from that visit's own clinical note, mirroring the
// real `Prescription` entity, whose identity FKs are all derived from
// its parent `ClinicalNote` server-side.
export function PrescriptionForm({ defaultValues, onSubmit, isSubmitting }: PrescriptionFormProps) {
  const form = useForm<PrescriptionFormInput>({
    resolver: zodResolver(prescriptionFormSchema),
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
        <PrescriptionFormSection title="Prescription Details">
          <VisitCombobox control={form.control} name="visit_id" />
          <PatientCombobox control={form.control} name="patient_id" />
          <DoctorCombobox control={form.control} name="doctor_id" />
          <FormInput
            control={form.control}
            name="prescription_date"
            label="Prescription Date"
            type="date"
          />
          <div className="sm:col-span-2">
            {visitId && !isLoadingClinicalNote && !linkedClinicalNote && (
              <p className="text-[0.8rem] text-destructive">
                This visit has no clinical note yet — a prescription can only be attached to an
                existing clinical note. Create one first.
              </p>
            )}
            {linkedClinicalNote && (
              <p className="text-[0.8rem] text-muted-foreground">
                Linked to Clinical Note {linkedClinicalNote.note_number}.
              </p>
            )}
          </div>
        </PrescriptionFormSection>

        <MedicationRepeater control={form.control} setValue={form.setValue} />

        <PrescriptionFormSection title="Notes">
          <div className="sm:col-span-2">
            <FormTextarea control={form.control} name="notes" label="Notes" rows={3} />
          </div>
        </PrescriptionFormSection>

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
