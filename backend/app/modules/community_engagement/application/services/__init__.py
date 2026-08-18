"""Application services for the Community Engagement module.

Fifteen use cases named in this task's own APPLICATION section
(`CastVote`/`RemoveVote`/`GetVoteStatus`/`GetVoteCounts`/`SaveContent`/
`UnsaveContent`/`ListSavedContent`/`FollowTopic`/`UnfollowTopic`/
`FollowCommunity`/`UnfollowCommunity`/`FollowDoctor`/`UnfollowDoctor`/
`ListFollowers`/`ListFollowing`) map to fourteen files here (`GetVoteStatus`
and `GetVoteCounts` share `vote_query_service.py`, the same "pair related
query services in one file" precedent
`app.modules.community_answers.application.services.answer_query_service`
already establishes for `GetAnswerService`/`ListAnswersService`).

"Do not duplicate voting logic for every content type" (this task's own
TARGET TYPES section) shows up twice: `_target_resolution.py` is the one
shared four-way (Post/Question/Answer/Comment) target lookup both
`CastVoteService` and `SaveContentService` depend on, and
`ListFollowersService`/`ListFollowingService` are each one service
dispatching across all three follower repositories
(`topic_followers`/`community_followers`/`doctor_followers`) by
`FollowTargetType`, rather than six near-duplicate listing services.
"""
