import { VisitDetailsCard } from "@/features/visits/components/visit-details-card";
import { formatDateTime } from "@/lib/format";
import type { VisitDetail } from "@/lib/mock/visits";

export function VitalSignsSection({ visit }: { visit: VisitDetail }) {
  const vitals = visit.vital_signs;

  const fields = vitals
    ? [
        { label: "Recorded At", value: formatDateTime(vitals.recorded_at) },
        { label: "Temperature", value: `${vitals.temperature_c} °C` },
        { label: "Pulse", value: `${vitals.pulse_bpm} bpm` },
        { label: "Respiratory Rate", value: `${vitals.respiratory_rate} /min` },
        { label: "Blood Pressure", value: `${vitals.systolic_bp}/${vitals.diastolic_bp} mmHg` },
        { label: "SpO2", value: `${vitals.spo2}%` },
        { label: "Height", value: vitals.height_cm ? `${vitals.height_cm} cm` : null },
        { label: "Weight", value: vitals.weight_kg ? `${vitals.weight_kg} kg` : null },
        { label: "BMI", value: vitals.bmi ? String(vitals.bmi) : null },
        {
          label: "Blood Glucose",
          value: vitals.blood_glucose ? `${vitals.blood_glucose} mg/dL` : null,
        },
        {
          label: "Pain Score",
          value:
            vitals.pain_score !== null && vitals.pain_score !== undefined
              ? `${vitals.pain_score}/10`
              : null,
        },
      ]
    : [];

  return (
    <VisitDetailsCard
      title="Vital Signs Summary"
      fields={fields}
      emptyMessage="No vital signs recorded for this visit."
    />
  );
}
