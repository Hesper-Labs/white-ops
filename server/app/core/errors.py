"""Structured error codes and exception classes for enterprise error handling."""

from enum import Enum
from typing import Any

from fastapi import HTTPException


class ErrorCode(str, Enum):
    """Structured error codes following domain:category:detail pattern."""

    # Authentication
    AUTH_INVALID_CREDENTIALS = "AUTH_001"
    AUTH_TOKEN_EXPIRED = "AUTH_002"
    AUTH_TOKEN_REVOKED = "AUTH_003"
    AUTH_INVALID_TOKEN = "AUTH_004"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_005"
    AUTH_ACCOUNT_LOCKED = "AUTH_006"
    AUTH_ACCOUNT_DISABLED = "AUTH_007"
    AUTH_MFA_REQUIRED = "AUTH_008"
    AUTH_MFA_INVALID_CODE = "AUTH_009"
    AUTH_REFRESH_TOKEN_INVALID = "AUTH_010"
    AUTH_PASSWORD_TOO_WEAK = "AUTH_011"
    AUTH_PASSWORD_REUSED = "AUTH_012"

    # Resources
    RESOURCE_NOT_FOUND = "RES_001"
    RESOURCE_ALREADY_EXISTS = "RES_002"
    RESOURCE_CONFLICT = "RES_003"
    RESOURCE_DELETED = "RES_004"

    # Agents
    AGENT_NOT_FOUND = "AGT_001"
    AGENT_ALREADY_RUNNING = "AGT_002"
    AGENT_OFFLINE = "AGT_003"
    AGENT_AT_CAPACITY = "AGT_004"
    AGENT_TOOL_MISMATCH = "AGT_005"

    # Tasks
    TASK_NOT_FOUND = "TSK_001"
    TASK_ALREADY_COMPLETED = "TSK_002"
    TASK_CANNOT_CANCEL = "TSK_003"
    TASK_MAX_RETRIES = "TSK_004"
    TASK_ASSIGNMENT_FAILED = "TSK_005"

    # Workers
    WORKER_NOT_FOUND = "WRK_001"
    WORKER_NOT_APPROVED = "WRK_002"
    WORKER_OFFLINE = "WRK_003"

    # Validation
    VALIDATION_ERROR = "VAL_001"
    VALIDATION_FIELD_REQUIRED = "VAL_002"
    VALIDATION_FIELD_INVALID = "VAL_003"

    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_001"

    # External Services
    SERVICE_UNAVAILABLE = "SVC_001"
    SERVICE_TIMEOUT = "SVC_002"
    SERVICE_CIRCUIT_OPEN = "SVC_003"

    # Database
    DATABASE_ERROR = "DB_001"
    DATABASE_CONSTRAINT_VIOLATION = "DB_002"

    # File Storage
    STORAGE_UPLOAD_FAILED = "STG_001"
    STORAGE_FILE_NOT_FOUND = "STG_002"
    STORAGE_QUOTA_EXCEEDED = "STG_003"

    # Secrets
    SECRET_NOT_FOUND = "SEC_001"
    SECRET_DECRYPTION_FAILED = "SEC_002"
    SECRET_EXPIRED = "SEC_003"

    # Workflow
    WORKFLOW_NOT_FOUND = "WFL_001"
    WORKFLOW_STEP_FAILED = "WFL_002"
    WORKFLOW_CYCLE_DETECTED = "WFL_003"

    # General
    INTERNAL_ERROR = "INT_001"
    NOT_IMPLEMENTED = "INT_002"
    CONFIGURATION_ERROR = "INT_003"


class AppException(HTTPException):
    """Application exception with structured error code."""

    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(
            status_code=status_code,
            detail={
                "error_code": error_code.value,
                "error_name": error_code.name,
                "message": message,
                "details": self.details,
            },
        )


# Convenience factory functions
def not_found(resource: str, resource_id: str | None = None) -> AppException:
    msg = f"{resource} not found"
    if resource_id:
        msg = f"{resource} '{resource_id}' not found"
    return AppException(404, ErrorCode.RESOURCE_NOT_FOUND, msg)


def forbidden(message: str = "Insufficient permissions") -> AppException:
    return AppException(403, ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS, message)


def unauthorized(
    error_code: ErrorCode = ErrorCode.AUTH_INVALID_TOKEN,
    message: str = "Authentication required",
) -> AppException:
    return AppException(401, error_code, message)


def bad_request(
    error_code: ErrorCode = ErrorCode.VALIDATION_ERROR,
    message: str = "Invalid request",
    details: dict[str, Any] | None = None,
) -> AppException:
    return AppException(400, error_code, message, details)


def conflict(message: str = "Resource conflict") -> AppException:
    return AppException(409, ErrorCode.RESOURCE_CONFLICT, message)


def service_unavailable(service: str, message: str = "") -> AppException:
    return AppException(
        503,
        ErrorCode.SERVICE_UNAVAILABLE,
        message or f"Service '{service}' is currently unavailable",
        {"service": service},
    )


def rate_limited(retry_after: int = 60) -> AppException:
    return AppException(
        429,
        ErrorCode.RATE_LIMIT_EXCEEDED,
        f"Rate limit exceeded. Retry after {retry_after} seconds.",
        {"retry_after": retry_after},
    )
