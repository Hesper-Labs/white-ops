"""Secrets vault service - encrypted secret storage with rotation and auditing."""

import os
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.secret import Secret
from app.services.audit import log_action

logger = structlog.get_logger()


class VaultService:
    """Manages encrypted secrets with audit logging, rotation, and expiry tracking."""

    def __init__(self):
        master_key = os.getenv("VAULT_MASTER_KEY", "")
        if not master_key:
            # In production, refuse to start without a master key
            app_env = os.getenv("APP_ENV", "development")
            if app_env in ("production", "staging"):
                raise RuntimeError(
                    "VAULT_MASTER_KEY is required in production/staging. "
                    "Generate with: python -c 'from cryptography.fernet "
                    "import Fernet; print(Fernet.generate_key().decode())'"
                )
            master_key = Fernet.generate_key().decode()
            logger.warning(
                "vault_ephemeral_key",
                msg="Using ephemeral key - secrets will be lost on restart. "
                    "Set VAULT_MASTER_KEY for persistence.",
            )
        key = master_key if isinstance(master_key, bytes) else master_key.encode()
        try:
            self._fernet = Fernet(key)
        except Exception as exc:
            logger.error("vault_invalid_master_key", error=str(exc))
            raise RuntimeError(f"Invalid VAULT_MASTER_KEY format: {exc}") from exc

    # ------------------------------------------------------------------
    # Encryption helpers
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string and return the ciphertext as a UTF-8 string."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a ciphertext string and return the original plaintext."""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            logger.error("vault_decrypt_failed", msg="Invalid token or wrong key")
            raise ValueError(
                "Failed to decrypt secret - invalid token or wrong master key"
            ) from None
        except Exception as exc:
            logger.error("vault_decrypt_error", error=str(exc), error_type=type(exc).__name__)
            raise ValueError(f"Failed to decrypt secret: {exc}") from exc

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    async def store_secret(
        self,
        db: AsyncSession,
        name: str,
        value: str,
        category: str,
        description: str | None = None,
        created_by: uuid.UUID | None = None,
        expires_at: datetime | None = None,
    ) -> Secret:
        """Encrypt and store a new secret."""
        log = logger.bind(secret_name=name, category=category)

        # Check for duplicate name
        existing = await db.execute(
            select(Secret).where(Secret.name == name, Secret.is_deleted.is_(False))
        )
        if existing.scalar_one_or_none():
            log.warning("vault_secret_exists")
            raise ValueError(f"Secret with name '{name}' already exists")

        encrypted = self.encrypt(value)
        secret = Secret(
            name=name,
            encrypted_value=encrypted,
            category=category,
            description=description,
            created_by=created_by,
            expires_at=expires_at,
            version=1,
        )
        db.add(secret)
        await db.flush()

        await log_action(
            db,
            action="secret_created",
            resource_type="secret",
            resource_id=secret.id,
            actor_type="user",
            actor_id=created_by,
            details=f"Secret '{name}' created in category '{category}'",
        )

        log.info("vault_secret_stored", secret_id=str(secret.id))
        return secret

    async def get_secret(
        self,
        db: AsyncSession,
        secret_id: uuid.UUID,
        audit_user_id: uuid.UUID | None = None,
    ) -> dict:
        """Retrieve and decrypt a secret, recording an audit log entry."""
        log = logger.bind(secret_id=str(secret_id))

        result = await db.execute(
            select(Secret).where(Secret.id == secret_id, Secret.is_deleted.is_(False))
        )
        secret = result.scalar_one_or_none()
        if not secret:
            log.warning("vault_secret_not_found")
            raise ValueError("Secret not found")

        decrypted = self.decrypt(secret.encrypted_value)

        # Audit the access
        await log_action(
            db,
            action="secret_accessed",
            resource_type="secret",
            resource_id=secret.id,
            actor_type="user",
            actor_id=audit_user_id,
            details=f"Secret '{secret.name}' accessed",
        )

        log.info("vault_secret_accessed")
        return {
            "id": str(secret.id),
            "name": secret.name,
            "value": decrypted,
            "category": secret.category,
            "description": secret.description,
            "version": secret.version,
            "expires_at": secret.expires_at.isoformat() if secret.expires_at else None,
            "created_at": secret.created_at.isoformat(),
            "updated_at": secret.updated_at.isoformat(),
        }

    async def list_secrets(
        self,
        db: AsyncSession,
        category: str | None = None,
    ) -> list[dict]:
        """List secret metadata without decrypted values."""
        query = select(Secret).where(Secret.is_deleted.is_(False))
        if category:
            query = query.where(Secret.category == category)
        query = query.order_by(Secret.created_at.desc())

        result = await db.execute(query)
        secrets = result.scalars().all()

        return [
            {
                "id": str(s.id),
                "name": s.name,
                "category": s.category,
                "description": s.description,
                "version": s.version,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                "rotated_at": s.rotated_at.isoformat() if s.rotated_at else None,
                "created_at": s.created_at.isoformat(),
            }
            for s in secrets
        ]

    async def rotate_secret(
        self,
        db: AsyncSession,
        secret_id: uuid.UUID,
        new_value: str,
        rotated_by: uuid.UUID | None = None,
    ) -> Secret:
        """Rotate a secret to a new value, incrementing its version."""
        log = logger.bind(secret_id=str(secret_id))

        result = await db.execute(
            select(Secret).where(Secret.id == secret_id, Secret.is_deleted.is_(False))
        )
        secret = result.scalar_one_or_none()
        if not secret:
            log.warning("vault_secret_not_found")
            raise ValueError("Secret not found")

        secret.encrypted_value = self.encrypt(new_value)
        secret.version += 1
        secret.rotated_at = datetime.now(UTC)
        secret.rotated_by = rotated_by
        await db.flush()

        await log_action(
            db,
            action="secret_rotated",
            resource_type="secret",
            resource_id=secret.id,
            actor_type="user",
            actor_id=rotated_by,
            details=f"Secret '{secret.name}' rotated to version {secret.version}",
        )

        log.info("vault_secret_rotated", version=secret.version)
        return secret

    async def delete_secret(self, db: AsyncSession, secret_id: uuid.UUID) -> bool:
        """Soft-delete a secret."""
        log = logger.bind(secret_id=str(secret_id))

        result = await db.execute(
            select(Secret).where(Secret.id == secret_id, Secret.is_deleted.is_(False))
        )
        secret = result.scalar_one_or_none()
        if not secret:
            log.warning("vault_secret_not_found")
            return False

        secret.soft_delete()
        await db.flush()

        await log_action(
            db,
            action="secret_deleted",
            resource_type="secret",
            resource_id=secret.id,
            details=f"Secret '{secret.name}' deleted",
        )

        log.info("vault_secret_deleted")
        return True

    async def check_expiring(
        self,
        db: AsyncSession,
        days: int = 7,
    ) -> list[dict]:
        """Find secrets that will expire within the given number of days."""
        now = datetime.now(UTC)
        threshold = now + timedelta(days=days)

        result = await db.execute(
            select(Secret).where(
                Secret.is_deleted.is_(False),
                Secret.expires_at.isnot(None),
                Secret.expires_at <= threshold,
                Secret.expires_at > now,
            ).order_by(Secret.expires_at.asc())
        )
        secrets = result.scalars().all()

        return [
            {
                "id": str(s.id),
                "name": s.name,
                "category": s.category,
                "expires_at": s.expires_at.isoformat(),
                "days_until_expiry": (s.expires_at - now).days,
                "version": s.version,
            }
            for s in secrets
        ]


vault_service = VaultService()
