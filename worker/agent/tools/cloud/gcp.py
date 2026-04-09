"""Google Cloud Platform tool - interact with GCP resources via REST API."""

import json
import os
from typing import Any

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
GCP_COMPUTE_URL = "https://compute.googleapis.com/compute/v1"
GCP_STORAGE_URL = "https://storage.googleapis.com"
GCP_STORAGE_API_URL = "https://storage.googleapis.com/storage/v1"


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


class GCPCloudTool(BaseTool):
    name = "gcp_cloud"
    description = (
        "Interact with Google Cloud Platform resources. List and check compute "
        "instances, manage Cloud Storage buckets and objects. "
        "Requires GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_API_KEY."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "list_instances", "instance_status", "list_buckets",
                    "upload_object", "download_object",
                ],
                "description": "GCP action to perform.",
            },
            "project": {
                "type": "string",
                "description": "GCP project ID.",
            },
            "zone": {
                "type": "string",
                "description": "Compute zone (e.g. us-central1-a).",
            },
            "instance": {
                "type": "string",
                "description": "Instance name (for instance_status).",
            },
            "bucket": {
                "type": "string",
                "description": "Cloud Storage bucket name.",
            },
            "name": {
                "type": "string",
                "description": "Object name/key in the bucket.",
            },
            "data": {
                "type": "string",
                "description": "Data to upload (for upload_object).",
            },
        },
        "required": ["action"],
    }

    async def _get_access_token(self) -> str:
        """Get access token from service account credentials or metadata server."""
        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path:
            return await self._get_token_from_service_account(creds_path)

        api_key = os.environ.get("GOOGLE_API_KEY")
        if api_key:
            return api_key

        # Try metadata server (running on GCP)
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    "http://metadata.google.internal/computeMetadata/v1/instance/"
                    "service-accounts/default/token",
                    headers={"Metadata-Flavor": "Google"},
                )
                resp.raise_for_status()
                return resp.json()["access_token"]
        except Exception:
            pass

        raise ValueError(
            "No GCP credentials found. Set GOOGLE_APPLICATION_CREDENTIALS "
            "or GOOGLE_API_KEY environment variable."
        )

    async def _get_token_from_service_account(self, creds_path: str) -> str:
        """Generate OAuth2 token from service account JSON key."""
        import time

        with open(creds_path) as f:
            creds = json.load(f)

        # Build JWT
        try:
            import jwt  # PyJWT

            now = int(time.time())
            payload = {
                "iss": creds["client_email"],
                "scope": "https://www.googleapis.com/auth/cloud-platform",
                "aud": "https://oauth2.googleapis.com/token",
                "iat": now,
                "exp": now + 3600,
            }
            signed = jwt.encode(payload, creds["private_key"], algorithm="RS256")

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": signed,
                    },
                )
                resp.raise_for_status()
                return resp.json()["access_token"]
        except ImportError:
            raise ValueError(
                "PyJWT is required for service account auth. Install: pip install PyJWT"
            )

    def _auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        logger.info("gcp_execute", action=action)

        try:
            if action == "list_instances":
                return await self._list_instances(kwargs)
            elif action == "instance_status":
                return await self._instance_status(kwargs)
            elif action == "list_buckets":
                return await self._list_buckets(kwargs)
            elif action == "upload_object":
                return await self._upload_object(kwargs)
            elif action == "download_object":
                return await self._download_object(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except ValueError as e:
            return json.dumps({"error": str(e)})
        except httpx.TimeoutException:
            return json.dumps({"error": "GCP API request timed out"})
        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:500]
            return json.dumps({"error": f"HTTP {e.response.status_code}: {error_text}"})
        except Exception as e:
            logger.error("gcp_error", error=str(e))
            return json.dumps({"error": f"GCP operation failed: {e}"})

    async def _list_instances(self, kwargs: dict) -> str:
        project = kwargs.get("project")
        zone = kwargs.get("zone")

        if not project or not zone:
            return json.dumps({"error": "project and zone are required"})

        token = await self._get_access_token()
        url = f"{GCP_COMPUTE_URL}/projects/{project}/zones/{zone}/instances"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._auth_headers(token))
            resp.raise_for_status()
            data = resp.json()

        instances = [
            {
                "name": i.get("name"),
                "status": i.get("status"),
                "machine_type": i.get("machineType", "").split("/")[-1],
                "zone": zone,
                "creation_timestamp": i.get("creationTimestamp"),
                "network_interfaces": [
                    {
                        "network": ni.get("network", "").split("/")[-1],
                        "internal_ip": ni.get("networkIP"),
                        "external_ip": (
                            ni.get("accessConfigs", [{}])[0].get("natIP")
                            if ni.get("accessConfigs") else None
                        ),
                    }
                    for ni in i.get("networkInterfaces", [])
                ],
            }
            for i in data.get("items", [])
        ]

        logger.info("gcp_instances_listed", project=project, zone=zone, count=len(instances))
        return _truncate(json.dumps({"instances": instances, "count": len(instances)}))

    async def _instance_status(self, kwargs: dict) -> str:
        project = kwargs.get("project")
        zone = kwargs.get("zone")
        instance = kwargs.get("instance")

        if not all([project, zone, instance]):
            return json.dumps({"error": "project, zone, and instance are required"})

        token = await self._get_access_token()
        url = f"{GCP_COMPUTE_URL}/projects/{project}/zones/{zone}/instances/{instance}"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._auth_headers(token))
            resp.raise_for_status()
            data = resp.json()

        result = {
            "name": data.get("name"),
            "status": data.get("status"),
            "machine_type": data.get("machineType", "").split("/")[-1],
            "zone": zone,
            "creation_timestamp": data.get("creationTimestamp"),
            "disks": [
                {
                    "name": d.get("source", "").split("/")[-1],
                    "size_gb": d.get("diskSizeGb"),
                    "type": d.get("type"),
                    "boot": d.get("boot", False),
                }
                for d in data.get("disks", [])
            ],
            "network_interfaces": [
                {
                    "internal_ip": ni.get("networkIP"),
                    "external_ip": (
                        ni.get("accessConfigs", [{}])[0].get("natIP")
                        if ni.get("accessConfigs") else None
                    ),
                }
                for ni in data.get("networkInterfaces", [])
            ],
            "labels": data.get("labels", {}),
        }

        logger.info("gcp_instance_status", instance=instance, status=result["status"])
        return json.dumps(result)

    async def _list_buckets(self, kwargs: dict) -> str:
        project = kwargs.get("project")
        if not project:
            return json.dumps({"error": "project is required"})

        token = await self._get_access_token()
        url = f"{GCP_STORAGE_API_URL}/b"
        params = {"project": project}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._auth_headers(token), params=params)
            resp.raise_for_status()
            data = resp.json()

        buckets = [
            {
                "name": b.get("name"),
                "location": b.get("location"),
                "storage_class": b.get("storageClass"),
                "created": b.get("timeCreated"),
            }
            for b in data.get("items", [])
        ]

        logger.info("gcp_buckets_listed", project=project, count=len(buckets))
        return _truncate(json.dumps({"buckets": buckets, "count": len(buckets)}))

    async def _upload_object(self, kwargs: dict) -> str:
        bucket = kwargs.get("bucket")
        name = kwargs.get("name")
        data_str = kwargs.get("data", "")

        if not bucket or not name:
            return json.dumps({"error": "bucket and name are required"})
        if not data_str:
            return json.dumps({"error": "data is required for upload"})

        token = await self._get_access_token()
        url = (
            f"{GCP_STORAGE_URL}/upload/storage/v1/b/{bucket}/o"
            f"?uploadType=media&name={name}"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, content=data_str.encode())
            resp.raise_for_status()
            result = resp.json()

        logger.info("gcp_object_uploaded", bucket=bucket, name=name)
        return json.dumps({
            "success": True,
            "bucket": bucket,
            "name": name,
            "size": result.get("size"),
            "content_type": result.get("contentType"),
            "created": result.get("timeCreated"),
        })

    async def _download_object(self, kwargs: dict) -> str:
        bucket = kwargs.get("bucket")
        name = kwargs.get("name")

        if not bucket or not name:
            return json.dumps({"error": "bucket and name are required"})

        token = await self._get_access_token()
        url = f"{GCP_STORAGE_API_URL}/b/{bucket}/o/{name}?alt=media"
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        content = resp.text
        logger.info("gcp_object_downloaded", bucket=bucket, name=name)
        return _truncate(json.dumps({
            "bucket": bucket,
            "name": name,
            "content": content,
            "size_bytes": len(resp.content),
        }))
