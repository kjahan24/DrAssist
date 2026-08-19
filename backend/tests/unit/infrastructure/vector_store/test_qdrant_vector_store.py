"""Unit test for `QdrantVectorStore`'s point-id translation — pure logic,
no network. The round-trip against a real Qdrant instance (including the
regression case that first caught this as a bug) lives in
`tests/integration/modules/community_ai/test_qdrant_vector_store.py`.
"""

import uuid

from app.infrastructure.vector_store.qdrant_vector_store import _point_id


class TestPointId:
    def test_is_deterministic_for_the_same_input(self) -> None:
        assert _point_id("post:1234") == _point_id("post:1234")

    def test_differs_for_different_inputs(self) -> None:
        assert _point_id("post:1234") != _point_id("post:5678")

    def test_always_produces_a_valid_uuid_string(self) -> None:
        for candidate in ("post:1234", "not-a-uuid-at-all", "42", str(uuid.uuid4())):
            uuid.UUID(_point_id(candidate))
