"use client";

import { Bold, Check, Cloud, Italic, List, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Control, UseFormSetValue, UseFormWatch } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { CLINICAL_NOTE_TEMPLATES, type ClinicalNoteFormInput } from "@/lib/mock/clinical-notes";

type NarrativeFieldName =
  | "chief_complaint_summary"
  | "history_summary"
  | "examination_summary"
  | "assessment_summary"
  | "plan_summary";

const NARRATIVE_FIELDS: { name: NarrativeFieldName; label: string }[] = [
  { name: "chief_complaint_summary", label: "Chief Complaint" },
  { name: "history_summary", label: "History of Present Illness" },
  { name: "examination_summary", label: "Examination Findings" },
];

const ASSESSMENT_PLAN_FIELDS: { name: NarrativeFieldName; label: string }[] = [
  { name: "assessment_summary", label: "Assessment" },
  { name: "plan_summary", label: "Plan" },
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

interface RichTextFieldProps {
  control: Control<ClinicalNoteFormInput>;
  name: NarrativeFieldName;
  label: string;
}

// A single narrative field: label + a mini formatting toolbar (Bold,
// Italic, Bulleted List — inserted as lightweight markdown, since this
// is explicitly a *mock* rich text editor, not a real WYSIWYG) + a
// textarea. Each field owns its own toolbar/selection state rather than
// sharing one across fields, which keeps "format the text I just
// selected" unambiguous.
function RichTextField({ control, name, label }: RichTextFieldProps) {
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
          <FormItem>
            <FormLabel>{label}</FormLabel>
            <div className="overflow-hidden rounded-md border">
              <div className="flex items-center gap-1 border-b bg-muted/40 px-2 py-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  aria-label={`Bold — ${label}`}
                  onClick={() => format("bold")}
                >
                  <Bold className="size-3.5" aria-hidden="true" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  aria-label={`Italic — ${label}`}
                  onClick={() => format("italic")}
                >
                  <Italic className="size-3.5" aria-hidden="true" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  aria-label={`Bulleted list — ${label}`}
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
                  rows={3}
                  className="rounded-none border-0 focus-visible:ring-0"
                />
              </FormControl>
            </div>
            <FormMessage />
          </FormItem>
        );
      }}
    />
  );
}

interface ClinicalNoteEditorProps {
  control: Control<ClinicalNoteFormInput>;
  watch: UseFormWatch<ClinicalNoteFormInput>;
  setValue: UseFormSetValue<ClinicalNoteFormInput>;
}

// The "rich text editor (mock)" required by this module — a set of
// markdown-lite text fields (see `RichTextField`) plus two features the
// task explicitly asks for: a Templates selector that fills all five
// fields at once, and a UI-only autosave indicator that reacts to any
// field change with a brief "Unsaved changes" → "Saving..." → "All
// changes saved" cycle (no real persistence — actual saving still
// happens on explicit form submit).
export function ClinicalNoteEditor({ control, watch, setValue }: ClinicalNoteEditorProps) {
  const watchedValues = watch([
    "chief_complaint_summary",
    "history_summary",
    "examination_summary",
    "assessment_summary",
    "plan_summary",
  ]);
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

  function applyTemplate(templateId: string) {
    const template = CLINICAL_NOTE_TEMPLATES.find((option) => option.id === templateId);
    if (!template) return;
    setValue("chief_complaint_summary", template.chief_complaint_summary, { shouldDirty: true });
    setValue("history_summary", template.history_summary, { shouldDirty: true });
    setValue("examination_summary", template.examination_summary, { shouldDirty: true });
    setValue("assessment_summary", template.assessment_summary, { shouldDirty: true });
    setValue("plan_summary", template.plan_summary, { shouldDirty: true });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <Select onValueChange={applyTemplate}>
          <SelectTrigger className="w-full sm:w-64" aria-label="Insert a template">
            <SelectValue placeholder="Insert a template..." />
          </SelectTrigger>
          <SelectContent>
            {CLINICAL_NOTE_TEMPLATES.map((template) => (
              <SelectItem key={template.id} value={template.id}>
                {template.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
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

      <div className="space-y-4">
        {NARRATIVE_FIELDS.map((field) => (
          <RichTextField key={field.name} control={control} name={field.name} label={field.label} />
        ))}
      </div>
      <div className="space-y-4">
        {ASSESSMENT_PLAN_FIELDS.map((field) => (
          <RichTextField key={field.name} control={control} name={field.name} label={field.label} />
        ))}
      </div>
    </div>
  );
}
