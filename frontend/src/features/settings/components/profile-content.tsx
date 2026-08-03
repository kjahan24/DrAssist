"use client";

import { Pencil } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { Button } from "@/components/ui/button";
import { ProfileCard } from "@/features/settings/components/profile-card";
import { ProfileForm } from "@/features/settings/components/profile-form";
import {
  useProfile,
  useUpdateAvatar,
  useUpdateProfile,
} from "@/features/settings/hooks/use-profile";
import { profileToFormInput, type ProfileFormInput } from "@/lib/mock/profile";

export function ProfileContent() {
  const { data: profile, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();
  const updateAvatar = useUpdateAvatar();
  const [isEditing, setIsEditing] = useState(false);

  if (isLoading || !profile) {
    return <PageSkeleton title="Profile" />;
  }

  function handleSubmit(values: ProfileFormInput) {
    updateProfile.mutate(values, {
      onSuccess: () => {
        toast.success("Profile updated.");
        setIsEditing(false);
      },
    });
  }

  function handleAvatarChange(avatarUrl: string) {
    updateAvatar.mutate(avatarUrl);
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title="Profile"
        description="Your public professional profile."
        actions={
          !isEditing && (
            <Button onClick={() => setIsEditing(true)}>
              <Pencil className="size-4" />
              Edit Profile
            </Button>
          )
        }
      />

      {isEditing ? (
        <ProfileForm
          profile={profile}
          defaultValues={profileToFormInput(profile)}
          onSubmit={handleSubmit}
          onAvatarChange={handleAvatarChange}
          onCancel={() => setIsEditing(false)}
          isSubmitting={updateProfile.isPending}
        />
      ) : (
        <ProfileCard profile={profile} />
      )}
    </div>
  );
}
