import { PageHeader } from "@/components/dashboard/page-header";

import { ProfileDetails } from "./profile-details";

export const metadata = { title: "Profile" };

export default function ProfilePage() {
  return (
    <div className="max-w-2xl space-y-6">
      <PageHeader title="Profile" description="Your account information." />
      <ProfileDetails />
    </div>
  );
}
