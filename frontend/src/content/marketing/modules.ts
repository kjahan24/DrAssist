// "Platform Modules" section data — a marketing-facing summary of the
// same module boundaries the backend actually ships
// (`backend/app/modules/*`), grouped for readability rather than listing
// all ~27 by name.
export interface PlatformModuleGroup {
  title: string;
  description: string;
  modules: string[];
}

export const platformModules: PlatformModuleGroup[] = [
  {
    title: "Patients & Visits",
    description: "The clinical record foundation every other module builds on.",
    modules: ["Patients", "Visits", "Vital Signs", "Chief Complaints"],
  },
  {
    title: "Clinical Documentation",
    description: "Structured documentation from first assessment to final coding.",
    modules: [
      "Clinical Notes",
      "SOAP Notes",
      "Diagnoses",
      "Procedures",
      "Clinical Reasoning",
      "Differential Diagnosis",
      "ICD-10 Coding",
      "Doctor Reviews",
    ],
  },
  {
    title: "Orders & Results",
    description: "Prescriptions and lab work, tracked end-to-end.",
    modules: ["Prescriptions", "Lab Orders", "Lab Results"],
  },
  {
    title: "Scheduling",
    description: "Appointment booking backed by real doctor availability.",
    modules: ["Appointments", "Doctor Availability"],
  },
  {
    title: "Records & Access",
    description: "Documents, timelines, and controlled sharing with families.",
    modules: ["Documents", "Attachments", "Patient Timeline", "Family Access"],
  },
  {
    title: "Platform & Trust",
    description: "The multi-tenant, access-controlled foundation underneath every module.",
    modules: ["Organizations", "Doctors", "Access Control", "Audit Logs", "Notifications"],
  },
];
