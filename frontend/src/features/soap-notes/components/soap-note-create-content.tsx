"use client";

import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { SoapNoteForm } from "@/features/soap-notes/components/soap-note-form";
import { useCreateSoapNote } from "@/features/soap-notes/hooks/use-soap-notes";
import type { SOAPNoteFormInput, SOAPNoteStatus } from "@/lib/mock/soap-notes";

export function SoapNoteCreateContent() {
  const router = useRouter();
  const createNote = useCreateSoapNote();

  function handleSubmit(values: SOAPNoteFormInput, status: SOAPNoteStatus) {
    createNote.mutate(
      { input: values, status },
      {
        onSuccess: (note) => {
          router.push(`/dashboard/soap-notes/${note.soap_note_id}`);
        },
      },
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader
        title="New SOAP Note"
        description="Document a new structured clinical encounter."
      />
      <SoapNoteForm onSubmit={handleSubmit} isSubmitting={createNote.isPending} />
    </div>
  );
}
