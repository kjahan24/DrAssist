"use client";

import { Laptop, ShieldCheck, ShieldOff } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SettingsEmptyState } from "@/features/settings/components/settings-empty-state";
import { formatDateTime, formatRelativeTime } from "@/lib/format";
import type { UserSessionItem } from "@/lib/mock/settings";

type SessionTableMode = "active" | "history" | "trusted";

interface SessionTableProps {
  sessions: UserSessionItem[];
  mode: SessionTableMode;
  isLoading?: boolean;
  onRevoke?: (sessionId: string) => void;
  onToggleTrusted?: (sessionId: string, trusted: boolean) => void;
}

function getSessionStatusLabel(session: UserSessionItem): string {
  if (session.revoked_at) return "Revoked";
  if (new Date(session.expires_at).getTime() <= Date.now()) return "Expired";
  return "Active";
}

const EMPTY_COPY: Record<SessionTableMode, { title: string; description: string }> = {
  active: { title: "No active sessions", description: "You're not signed in anywhere else." },
  history: { title: "No login history", description: "Sign-in activity will appear here." },
  trusted: { title: "No trusted devices", description: "Mark a device as trusted to see it here." },
};

// Reused for all three session views this task asks for (Active
// Sessions/Login History/Trusted Devices) — all three read the same
// underlying `UserSession` rows, just filtered differently (see
// `lib/mock/settings.ts`'s own docstring), so one table handles all
// three via `mode`. Desktop shows a real `<table>`; mobile falls back to
// a card stack, same responsive split as every other list in this app.
export function SessionTable({
  sessions,
  mode,
  isLoading,
  onRevoke,
  onToggleTrusted,
}: SessionTableProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 2 }).map((_, index) => (
          <Skeleton key={index} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (sessions.length === 0) {
    return <SettingsEmptyState icon={Laptop} {...EMPTY_COPY[mode]} />;
  }

  return (
    <>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="py-2 pr-4 font-medium">Device</th>
              <th className="py-2 pr-4 font-medium">Location</th>
              <th className="py-2 pr-4 font-medium">IP Address</th>
              <th className="py-2 pr-4 font-medium">
                {mode === "history" ? "Signed In" : "Last Active"}
              </th>
              <th className="py-2 pr-4 font-medium">Status</th>
              <th className="py-2 text-right font-medium">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((session) => (
              <tr key={session.session_id} className="border-b last:border-0">
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2">
                    <Laptop className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                    <span>{session.device_label}</span>
                    {session.is_current_session && <Badge variant="outline">This Device</Badge>}
                  </div>
                </td>
                <td className="py-3 pr-4 text-muted-foreground">{session.location}</td>
                <td className="py-3 pr-4 text-muted-foreground">{session.ip_address}</td>
                <td className="py-3 pr-4 text-muted-foreground">
                  {mode === "history"
                    ? formatDateTime(session.issued_at)
                    : session.last_used_at
                      ? formatRelativeTime(session.last_used_at)
                      : "—"}
                </td>
                <td className="py-3 pr-4">
                  <Badge variant={session.revoked_at ? "secondary" : "default"}>
                    {getSessionStatusLabel(session)}
                  </Badge>
                </td>
                <td className="py-3 text-right">
                  {mode === "trusted" && onToggleTrusted && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onToggleTrusted(session.session_id, false)}
                    >
                      <ShieldOff className="size-4" />
                      Remove Trust
                    </Button>
                  )}
                  {mode === "active" && !session.is_current_session && onRevoke && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onRevoke(session.session_id)}
                    >
                      Revoke
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid gap-3 md:hidden">
        {sessions.map((session) => (
          <div key={session.session_id} className="space-y-2 rounded-lg border p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Laptop className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <span className="text-sm font-medium">{session.device_label}</span>
              </div>
              <Badge variant={session.revoked_at ? "secondary" : "default"}>
                {getSessionStatusLabel(session)}
              </Badge>
            </div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <div>
                <dt>Location</dt>
                <dd className="text-foreground">{session.location}</dd>
              </div>
              <div>
                <dt>IP Address</dt>
                <dd className="text-foreground">{session.ip_address}</dd>
              </div>
              <div className="col-span-2">
                <dt>{mode === "history" ? "Signed In" : "Last Active"}</dt>
                <dd className="text-foreground">
                  {mode === "history"
                    ? formatDateTime(session.issued_at)
                    : session.last_used_at
                      ? formatRelativeTime(session.last_used_at)
                      : "—"}
                </dd>
              </div>
            </dl>
            <div className="flex flex-wrap gap-2 pt-1">
              {session.is_current_session && (
                <Badge variant="outline">
                  <ShieldCheck className="size-3" aria-hidden="true" />
                  This Device
                </Badge>
              )}
              {mode === "trusted" && onToggleTrusted && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onToggleTrusted(session.session_id, false)}
                >
                  Remove Trust
                </Button>
              )}
              {mode === "active" && !session.is_current_session && onRevoke && (
                <Button variant="outline" size="sm" onClick={() => onRevoke(session.session_id)}>
                  Revoke
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
