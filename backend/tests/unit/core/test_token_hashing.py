"""Unit tests for `app.core.security.token_hashing`."""

from app.core.security.token_hashing import generate_raw_refresh_token, hash_refresh_token


class TestGenerateRawRefreshToken:
    def test_generates_a_nonempty_string(self) -> None:
        assert len(generate_raw_refresh_token()) > 20

    def test_successive_calls_produce_different_values(self) -> None:
        assert generate_raw_refresh_token() != generate_raw_refresh_token()


class TestHashRefreshToken:
    def test_same_input_produces_the_same_hash(self) -> None:
        raw = generate_raw_refresh_token()
        assert hash_refresh_token(raw) == hash_refresh_token(raw)

    def test_different_inputs_produce_different_hashes(self) -> None:
        assert hash_refresh_token("token-a") != hash_refresh_token("token-b")

    def test_hash_is_not_the_raw_value(self) -> None:
        raw = generate_raw_refresh_token()
        assert hash_refresh_token(raw) != raw

    def test_hash_is_a_64_character_hex_digest(self) -> None:
        digest = hash_refresh_token("anything")
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)
