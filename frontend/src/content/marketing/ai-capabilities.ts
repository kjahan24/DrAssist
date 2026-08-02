export interface AiCapability {
  title: string;
  description: string;
}

// All "Coming Soon" — no AI features are implemented yet (out of scope
// for this module and every module before it).
export const aiCapabilities: AiCapability[] = [
  {
    title: "AI-Assisted Documentation",
    description:
      "Draft clinical notes faster with AI support that stays inside your review workflow.",
  },
  {
    title: "Clinical Insights",
    description: "Surface relevant history and patterns from a patient's timeline as you work.",
  },
  {
    title: "Smart Coding Support",
    description: "AI-assisted suggestions for differential diagnosis and ICD-10 coding.",
  },
];
