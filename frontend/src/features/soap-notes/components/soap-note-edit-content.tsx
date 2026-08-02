"use client";

import { AlertTriangle, Lock } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { SoapNoteForm } from "@/features/soap-notes/components/soap-note-form";
import { useSoapNote, useUpdateSoapNote } from "@/features/soap-notes/hooks/use-soap-notes";
import {
  getSoapNoteStatusLabel,
  isSoapNoteEditable,
  soapNoteToFormInput,
  type SOAPNoteFormInput,
  type SOAPNoteStatus,
} from "@/lib/mock/soap-notes";

export function SoapNoteEditContent({ soapNoteId }: { soapNoteId: string }) {
  const router = useRouter();
  const { data: note, isLoading } = useSoapNote(soapNoteId);
  const updateNote = useUpdateSoapNote(soapNoteId);

  if (isLoading) {
    return <PageSkeleton title="Edit SOAP Note" />;
  }

  if (!note) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="SOAP note not found"
        description="This note may have been removed, or the link is incorrect."
      />
    );
  }

  // A "Final" SOAP note is treated as immutable, mirroring the real
  // parent-status-gated editability of the actual `SOAPNote` entity —
  // see `lib/mock/soap-notes.ts`'s docstring.
  if (!isSoapNoteEditable(note.status)) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Edit SOAP Note"
          description={`${note.soap_number} is no longer editable.`}
        />
        <EmptyState
          icon={Lock}
          title={`This note is ${getSoapNoteStatusLabel(note.status).toLowerCase()}`}
          description="Final SOAP notes cannot be edited, matching the real clinical documentation workflow."
          action={
            <Button variant="outline" asChild>
              <Link href={`/dashboard/soap-notes/${soapNoteId}`}>View Note</Link>
            </Button>
          }
        />
      </div>
    );
  }

  function handleSubmit(values: SOAPNoteFormInput, status: SOAPNoteStatus) {
    updateNote.mutate(
      { input: values, status },
      {
        onSuccess: () => {
          router.push(`/dashboard/soap-notes/${soapNoteId}`);
        },
      },
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader
        title="Edit SOAP Note"
        description={`Update ${note.soap_number} for ${note.patient_name}.`}
      />
      <SoapNoteForm
        defaultValues={soapNoteToFormInput(note)}
        onSubmit={handleSubmit}
        isSubmitting={updateNote.isPending}
      />
    </div>
  );
}
