"""Unit tests for `app.core.security.password_hashing`."""

from app.core.security.password_hashing import hash_password, needs_rehash, verify_password


class TestHashAndVerify:
    def test_correct_password_verifies(self) -> None:
        hashed = hash_password("correct horse battery staple")
        assert verify_password("correct horse battery staple", hashed) is True

    def test_wrong_password_does_not_verify(self) -> None:
        hashed = hash_password("correct horse battery staple")
        assert verify_password("wrong password", hashed) is False

    def test_hash_is_not_the_plaintext(self) -> None:
        plaintext = "a-secret-password"
        assert hash_password(plaintext) != plaintext

    def test_hashing_the_same_password_twice_yields_different_hashes(self) -> None:
        # bcrypt salts each hash independently.
        assert hash_password("same-password") != hash_password("same-password")

    def test_hash_looks_like_bcrypt(self) -> None:
        hashed = hash_password("whatever")
        assert hashed.startswith(("$2a$", "$2b$", "$2y$"))


class TestNeedsRehash:
    def test_freshly_hashed_password_does_not_need_rehash(self) -> None:
        hashed = hash_password("whatever")
        assert needs_rehash(hashed) is False
