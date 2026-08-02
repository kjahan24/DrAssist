"use client";

import { Bold, Check, Cloud, Italic, List, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Control, UseFormWatch } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormControl, FormField, FormItem, FormMessage } from "@/components/ui/form";
import { Textarea } from "@/components/ui/textarea";
import { SoapSectionCard } from "@/features/soap-notes/components/soap-section-card";
import type { SOAPNoteFormInput } from "@/lib/mock/soap-notes";

type QuadrantFieldName = "subjective" | "objective" | "assessment" | "plan";

const QUADRANTS: { name: QuadrantFieldName; letter: "S" | "O" | "A" | "P"; title: string }[] = [
  { name: "subjective", letter: "S", title: "Subjective" },
  { name: "objective", letter: "O", title: "Objective" },
  { name: "assessment", letter: "A", title: "Assessment" },
  { name: "plan", letter: "P", title: "Plan" },
];

function wrapSelection(value: string, start: number, end: number, marker: string) {
  const before = value.slice(0, start);
  const selected = value.slice(start, end);
  const after = value.slice(end);
  return {
    next: `${before}${marker}${selected}${marker}${after}`,
    nextStart: start + marker.length,
    nextEnd: end + marker.length,
  };
}

function prefixLine(value: string, cursor: number, prefix: string) {
  const lineStart = value.lastIndexOf("\n", Math.max(0, cursor - 1)) + 1;
  return {
    next: value.slice(0, lineStart) + prefix + value.slice(lineStart),
    nextCursor: cursor + prefix.length,
  };
}

interface QuadrantFieldProps {
  control: Control<SOAPNoteFormInput>;
  name: QuadrantFieldName;
  letter: "S" | "O" | "A" | "P";
  title: string;
}

// One SOAP quadrant: a `SoapSectionCard` (matching the detail page's own
// visual identity) housing a mini formatting toolbar (Bold, Italic,
// Bulleted List — lightweight markdown, since this is explicitly a
// *mock* rich text editor, not a real WYSIWYG) plus a textarea.
function QuadrantField({ control, name, letter, title }: QuadrantFieldProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => {
        function format(kind: "bold" | "italic" | "list") {
          const element = textareaRef.current;
          if (!element) return;
          const start = element.selectionStart;
          const end = element.selectionEnd;
          const value = field.value;

          if (kind === "list") {
            const { next, nextCursor } = prefixLine(value, start, "- ");
            field.onChange(next);
            requestAnimationFrame(() => {
              element.focus();
              element.setSelectionRange(nextCursor, nextCursor);
            });
            return;
          }

          const marker = kind === "bold" ? "**" : "_";
          const { next, nextStart, nextEnd } = wrapSelection(value, start, end, marker);
          field.onChange(next);
          requestAnimationFrame(() => {
            element.focus();
            element.setSelectionRange(nextStart, nextEnd);
          });
        }

        return (
          <SoapSectionCard letter={letter} title={title}>
            <FormItem>
              <div className="mb-2 flex items-center gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  aria-label={`Bold — ${title}`}
                  onClick={() => format("bold")}
                >
                  <Bold className="size-3.5" aria-hidden="true" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  aria-label={`Italic — ${title}`}
                  onClick={() => format("italic")}
                >
                  <Italic className="size-3.5" aria-hidden="true" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  aria-label={`Bulleted list — ${title}`}
                  onClick={() => format("list")}
                >
                  <List className="size-3.5" aria-hidden="true" />
                </Button>
              </div>
              <FormControl>
                <Textarea
                  value={field.value}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                  name={field.name}
                  ref={(element) => {
                    field.ref(element);
                    textareaRef.current = element;
                  }}
                  rows={4}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          </SoapSectionCard>
        );
      }}
    />
  );
}

interface SoapNoteEditorProps {
  control: Control<SOAPNoteFormInput>;
  watch: UseFormWatch<SOAPNoteFormInput>;
}

// The "editor" required by this module — four `SoapSectionCard`-wrapped
// markdown-lite text fields, one per SOAP quadrant, plus a UI-only
// autosave indicator that reacts to any field change with a brief
// "Unsaved changes" → "Saving..." → "All changes saved" cycle (no real
// persistence — actual saving still happens on explicit form submit).
export function SoapNoteEditor({ control, watch }: SoapNoteEditorProps) {
  const watchedValues = watch(["subjective", "objective", "assessment", "plan"]);
  const [saveState, setSaveState] = useState<"saved" | "saving" | "unsaved">("saved");
  const isFirstRender = useRef(true);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    setSaveState("unsaved");
    const savingTimeout = setTimeout(() => setSaveState("saving"), 400);
    const savedTimeout = setTimeout(() => setSaveState("saved"), 1400);
    return () => {
      clearTimeout(savingTimeout);
      clearTimeout(savedTimeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(watchedValues)]);

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <div
          className="flex items-center gap-1.5 text-xs text-muted-foreground"
          role="status"
          aria-live="polite"
        >
          {saveState === "saved" && (
            <>
              <Check className="size-3.5" aria-hidden="true" />
              All changes saved
            </>
          )}
          {saveState === "saving" && (
            <>
              <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
              Saving...
            </>
          )}
          {saveState === "unsaved" && (
            <>
              <Cloud className="size-3.5" aria-hidden="true" />
              Unsaved changes
            </>
          )}
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {QUADRANTS.map((quadrant) => (
          <QuadrantField
            key={quadrant.name}
            control={control}
            name={quadrant.name}
            letter={quadrant.letter}
            title={quadrant.title}
          />
        ))}
      </div>
    </div>
  );
}
