"use client";

import { AlertTriangle } from "lucide-react";
import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { VisitForm } from "@/features/visits/components/visit-form";
import { useUpdateVisit, useVisit } from "@/features/visits/hooks/use-visits";
import { visitToFormInput, type VisitFormInput } from "@/lib/mock/visits";

export function VisitEditContent({ visitId }: { visitId: string }) {
  const router = useRouter();
  const { data: visit, isLoading } = useVisit(visitId);
  const updateVisit = useUpdateVisit(visitId);

  if (isLoading) {
    return <PageSkeleton title="Edit Visit" />;
  }

  if (!visit) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Visit not found"
        description="This visit may have been removed, or the link is incorrect."
      />
    );
  }

  function handleSubmit(values: VisitFormInput) {
    updateVisit.mutate(values, {
      onSuccess: () => {
        router.push(`/dashboard/visits/${visitId}`);
      },
    });
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title="Edit Visit"
        description={`Update ${visit.visit_number} for ${visit.patient_name}.`}
      />
      <VisitForm
        defaultValues={visitToFormInput(visit)}
        onSubmit={handleSubmit}
        isSubmitting={updateVisit.isPending}
        submitLabel="Save Changes"
      />
    </div>
  );
}
