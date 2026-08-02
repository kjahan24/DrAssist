import { Building2, Lock, ShieldCheck, Users } from "lucide-react";

// No customer logos — DrAssist has no published customers yet, and
// fabricating them would be dishonest. These are honest, verifiable
// architectural facts instead (see `content/marketing/security.ts` for
// the fuller version on the Home page's own Security section).
const trustMarkers = [
  { icon: Building2, label: "Multi-tenant by design" },
  { icon: ShieldCheck, label: "Role-based access control" },
  { icon: Lock, label: "Encrypted credentials" },
  { icon: Users, label: "Built for care teams" },
];

export function TrustedBySection() {
  return (
    <section className="border-y bg-muted/30 py-10">
      <div className="container">
        <p className="text-center text-sm font-medium text-muted-foreground">
          Built on a foundation healthcare teams can rely on
        </p>
        <div className="mt-6 grid grid-cols-2 gap-6 sm:grid-cols-4">
          {trustMarkers.map((marker) => {
            const Icon = marker.icon;
            return (
              <div key={marker.label} className="flex flex-col items-center gap-2 text-center">
                <Icon className="size-5 text-muted-foreground" aria-hidden="true" />
                <span className="text-sm text-muted-foreground">{marker.label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
