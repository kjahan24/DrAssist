import { cn } from "@/lib/utils";

interface SectionHeadingProps {
  eyebrow?: string;
  title: string;
  description?: string;
  align?: "center" | "left";
  className?: string;
  // Defaults to h2 (a *section* within a page that has its own h1
  // elsewhere, e.g. every Home page section). Pages that use this
  // component as their only heading — Features, Solutions, Pricing,
  // About, Contact, FAQ — must pass "h1" so the page has exactly one,
  // per WCAG heading-structure requirements.
  titleAs?: "h1" | "h2";
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  align = "center",
  className,
  titleAs: TitleTag = "h2",
}: SectionHeadingProps) {
  return (
    <div
      className={cn("max-w-2xl space-y-3", align === "center" && "mx-auto text-center", className)}
    >
      {eyebrow && (
        <p className="text-sm font-semibold uppercase tracking-wide text-primary">{eyebrow}</p>
      )}
      <TitleTag className="text-3xl font-semibold tracking-tight sm:text-4xl">{title}</TitleTag>
      {description && <p className="text-lg text-muted-foreground">{description}</p>}
    </div>
  );
}
