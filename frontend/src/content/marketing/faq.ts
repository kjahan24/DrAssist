export interface FaqItem {
  question: string;
  answer: string;
}

export const faqItems: FaqItem[] = [
  {
    question: "Is DrAssist built with healthcare compliance in mind?",
    answer:
      "Yes. Multi-tenant data isolation, role-based access control, and full audit logging are built into the platform's architecture from the ground up. Contact us to discuss your organization's specific compliance requirements.",
  },
  {
    question: "Can I use DrAssist as a solo practitioner?",
    answer: "Yes — the Starter plan is designed for individual doctors and small practices.",
  },
  {
    question: "Does DrAssist integrate with other systems?",
    answer:
      "Every module is exposed through a documented REST API, so DrAssist can integrate with your existing tools and workflows.",
  },
  {
    question: "Is my organization's data isolated from others?",
    answer:
      "Yes. DrAssist is multi-tenant by design — every organization's data is fully isolated at the data layer.",
  },
  {
    question: "When will AI features be available?",
    answer:
      "AI-assisted documentation and clinical insights are in active development — reach out to be notified when they launch.",
  },
  {
    question: "How do I get started?",
    answer:
      "Reach out through our contact page and our team will help you find the right plan for your organization.",
  },
];
