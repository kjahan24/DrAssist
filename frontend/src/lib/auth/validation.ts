import { z } from "zod";

// Shared password policy for Register and Reset Password — kept in one
// place so the rule set (and its error copy) can't drift between the two
// forms.
export const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters")
  .regex(/[a-z]/, "Password must include a lowercase letter")
  .regex(/[A-Z]/, "Password must include an uppercase letter")
  .regex(/[0-9]/, "Password must include a number");

export type PasswordStrengthLabel = "Weak" | "Fair" | "Good" | "Strong";

export interface PasswordStrength {
  score: 0 | 1 | 2 | 3 | 4;
  label: PasswordStrengthLabel;
}

// A Record (not an array) so every possible `score` has a statically
// known, non-optional label — an array here would make every index read
// `PasswordStrengthLabel | undefined` under this project's
// `noUncheckedIndexedAccess`.
const STRENGTH_LABELS: Record<PasswordStrength["score"], PasswordStrengthLabel> = {
  0: "Weak",
  1: "Weak",
  2: "Fair",
  3: "Good",
  4: "Strong",
};

// A simple, transparent heuristic (not a real entropy estimator like
// zxcvbn — no such dependency is in this project's stack) — length plus
// character-class variety, which is enough to give useful, honest visual
// feedback without pulling in a large scoring library for one indicator.
export function getPasswordStrength(password: string): PasswordStrength {
  if (password.length === 0) {
    return { score: 0, label: STRENGTH_LABELS[0] };
  }

  let score = 0;
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^a-zA-Z0-9]/.test(password)) score += 1;

  const clamped = Math.min(score, 4) as PasswordStrength["score"];
  return { score: clamped, label: STRENGTH_LABELS[clamped] };
}
