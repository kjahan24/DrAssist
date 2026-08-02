// Public marketing IA — separate from `config/navigation.ts` (the
// authenticated dashboard's sidebar), since the two serve different
// audiences and neither should reference the other's routes.
export interface MarketingNavLink {
  title: string;
  href: string;
}

export const marketingNavLinks: MarketingNavLink[] = [
  { title: "Features", href: "/features" },
  { title: "Solutions", href: "/solutions" },
  { title: "Pricing", href: "/pricing" },
  { title: "About", href: "/about" },
];

export const footerLinks: { title: string; links: MarketingNavLink[] }[] = [
  {
    title: "Product",
    links: [
      { title: "Features", href: "/features" },
      { title: "Solutions", href: "/solutions" },
      { title: "Pricing", href: "/pricing" },
    ],
  },
  {
    title: "Company",
    links: [
      { title: "About", href: "/about" },
      { title: "Careers", href: "/careers" },
      { title: "Contact", href: "/contact" },
    ],
  },
  {
    title: "Resources",
    links: [
      { title: "Blog", href: "/blog" },
      { title: "FAQ", href: "/faq" },
    ],
  },
  {
    title: "Legal",
    links: [
      { title: "Privacy Policy", href: "/privacy" },
      { title: "Terms of Service", href: "/terms" },
    ],
  },
];
