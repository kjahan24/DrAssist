"use client";

import { Bell, Calendar, Clock, LayoutDashboard, Palette, Rocket } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PreferenceCard } from "@/features/settings/components/preference-card";
import { SettingsSection } from "@/features/settings/components/settings-section";
import { ThemeSelector } from "@/features/settings/components/theme-selector";
import {
  useUpdateUserPreferences,
  useUserPreferences,
} from "@/features/settings/hooks/use-preferences";
import {
  DASHBOARD_LAYOUT_OPTIONS,
  DATE_FORMAT_OPTIONS,
  DEFAULT_LANDING_PAGE_OPTIONS,
  TIME_FORMAT_OPTIONS,
  type UserPreferences,
} from "@/lib/mock/settings";

export function PreferencesContent() {
  const { data: preferences, isLoading } = useUserPreferences();
  const updatePreferences = useUpdateUserPreferences();
  const [values, setValues] = useState<UserPreferences | null>(null);

  useEffect(() => {
    if (preferences) setValues(preferences);
  }, [preferences]);

  if (isLoading || !values) {
    return <PageSkeleton title="Preferences" />;
  }

  function handleSave() {
    if (!values) return;
    updatePreferences.mutate(values, {
      onSuccess: () => toast.success("Preferences saved."),
    });
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title="Preferences"
        description="Customize how DrAssist looks and behaves for you."
      />

      <SettingsSection title="Appearance">
        <PreferenceCard
          icon={Palette}
          title="Theme"
          description="Switch between light, dark, or match your system."
          control={<ThemeSelector />}
        />
      </SettingsSection>

      <SettingsSection
        title="Formatting"
        description="Applied across dates and times shown in the app."
      >
        <div className="space-y-3">
          <PreferenceCard
            icon={Calendar}
            title="Date Format"
            description="How dates are displayed."
            control={
              <Select
                value={values.date_format}
                onValueChange={(value) =>
                  setValues((current) =>
                    current
                      ? { ...current, date_format: value as UserPreferences["date_format"] }
                      : current,
                  )
                }
              >
                <SelectTrigger aria-label="Date format">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DATE_FORMAT_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            }
          />
          <PreferenceCard
            icon={Clock}
            title="Time Format"
            description="How times are displayed."
            control={
              <Select
                value={values.time_format}
                onValueChange={(value) =>
                  setValues((current) =>
                    current
                      ? { ...current, time_format: value as UserPreferences["time_format"] }
                      : current,
                  )
                }
              >
                <SelectTrigger aria-label="Time format">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIME_FORMAT_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            }
          />
        </div>
      </SettingsSection>

      <SettingsSection
        title="Dashboard"
        description="How the dashboard is laid out when you sign in."
      >
        <div className="space-y-3">
          <PreferenceCard
            icon={LayoutDashboard}
            title="Dashboard Layout"
            description="Adjust spacing density across tables and lists."
            control={
              <Select
                value={values.dashboard_layout}
                onValueChange={(value) =>
                  setValues((current) =>
                    current
                      ? {
                          ...current,
                          dashboard_layout: value as UserPreferences["dashboard_layout"],
                        }
                      : current,
                  )
                }
              >
                <SelectTrigger aria-label="Dashboard layout">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DASHBOARD_LAYOUT_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            }
          />
          <PreferenceCard
            icon={Rocket}
            title="Default Landing Page"
            description="The page you see right after signing in."
            control={
              <Select
                value={values.default_landing_page}
                onValueChange={(value) =>
                  setValues((current) =>
                    current
                      ? {
                          ...current,
                          default_landing_page: value as UserPreferences["default_landing_page"],
                        }
                      : current,
                  )
                }
              >
                <SelectTrigger aria-label="Default landing page">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DEFAULT_LANDING_PAGE_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            }
          />
        </div>
      </SettingsSection>

      <SettingsSection title="Notifications">
        <PreferenceCard
          icon={Bell}
          title="Notification Preferences"
          description="Manage channels, quiet hours, and delivery frequency."
          control={
            <Button variant="outline" className="w-full" asChild>
              <Link href="/dashboard/notifications/settings">Manage</Link>
            </Button>
          }
        />
      </SettingsSection>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={updatePreferences.isPending}>
          Save Changes
        </Button>
      </div>
    </div>
  );
}
