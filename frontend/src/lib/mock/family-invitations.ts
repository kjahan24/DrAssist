// Temporary frontend mock repository for Invitation Management
// (`/dashboard/family/invitations*`) — the invitation-lifecycle-flavored
// facet of the exact same underlying grants `lib/mock/family-members.ts`
// owns. There is only ever one in-memory array (defined once, in that
// file); this file adds no state of its own, only invitation-specific
// naming and the actions this task's "Invitation Management" section
// asks for (Create/Resend/Cancel) on top of it — the same
// "single source of truth, purpose-named wrappers" reasoning already
// used when `lib/mock/documents.ts` reuses lookups from sibling modules,
// just within one module's own pair of files this time.
//
// `cancelInvitation()` is `revokeFamilyMember()` under a different name:
// the real backend has exactly one use case for ending a grant early —
// `RevokeAccess`, `(Pending|Accepted) -> Revoked` — "cancelling" a
// pending invitation and "revoking" an accepted member's access are the
// same domain operation from two different pages' vocabulary, not two
// different behaviors.

import type { PaginatedResponse } from "@/types";
import {
  createFamilyAccessGrant,
  getFamilyMember,
  isFamilyAccessCancellable,
  listFamilyMembers,
  resendFamilyInvitation,
  revokeFamilyMember,
  type FamilyAccessHistoryEntry,
  type FamilyInviteInput,
  type FamilyMember,
  type FamilyMemberDetail,
  type FamilyMemberListParams,
} from "@/lib/mock/family-members";

export type {
  FamilyAccessHistoryEntry,
  FamilyMember,
  FamilyMemberDetail,
  FamilyInviteInput as CreateInvitationInput,
};
export type InvitationListParams = FamilyMemberListParams;

export { isFamilyAccessCancellable };

export function listInvitations(
  params: InvitationListParams = {},
): Promise<PaginatedResponse<FamilyMember>> {
  return listFamilyMembers(params);
}

export function getInvitation(familyAccessId: string): Promise<FamilyMemberDetail | null> {
  return getFamilyMember(familyAccessId);
}

export function createInvitation(input: FamilyInviteInput): Promise<FamilyMemberDetail> {
  return createFamilyAccessGrant(input);
}

export function resendInvitation(familyAccessId: string): Promise<FamilyMemberDetail> {
  return resendFamilyInvitation(familyAccessId);
}

export function cancelInvitation(familyAccessId: string): Promise<FamilyMemberDetail> {
  return revokeFamilyMember(familyAccessId);
}
