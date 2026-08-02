import { getPasswordStrength, type PasswordStrength } from "@/lib/auth/validation";
import { cn } from "@/lib/utils";

const STRENGTH_COLOR: Record<PasswordStrength["score"], string> = {
  0: "bg-destructive",
  1: "bg-destructive",
  2: "bg-warning",
  3: "bg-primary",
  4: "bg-success",
};

export function PasswordStrengthIndicator({ password }: { password: string }) {
  if (!password) return null;

  const { score, label } = getPasswordStrength(password);

  return (
    <div className="space-y-1.5" aria-live="polite">
      <div className="flex gap-1" role="presentation">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className={cn(
              "h-1.5 flex-1 rounded-full bg-muted",
              index < score && STRENGTH_COLOR[score],
            )}
          />
        ))}
      </div>
      <p className="text-xs text-muted-foreground">Password strength: {label}</p>
    </div>
  );
}
