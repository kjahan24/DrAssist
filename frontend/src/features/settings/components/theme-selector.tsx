"use client";

import { Laptop, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";
import { useMounted } from "@/hooks/use-mounted";
import { cn } from "@/lib/utils";

const THEME_OPTIONS = [
  { label: "Light", value: "light", icon: Sun },
  { label: "Dark", value: "dark", icon: Moon },
  { label: "System", value: "system", icon: Laptop },
] as const;

// Unlike every other control on the Preferences page, Theme is real,
// already-working infrastructure (`next-themes`) — this reads/writes it
// directly via `useTheme()` instead of `lib/mock/settings.ts`, the same
// underlying hook `components/layout/theme-toggle.tsx` already uses, just
// presented as a three-way button group appropriate for a settings page
// rather than a compact header dropdown.
export function ThemeSelector() {
  const { theme, setTheme } = useTheme();
  const mounted = useMounted();

  return (
    <div className="flex gap-2" role="group" aria-label="Theme">
      {THEME_OPTIONS.map((option) => (
        <Button
          key={option.value}
          type="button"
          size="sm"
          variant={mounted && theme === option.value ? "default" : "outline"}
          onClick={() => setTheme(option.value)}
          className={cn("flex-1")}
          aria-pressed={mounted && theme === option.value}
        >
          <option.icon className="size-4" aria-hidden="true" />
          {option.label}
        </Button>
      ))}
    </div>
  );
}
