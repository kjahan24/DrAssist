import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  NOTIFICATION_FREQUENCY_OPTIONS,
  type ChannelPreference,
  type NotificationFrequency,
} from "@/lib/mock/notifications";

interface NotificationPreferenceCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  preference: ChannelPreference;
  onChange: (preference: ChannelPreference) => void;
}

// One channel's settings (In-App/Email/SMS/Push) — Enable/Disable plus a
// Frequency select that's only meaningful while enabled.
export function NotificationPreferenceCard({
  icon: Icon,
  title,
  description,
  preference,
  onChange,
}: NotificationPreferenceCardProps) {
  const inputId = `channel-${title.toLowerCase().replace(/\s+/g, "-")}`;

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 pt-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-muted">
            <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
          </div>
          <div>
            <label htmlFor={inputId} className="text-sm font-medium">
              {title}
            </label>
            <p className="text-xs text-muted-foreground">{description}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Select
            value={preference.frequency}
            disabled={!preference.enabled}
            onValueChange={(value) =>
              onChange({ ...preference, frequency: value as NotificationFrequency })
            }
          >
            <SelectTrigger className="w-40" aria-label={`${title} frequency`}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {NOTIFICATION_FREQUENCY_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Switch
            id={inputId}
            checked={preference.enabled}
            onCheckedChange={(checked) => onChange({ ...preference, enabled: checked })}
          />
        </div>
      </CardContent>
    </Card>
  );
}
