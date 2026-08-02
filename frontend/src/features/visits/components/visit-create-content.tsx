"use client";

import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { VisitForm } from "@/features/visits/components/visit-form";
import { useCreateVisit } from "@/features/visits/hooks/use-visits";
import type { VisitFormInput } from "@/lib/mock/visits";

export function VisitCreateContent() {
  const router = useRouter();
  const createVisit = useCreateVisit();

  function handleSubmit(values: VisitFormInput) {
    createVisit.mutate(values, {
      onSuccess: (visit) => {
        router.push(`/dashboard/visits/${visit.visit_id}`);
      },
    });
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader title="New Visit" description="Record a new patient visit." />
      <VisitForm
        onSubmit={handleSubmit}
        isSubmitting={createVisit.isPending}
        submitLabel="Create Visit"
      />
    </div>
  );
}
