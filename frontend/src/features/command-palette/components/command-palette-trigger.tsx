"use client";

import { Search } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { CommandPalette } from "@/features/command-palette/components/command-palette";

// Mounted once in `AppHeader`, replacing the disabled search input that
// component's own docstring already called out as a placeholder ("no
// search endpoint exists for any module yet"). Owns the global Ctrl+K /
// Cmd+K listener and the visible trigger button; `CommandPalette` itself
// is stateless with respect to *how* it opens.
export function CommandPaletteTrigger() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen((current) => !current);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <>
      <Button
        variant="outline"
        onClick={() => setOpen(true)}
        className="hidden h-9 w-56 justify-start gap-2 text-muted-foreground md:flex lg:w-72"
      >
        <Search className="size-4 shrink-0" aria-hidden="true" />
        <span className="flex-1 text-left">Search...</span>
        <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-0.5 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
          <span className="text-xs">⌘</span>K
        </kbd>
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setOpen(true)}
        className="md:hidden"
        aria-label="Search"
      >
        <Search className="size-5" aria-hidden="true" />
      </Button>
      <CommandPalette open={open} onOpenChange={setOpen} />
    </>
  );
}
