// Standalone reference-data mock backing the "Medication search (mock)"
// feature and `MedicationSelector` component — a small in-memory
// medication catalog, explicitly NOT a real drug database integration
// (the task itself calls this out as "(mock)"). No backend module
// exists for this; it's frontend-only reference data, the same kind of
// thing `lib/mock/doctors.ts` is for doctor identity.
//
// `AdministrationRoute` IS grounded in the real backend
// (`app.modules.prescriptions.domain.enums.AdministrationRoute`) but
// lives here rather than in `lib/mock/prescriptions.ts` so that file
// has no need to import from this one in the wrong direction —
// `prescriptions.ts` imports the catalog and this enum FROM here, this
// file depends on nothing.

const MIN_LATENCY_MS = 200;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

export type AdministrationRoute =
  | "oral"
  | "iv"
  | "im"
  | "sc"
  | "topical"
  | "inhalation"
  | "ophthalmic"
  | "otic"
  | "nasal"
  | "rectal"
  | "vaginal"
  | "other";

export const ADMINISTRATION_ROUTE_OPTIONS: { label: string; value: AdministrationRoute }[] = [
  { label: "Oral", value: "oral" },
  { label: "Intravenous (IV)", value: "iv" },
  { label: "Intramuscular (IM)", value: "im" },
  { label: "Subcutaneous (SC)", value: "sc" },
  { label: "Topical", value: "topical" },
  { label: "Inhalation", value: "inhalation" },
  { label: "Ophthalmic", value: "ophthalmic" },
  { label: "Otic", value: "otic" },
  { label: "Nasal", value: "nasal" },
  { label: "Rectal", value: "rectal" },
  { label: "Vaginal", value: "vaginal" },
  { label: "Other", value: "other" },
];

export interface MedicationCatalogEntry {
  medication_id: string;
  medication_name: string;
  generic_name: string | null;
  common_strengths: string[];
  default_route: AdministrationRoute;
  default_dosage_unit: string;
  default_frequency: string;
}

const MEDICATIONS: MedicationCatalogEntry[] = [
  {
    medication_id: "med-cat-0001",
    medication_name: "Lisinopril",
    generic_name: "Lisinopril",
    common_strengths: ["5 mg", "10 mg", "20 mg", "40 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Once daily",
  },
  {
    medication_id: "med-cat-0002",
    medication_name: "Metformin",
    generic_name: "Metformin HCl",
    common_strengths: ["500 mg", "850 mg", "1000 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Twice daily",
  },
  {
    medication_id: "med-cat-0003",
    medication_name: "Atorvastatin",
    generic_name: "Atorvastatin calcium",
    common_strengths: ["10 mg", "20 mg", "40 mg", "80 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Once daily",
  },
  {
    medication_id: "med-cat-0004",
    medication_name: "Amoxicillin",
    generic_name: "Amoxicillin",
    common_strengths: ["250 mg", "500 mg", "875 mg"],
    default_route: "oral",
    default_dosage_unit: "capsule",
    default_frequency: "Three times daily",
  },
  {
    medication_id: "med-cat-0005",
    medication_name: "Ibuprofen",
    generic_name: "Ibuprofen",
    common_strengths: ["200 mg", "400 mg", "600 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Every 6-8 hours as needed",
  },
  {
    medication_id: "med-cat-0006",
    medication_name: "Acetaminophen",
    generic_name: "Paracetamol",
    common_strengths: ["325 mg", "500 mg", "650 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Every 6 hours as needed",
  },
  {
    medication_id: "med-cat-0007",
    medication_name: "Omeprazole",
    generic_name: "Omeprazole",
    common_strengths: ["10 mg", "20 mg", "40 mg"],
    default_route: "oral",
    default_dosage_unit: "capsule",
    default_frequency: "Once daily",
  },
  {
    medication_id: "med-cat-0008",
    medication_name: "Albuterol",
    generic_name: "Salbutamol",
    common_strengths: ["90 mcg/actuation"],
    default_route: "inhalation",
    default_dosage_unit: "puff",
    default_frequency: "Every 4-6 hours as needed",
  },
  {
    medication_id: "med-cat-0009",
    medication_name: "Levothyroxine",
    generic_name: "Levothyroxine sodium",
    common_strengths: ["25 mcg", "50 mcg", "75 mcg", "100 mcg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Once daily",
  },
  {
    medication_id: "med-cat-0010",
    medication_name: "Losartan",
    generic_name: "Losartan potassium",
    common_strengths: ["25 mg", "50 mg", "100 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Once daily",
  },
  {
    medication_id: "med-cat-0011",
    medication_name: "Metoprolol",
    generic_name: "Metoprolol tartrate",
    common_strengths: ["25 mg", "50 mg", "100 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Twice daily",
  },
  {
    medication_id: "med-cat-0012",
    medication_name: "Amlodipine",
    generic_name: "Amlodipine besylate",
    common_strengths: ["2.5 mg", "5 mg", "10 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Once daily",
  },
  {
    medication_id: "med-cat-0013",
    medication_name: "Gabapentin",
    generic_name: "Gabapentin",
    common_strengths: ["100 mg", "300 mg", "600 mg"],
    default_route: "oral",
    default_dosage_unit: "capsule",
    default_frequency: "Three times daily",
  },
  {
    medication_id: "med-cat-0014",
    medication_name: "Hydrochlorothiazide",
    generic_name: "Hydrochlorothiazide",
    common_strengths: ["12.5 mg", "25 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Once daily",
  },
  {
    medication_id: "med-cat-0015",
    medication_name: "Sertraline",
    generic_name: "Sertraline HCl",
    common_strengths: ["25 mg", "50 mg", "100 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Once daily",
  },
  {
    medication_id: "med-cat-0016",
    medication_name: "Simvastatin",
    generic_name: "Simvastatin",
    common_strengths: ["10 mg", "20 mg", "40 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Once daily at bedtime",
  },
  {
    medication_id: "med-cat-0017",
    medication_name: "Prednisone",
    generic_name: "Prednisone",
    common_strengths: ["5 mg", "10 mg", "20 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Once daily",
  },
  {
    medication_id: "med-cat-0018",
    medication_name: "Azithromycin",
    generic_name: "Azithromycin",
    common_strengths: ["250 mg", "500 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Once daily",
  },
  {
    medication_id: "med-cat-0019",
    medication_name: "Warfarin",
    generic_name: "Warfarin sodium",
    common_strengths: ["1 mg", "2 mg", "5 mg"],
    default_route: "oral",
    default_dosage_unit: "tablet",
    default_frequency: "Once daily",
  },
  {
    medication_id: "med-cat-0020",
    medication_name: "Insulin Glargine",
    generic_name: "Insulin glargine",
    common_strengths: ["100 units/mL"],
    default_route: "sc",
    default_dosage_unit: "unit",
    default_frequency: "Once daily at bedtime",
  },
];

export interface MedicationListParams {
  search?: string;
}

export function listMedications(
  params: MedicationListParams = {},
): Promise<MedicationCatalogEntry[]> {
  const needle = (params.search ?? "").trim().toLowerCase();
  const filtered = needle
    ? MEDICATIONS.filter(
        (medication) =>
          medication.medication_name.toLowerCase().includes(needle) ||
          (medication.generic_name ?? "").toLowerCase().includes(needle),
      )
    : MEDICATIONS;
  return mockFetch(filtered);
}

export function getMedication(medicationId: string): Promise<MedicationCatalogEntry | null> {
  const found = MEDICATIONS.find((medication) => medication.medication_id === medicationId) ?? null;
  return mockFetch(found);
}
