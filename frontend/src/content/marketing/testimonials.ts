// Placeholder content — DrAssist has no published customer testimonials
// yet. Deliberately role-based, not attributed to named individuals, so
// nothing here reads as a real (or real-seeming) endorsement. Replace
// wholesale once real testimonials exist.
export interface Testimonial {
  quote: string;
  role: string;
  initials: string;
}

export const testimonials: Testimonial[] = [
  {
    quote:
      "Having every patient's clinical record, documents, and timeline in one place has changed how our team works day to day.",
    role: "Family Medicine Physician",
    initials: "FM",
  },
  {
    quote:
      "Role-based access and audit logs gave us the confidence to roll this out across every department.",
    role: "Clinic Administrator",
    initials: "CA",
  },
  {
    quote:
      "The REST API meant our existing systems could integrate on day one instead of waiting on a custom build.",
    role: "Healthcare IT Director",
    initials: "IT",
  },
];
