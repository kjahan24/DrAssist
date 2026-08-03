"use client";

import { Bell, Mail, MessageSquare, Smartphone } from "lucide-react";
import { useState, type FormEvent } from "react";

import { LoadingButton } from "@/components/auth/loading-button";
import { SectionCard } from "@/components/dashboard/section-card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { NotificationPreferenceCard } from "@/features/notifications/components/notification-preference-card";
import type { ChannelPreference, NotificationPreferences } from "@/lib/mock/notifications";

interface NotificationSettingsFormProps {
  defaultValues: NotificationPreferences;
  onSubmit: (values: NotificationPreferences) => void;
  isSubmitting?: boolean;
}

// Every field here is a controlled Switch/Select/time-input with no text
// validation rules to enforce (no min/max, no required-string checks) —
// unlike every other form in this app, react-hook-form/zod wouldn't earn
// its keep, so this is plain local state instead.
export function NotificationSettingsForm({
  defaultValues,
  onSubmit,
  isSubmitting,
}: NotificationSettingsFormProps) {
  const [values, setValues] = useState<NotificationPreferences>(defaultValues);

  function updateChannel(
    channel: keyof NotificationPreferences["channels"],
    preference: ChannelPreference,
  ) {
    setValues((current) => ({
      ...current,
      channels: { ...current.channels, [channel]: preference },
    }));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit(values);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <SectionCard title="Channels" description="Choose how you want to be notified.">
        <div className="space-y-3">
          <NotificationPreferenceCard
            icon={Bell}
            title="In-App"
            description="Notifications shown in your Notifications Center."
            preference={values.channels.in_app}
            onChange={(preference) => updateChannel("in_app", preference)}
          />
          <NotificationPreferenceCard
            icon={Mail}
            title="Email"
            description="Notifications sent to your account email."
            preference={values.channels.email}
            onChange={(preference) => updateChannel("email", preference)}
          />
          <div className="relative">
            <Badge variant="secondary" className="absolute right-3 top-3 z-10">
              UI Preview
            </Badge>
            <NotificationPreferenceCard
              icon={MessageSquare}
              title="SMS"
              description="Text message notifications (not yet connected to a provider)."
              preference={values.channels.sms}
              onChange={(preference) => updateChannel("sms", preference)}
            />
          </div>
          <div className="relative">
            <Badge variant="secondary" className="absolute right-3 top-3 z-10">
              UI Preview
            </Badge>
            <NotificationPreferenceCard
              icon={Smartphone}
              title="Push"
              description="Mobile push notifications (not yet connected to a provider)."
              preference={values.channels.push}
              onChange={(preference) => updateChannel("push", preference)}
            />
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="Quiet Hours"
        description="Pause non-critical notifications during a set window each day."
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3 rounded-md border p-3">
            <div>
              <Label htmlFor="quiet-hours-enabled" className="text-sm font-medium">
                Enable Quiet Hours
              </Label>
              <p className="text-xs text-muted-foreground">
                Only critical notifications will be delivered during this window.
              </p>
            </div>
            <Switch
              id="quiet-hours-enabled"
              checked={values.quiet_hours_enabled}
              onCheckedChange={(checked) =>
                setValues((current) => ({ ...current, quiet_hours_enabled: checked }))
              }
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="quiet-hours-start">Starts At</Label>
              <Input
                id="quiet-hours-start"
                type="time"
                disabled={!values.quiet_hours_enabled}
                value={values.quiet_hours_start}
                onChange={(event) =>
                  setValues((current) => ({ ...current, quiet_hours_start: event.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="quiet-hours-end">Ends At</Label>
              <Input
                id="quiet-hours-end"
                type="time"
                disabled={!values.quiet_hours_enabled}
                value={values.quiet_hours_end}
                onChange={(event) =>
                  setValues((current) => ({ ...current, quiet_hours_end: event.target.value }))
                }
              />
            </div>
          </div>

          <div className="flex items-center justify-between gap-3 rounded-md border p-3">
            <div>
              <Label htmlFor="emergency-override" className="text-sm font-medium">
                Emergency Override
              </Label>
              <p className="text-xs text-muted-foreground">
                Always deliver critical-priority notifications, even during Quiet Hours.
              </p>
            </div>
            <Switch
              id="emergency-override"
              checked={values.emergency_override}
              onCheckedChange={(checked) =>
                setValues((current) => ({ ...current, emergency_override: checked }))
              }
            />
          </div>
        </div>
      </SectionCard>

      <div className="flex justify-end gap-3">
        <LoadingButton type="submit" loading={isSubmitting}>
          Save Changes
        </LoadingButton>
      </div>
    </form>
  );
}
