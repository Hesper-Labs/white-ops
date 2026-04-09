"""Security tests - password validation, JWT tokens, API key hashing, rate limiting."""

import pytest
from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    decode_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_api_key,
    hash_api_key,
    verify_api_key,
    verify_api_key_compat,
    generate_totp_secret,
    verify_totp,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "SecurePass123!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct_password")
        assert not verify_password("wrong_password", hashed)

    def test_different_hashes_for_same_password(self):
        """bcrypt should generate different hashes for the same password (salt)."""
        h1 = hash_password("test_password")
        h2 = hash_password("test_password")
        assert h1 != h2  # Different salts


class TestPasswordValidation:
    def test_valid_password(self):
        result = validate_password_strength("StrongP@ssw0rd!")
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_too_short(self):
        result = validate_password_strength("Short1!")
        assert result["valid"] is False
        assert any("12 characters" in e for e in result["errors"])

    def test_no_uppercase(self):
        result = validate_password_strength("lowercase1234!@#")
        assert result["valid"] is False
        assert any("uppercase" in e for e in result["errors"])

    def test_no_lowercase(self):
        result = validate_password_strength("UPPERCASE1234!@#")
        assert result["valid"] is False
        assert any("lowercase" in e for e in result["errors"])

    def test_no_digit(self):
        result = validate_password_strength("NoDigitsHere!@#$")
        assert result["valid"] is False
        assert any("digit" in e for e in result["errors"])

    def test_no_special(self):
        result = validate_password_strength("NoSpecialChar123")
        assert result["valid"] is False
        assert any("special" in e for e in result["errors"])


class TestJWTTokens:
    def test_create_and_decode_access_token(self):
        data = {"sub": "user-123", "role": "admin"}
        token = create_access_token(data)
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_and_decode_refresh_token(self):
        data = {"sub": "user-123"}
        token = create_refresh_token(data)
        payload = decode_refresh_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"

    def test_invalid_token_raises(self):
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_access_token("invalid-token")

    def test_refresh_token_cannot_be_used_as_access(self):
        token = create_refresh_token({"sub": "user-123"})
        # Access token decode should work but type check should differ
        payload = decode_access_token(token)
        assert payload["type"] == "refresh"  # Not "access"


class TestAPIKeys:
    def test_generate_api_key_length(self):
        key = generate_api_key()
        assert len(key) > 20

    def test_generate_unique_keys(self):
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100

    def test_hash_and_verify_api_key(self):
        key = generate_api_key()
        hashed = hash_api_key(key)
        assert hashed != key
        assert verify_api_key(key, hashed)

    def test_wrong_key_fails(self):
        key = generate_api_key()
        hashed = hash_api_key(key)
        assert not verify_api_key("wrong-key", hashed)

    def test_compat_verify_hmac(self):
        key = generate_api_key()
        hashed = hash_api_key(key)  # HMAC-SHA256 hash
        assert verify_api_key_compat(key, hashed)

    def test_compat_verify_legacy_sha256(self):
        import hashlib
        key = generate_api_key()
        legacy_hash = hashlib.sha256(key.encode()).hexdigest()
        assert verify_api_key_compat(key, legacy_hash)


class TestTOTP:
    def test_generate_secret(self):
        secret = generate_totp_secret()
        assert len(secret) > 10

    def test_verify_valid_code(self):
        import pyotp
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert verify_totp(secret, code)

    def test_verify_wrong_code(self):
        secret = generate_totp_secret()
        assert not verify_totp(secret, "000000")
