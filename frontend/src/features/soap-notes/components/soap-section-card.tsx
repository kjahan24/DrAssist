import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface SoapSectionCardProps {
  letter: "S" | "O" | "A" | "P";
  title: string;
  children: React.ReactNode;
}

// The building block for each of the four SOAP quadrants (Subjective,
// Objective, Assessment, Plan) — distinct from the generic
// `SoapNoteDetailsCard` by design: a single letter badge gives each
// quadrant an immediately recognizable identity, on both the detail
// page (read-only) and the editor (each field grouped under its own
// card). Renders a real `<h2>` like `SectionCard` does, just with the
// badge instead of `SectionCard`'s plain title-only header.
export function SoapSectionCard({ letter, title, children }: SoapSectionCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center gap-3 space-y-0">
        <span
          className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-sm font-semibold text-primary"
          aria-hidden="true"
        >
          {letter}
        </span>
        <h2 className="font-semibold leading-none tracking-tight">{title}</h2>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
