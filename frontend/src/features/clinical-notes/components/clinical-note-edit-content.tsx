"use client";

import { AlertTriangle, Lock } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { ClinicalNoteForm } from "@/features/clinical-notes/components/clinical-note-form";
import {
  useClinicalNote,
  useUpdateClinicalNote,
} from "@/features/clinical-notes/hooks/use-clinical-notes";
import {
  clinicalNoteToFormInput,
  getClinicalNoteStatusLabel,
  isClinicalNoteEditable,
  type ClinicalNoteFormInput,
} from "@/lib/mock/clinical-notes";

export function ClinicalNoteEditContent({ clinicalNoteId }: { clinicalNoteId: string }) {
  const router = useRouter();
  const { data: note, isLoading } = useClinicalNote(clinicalNoteId);
  const updateNote = useUpdateClinicalNote(clinicalNoteId);

  if (isLoading) {
    return <PageSkeleton title="Edit Clinical Note" />;
  }

  if (!note) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Clinical note not found"
        description="This note may have been removed, or the link is incorrect."
      />
    );
  }

  // Mirrors the real backend's own guard (`ClinicalNote._ensure_editable()`
  // — only a Draft note can have its content modified). Rather than
  // letting the user fill out a form the real API would reject, this
  // shows a clear, non-interactive message instead.
  if (!isClinicalNoteEditable(note.status)) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Edit Clinical Note"
          description={`${note.note_number} is no longer editable.`}
        />
        <EmptyState
          icon={Lock}
          title={`This note is ${getClinicalNoteStatusLabel(note.status).toLowerCase()}`}
          description="Signed and locked notes cannot be edited, matching the real clinical documentation workflow."
          action={
            <Button variant="outline" asChild>
              <Link href={`/dashboard/clinical-notes/${clinicalNoteId}`}>View Note</Link>
            </Button>
          }
        />
      </div>
    );
  }

  function handleSubmit(values: ClinicalNoteFormInput, action: "draft" | "sign") {
    updateNote.mutate(
      { input: values, action },
      {
        onSuccess: () => {
          router.push(`/dashboard/clinical-notes/${clinicalNoteId}`);
        },
      },
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader
        title="Edit Clinical Note"
        description={`Update ${note.note_number} for ${note.patient_name}.`}
      />
      <ClinicalNoteForm
        defaultValues={clinicalNoteToFormInput(note)}
        onSubmit={handleSubmit}
        isSubmitting={updateNote.isPending}
        allowSign
      />
    </div>
  );
}
