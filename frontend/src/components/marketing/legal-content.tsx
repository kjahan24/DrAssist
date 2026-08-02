interface LegalSection {
  heading: string;
  body: string[];
}

interface LegalContentProps {
  title: string;
  lastUpdated: string;
  intro: string;
  sections: LegalSection[];
}

// Shared prose layout for Privacy Policy / Terms of Service — plain
// Tailwind utilities rather than a typography plugin, since these are the
// only two pages that need this shape.
export function LegalContent({ title, lastUpdated, intro, sections }: LegalContentProps) {
  return (
    <article className="container max-w-3xl py-20 sm:py-28">
      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">Last updated: {lastUpdated}</p>
      <div className="mt-4 rounded-lg border border-dashed bg-muted/30 p-4 text-sm text-muted-foreground">
        This is a template {title.toLowerCase()} provided for reference and should be reviewed by
        qualified legal counsel before being relied upon as binding.
      </div>
      <p className="mt-8 text-muted-foreground">{intro}</p>
      <div className="mt-8 space-y-8">
        {sections.map((section) => (
          <section key={section.heading}>
            <h2 className="text-xl font-semibold">{section.heading}</h2>
            <div className="mt-3 space-y-3 text-muted-foreground">
              {section.body.map((paragraph, index) => (
                <p key={index}>{paragraph}</p>
              ))}
            </div>
          </section>
        ))}
      </div>
    </article>
  );
}
