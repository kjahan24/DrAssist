"use client";

import { AlertTriangle } from "lucide-react";

import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { AllergiesSection } from "@/features/patients/components/detail/allergies-section";
import { ConditionsSection } from "@/features/patients/components/detail/conditions-section";
import { DocumentsSection } from "@/features/patients/components/detail/documents-section";
import { MedicationsSection } from "@/features/patients/components/detail/medications-section";
import { RecentVisitsSection } from "@/features/patients/components/detail/recent-visits-section";
import { TimelineSection } from "@/features/patients/components/detail/timeline-section";
import { VitalSignsSection } from "@/features/patients/components/detail/vital-signs-section";
import { PatientInformationCard } from "@/features/patients/components/patient-information-card";
import { PatientProfileHeader } from "@/features/patients/components/patient-profile-header";
import { usePatient } from "@/features/patients/hooks/use-patients";
import { formatDate } from "@/lib/format";

export function PatientDetailContent({ patientId }: { patientId: string }) {
  const { data: patient, isLoading } = usePatient(patientId);

  if (isLoading) {
    return <PageSkeleton title="Patient Details" />;
  }

  if (!patient) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Patient not found"
        description="This patient may have been removed, or the link is incorrect."
      />
    );
  }

  const address = `${patient.contact.address_line1}${
    patient.contact.address_line2 ? `, ${patient.contact.address_line2}` : ""
  }, ${patient.contact.city}, ${patient.contact.state} ${patient.contact.postal_code}`;

  return (
    <div className="space-y-6">
      <PatientProfileHeader patient={patient} />

      <div className="grid gap-6 lg:grid-cols-2">
        <PatientInformationCard
          title="Basic Information"
          fields={[
            { label: "Patient ID", value: patient.patient_number },
            { label: "Date of Birth", value: formatDate(patient.date_of_birth) },
            { label: "Gender", value: <span className="capitalize">{patient.gender}</span> },
            { label: "Blood Group", value: patient.blood_group },
          ]}
        />
        <PatientInformationCard
          title="Contact Information"
          fields={[
            { label: "Phone", value: patient.contact.phone },
            { label: "Email", value: patient.contact.email },
            { label: "Address", value: address },
          ]}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <PatientInformationCard
          title="Emergency Contact"
          emptyMessage="No emergency contact on file."
          fields={
            patient.emergency_contact
              ? [
                  { label: "Name", value: patient.emergency_contact.name },
                  { label: "Relationship", value: patient.emergency_contact.relationship },
                  { label: "Phone", value: patient.emergency_contact.phone },
                ]
              : []
          }
        />
        <PatientInformationCard
          title="Insurance"
          emptyMessage="No insurance on file."
          fields={
            patient.insurance[0]
              ? [
                  { label: "Provider", value: patient.insurance[0].provider_name },
                  { label: "Policy Number", value: patient.insurance[0].policy_number },
                  { label: "Coverage Type", value: patient.insurance[0].coverage_type },
                ]
              : []
          }
        />
      </div>

      <AllergiesSection allergies={patient.allergies} />
      <MedicationsSection medications={patient.medications} />
      <ConditionsSection conditions={patient.medical_conditions} />
      <VitalSignsSection vitalSigns={patient.vital_signs} />
      <RecentVisitsSection visits={patient.recent_visits} />

      <div className="grid gap-6 lg:grid-cols-2">
        <DocumentsSection documents={patient.documents} />
        <TimelineSection events={patient.timeline_events} />
      </div>
    </div>
  );
}
