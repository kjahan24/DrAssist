"use client";

import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { ClinicalNoteForm } from "@/features/clinical-notes/components/clinical-note-form";
import { useCreateClinicalNote } from "@/features/clinical-notes/hooks/use-clinical-notes";
import type { ClinicalNoteFormInput } from "@/lib/mock/clinical-notes";

export function ClinicalNoteCreateContent() {
  const router = useRouter();
  const createNote = useCreateClinicalNote();

  function handleSubmit(values: ClinicalNoteFormInput) {
    createNote.mutate(values, {
      onSuccess: (note) => {
        router.push(`/dashboard/clinical-notes/${note.clinical_note_id}`);
      },
    });
  }

  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader title="New Clinical Note" description="Document a new clinical encounter." />
      <ClinicalNoteForm
        onSubmit={handleSubmit}
        isSubmitting={createNote.isPending}
        allowSign={false}
      />
    </div>
  );
}
