import { SectionHeading } from "@/components/marketing/section-heading";
import { platformModules } from "@/content/marketing/modules";

export function PlatformModulesSection() {
  return (
    <section className="border-t bg-muted/30 py-20 sm:py-28">
      <div className="container">
        <SectionHeading
          eyebrow="Platform Modules"
          title="Built as one connected system"
          description="Every module shares the same organization, patient, and access-control foundation — nothing is bolted on."
        />
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {platformModules.map((group) => (
            <div key={group.title} className="rounded-lg border bg-background p-6">
              <h3 className="font-semibold">{group.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{group.description}</p>
              <ul className="mt-4 flex flex-wrap gap-2">
                {group.modules.map((module) => (
                  <li key={module} className="rounded-full bg-muted px-3 py-1 text-xs font-medium">
                    {module}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
