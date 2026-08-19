"""Application services for the Community Moderation module — 20 named
use cases from this task's own APPLICATION section, across 18 files:

Reports: `CreateReport`, `GetReport`+`ListReports` (one file,
`report_query_service.py`), `AssignReport`, `ResolveReport`,
`RejectReport`.

Moderation actions: `CreateModerationAction` (also the only way to record
a `RESTRICT` action — see its own docstring), `ReviewContent`,
`RemoveContent`, `RestoreContent`, `LockContent` (all five share one
resolve/authorize/state-lookup implementation — `_content_actions.py`);
`RestrictUser`, `SuspendUser` (also covers "Permanent ban where
authorized" — see its own docstring), `WarnUser` (all three share
`_user_restrictions.py`).

Doctor verification: `RequestDoctorVerification`,
`ApproveDoctorVerification`, `RejectDoctorVerification`,
`RevokeDoctorVerification`.

Status queries: `GetModerationStatus`+`GetVerificationStatus` (one file,
`status_query_service.py`).
"""
