import { HeartPulse } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { formatDateTime } from "@/lib/format";
import type { VitalSignsSummary } from "@/lib/mock/patients";

function VitalStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium">{value}</dd>
    </div>
  );
}

export function VitalSignsSection({ vitalSigns }: { vitalSigns: VitalSignsSummary | null }) {
  return (
    <SectionCard
      title="Vital Signs"
      description={
        vitalSigns ? `Last recorded ${formatDateTime(vitalSigns.recorded_at)}` : undefined
      }
    >
      {!vitalSigns ? (
        <EmptyState icon={HeartPulse} title="No vital signs on file" />
      ) : (
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <VitalStat label="Temperature" value={`${vitalSigns.temperature_c}°C`} />
          <VitalStat label="Pulse" value={`${vitalSigns.pulse_bpm} bpm`} />
          <VitalStat label="Respiratory Rate" value={`${vitalSigns.respiratory_rate}/min`} />
          <VitalStat
            label="Blood Pressure"
            value={`${vitalSigns.systolic_bp}/${vitalSigns.diastolic_bp}`}
          />
          <VitalStat label="SpO2" value={`${vitalSigns.spo2}%`} />
          <VitalStat label="BMI" value={vitalSigns.bmi.toFixed(1)} />
        </dl>
      )}
    </SectionCard>
  );
}
