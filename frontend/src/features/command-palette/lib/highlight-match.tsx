import { Fragment } from "react";

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Wraps the first case-insensitive match of `query` inside `text` in a
// `<mark>` — the "highlighted match" this task's own Search Results
// display asks for. Returns `text` untouched when there's nothing to
// highlight, so callers can use this unconditionally.
export function HighlightMatch({ text, query }: { text: string; query: string }) {
  const needle = query.trim();
  if (needle.length === 0) return <>{text}</>;

  const pattern = new RegExp(`(${escapeRegExp(needle)})`, "ig");
  const parts = text.split(pattern);
  if (parts.length === 1) return <>{text}</>;

  return (
    <>
      {parts.map((part, index) =>
        part.toLowerCase() === needle.toLowerCase() ? (
          <mark key={index} className="rounded-sm bg-primary/20 text-inherit">
            {part}
          </mark>
        ) : (
          <Fragment key={index}>{part}</Fragment>
        ),
      )}
    </>
  );
}
