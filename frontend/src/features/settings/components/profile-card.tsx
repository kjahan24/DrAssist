import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { SettingsSection } from "@/features/settings/components/settings-section";
import { formatDate } from "@/lib/format";
import type { DoctorProfile } from "@/lib/mock/profile";
import { getInitials } from "@/lib/utils";

// The read-only view of the current user's profile — `/dashboard/profile`
// shows this by default, switching to `ProfileForm` when "Edit Profile"
// is pressed (see `ProfileContent`).
export function ProfileCard({ profile }: { profile: DoctorProfile }) {
  return (
    <SettingsSection title="Profile">
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Avatar className="size-20">
            {profile.avatar_url && <AvatarImage src={profile.avatar_url} alt="" />}
            <AvatarFallback className="text-lg">{getInitials(profile.full_name)}</AvatarFallback>
          </Avatar>
          <div>
            <p className="text-lg font-semibold">{profile.full_name}</p>
            <p className="text-sm text-muted-foreground">{profile.professional_title}</p>
          </div>
        </div>

        <dl className="grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm text-muted-foreground">Specialization</dt>
            <dd className="text-sm font-medium">{profile.specialization_name}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">License Number</dt>
            <dd className="text-sm font-medium">{profile.license_number}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Organization</dt>
            <dd className="text-sm font-medium">{profile.organization_name}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Joined</dt>
            <dd className="text-sm font-medium">{formatDate(profile.joining_date)}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Email</dt>
            <dd className="text-sm font-medium">{profile.email}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Phone</dt>
            <dd className="text-sm font-medium">{profile.phone}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-sm text-muted-foreground">Address</dt>
            <dd className="text-sm font-medium">{profile.address}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-sm text-muted-foreground">Biography</dt>
            <dd className="text-sm">{profile.biography}</dd>
          </div>
        </dl>
      </div>
    </SettingsSection>
  );
}
