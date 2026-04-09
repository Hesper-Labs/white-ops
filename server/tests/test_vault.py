"""Vault service tests - encryption, key validation."""

import os
import pytest
from cryptography.fernet import Fernet

from app.services.vault import VaultService


class TestVaultEncryption:
    def setup_method(self):
        """Set a valid master key for testing."""
        self.test_key = Fernet.generate_key().decode()
        os.environ["VAULT_MASTER_KEY"] = self.test_key
        os.environ["APP_ENV"] = "test"

    def teardown_method(self):
        os.environ.pop("VAULT_MASTER_KEY", None)
        os.environ.pop("APP_ENV", None)

    def test_encrypt_decrypt_roundtrip(self):
        vault = VaultService()
        plaintext = "super-secret-api-key-12345"
        encrypted = vault.encrypt(plaintext)
        assert encrypted != plaintext
        decrypted = vault.decrypt(encrypted)
        assert decrypted == plaintext

    def test_different_encryptions_for_same_input(self):
        """Fernet produces different ciphertext each time (nonce)."""
        vault = VaultService()
        plaintext = "same-secret"
        e1 = vault.encrypt(plaintext)
        e2 = vault.encrypt(plaintext)
        assert e1 != e2

    def test_decrypt_with_wrong_key_fails(self):
        vault1 = VaultService()
        encrypted = vault1.encrypt("my-secret")

        os.environ["VAULT_MASTER_KEY"] = Fernet.generate_key().decode()
        vault2 = VaultService()
        with pytest.raises(ValueError, match="Failed to decrypt"):
            vault2.decrypt(encrypted)

    def test_decrypt_invalid_ciphertext_fails(self):
        vault = VaultService()
        with pytest.raises(ValueError, match="Failed to decrypt"):
            vault.decrypt("not-valid-ciphertext")

    def test_empty_plaintext(self):
        vault = VaultService()
        encrypted = vault.encrypt("")
        assert vault.decrypt(encrypted) == ""

    def test_unicode_plaintext(self):
        vault = VaultService()
        plaintext = "Sır: Türkçe karakter \u00f6zel!"
        encrypted = vault.encrypt(plaintext)
        assert vault.decrypt(encrypted) == plaintext


class TestVaultKeyValidation:
    def test_invalid_key_format_raises(self):
        os.environ["VAULT_MASTER_KEY"] = "not-a-valid-fernet-key"
        os.environ["APP_ENV"] = "test"
        with pytest.raises(RuntimeError, match="Invalid VAULT_MASTER_KEY"):
            VaultService()
        os.environ.pop("VAULT_MASTER_KEY", None)
        os.environ.pop("APP_ENV", None)

    def test_production_without_key_raises(self):
        os.environ.pop("VAULT_MASTER_KEY", None)
        os.environ["APP_ENV"] = "production"
        with pytest.raises(RuntimeError, match="VAULT_MASTER_KEY is required"):
            VaultService()
        os.environ.pop("APP_ENV", None)

    def test_development_without_key_warns(self):
        os.environ.pop("VAULT_MASTER_KEY", None)
        os.environ["APP_ENV"] = "development"
        # Should not raise, just warn
        vault = VaultService()
        assert vault is not None
        os.environ.pop("APP_ENV", None)
