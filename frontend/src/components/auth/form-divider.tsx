export function FormDivider({ label = "or" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="h-px flex-1 bg-border" aria-hidden="true" />
      <span className="text-xs uppercase text-muted-foreground">{label}</span>
      <div className="h-px flex-1 bg-border" aria-hidden="true" />
    </div>
  );
}
