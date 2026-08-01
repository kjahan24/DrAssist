import { format, formatDistanceToNow } from "date-fns";

// Shared, cross-feature formatting helpers. All backend timestamps are
// ISO 8601 strings (Pydantic's default `datetime` JSON encoding), so every
// function here accepts `string | Date` and normalizes internally.
function toDate(value: string | Date): Date {
  return typeof value === "string" ? new Date(value) : value;
}

export function formatDate(value: string | Date, pattern = "MMM d, yyyy"): string {
  return format(toDate(value), pattern);
}

export function formatDateTime(value: string | Date): string {
  return format(toDate(value), "MMM d, yyyy 'at' h:mm a");
}

export function formatRelativeTime(value: string | Date): string {
  return formatDistanceToNow(toDate(value), { addSuffix: true });
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;
  return `${exponent === 0 ? value : value.toFixed(1)} ${units[exponent]}`;
}
