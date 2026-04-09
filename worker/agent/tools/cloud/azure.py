"""Azure Cloud tool - interact with Azure resources via REST API."""

import json
import os
from typing import Any

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
AZURE_MGMT_URL = "https://management.azure.com"
AZURE_LOGIN_URL = "https://login.microsoftonline.com"
AZURE_STORAGE_URL = "https://{account}.blob.core.windows.net"
API_VERSION_COMPUTE = "2023-09-01"
API_VERSION_STORAGE = "2023-01-01"


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


class AzureCloudTool(BaseTool):
    name = "azure_cloud"
    description = (
        "Interact with Azure Cloud resources. List and manage VMs, "
        "storage accounts, and blob storage. Requires AZURE_TENANT_ID, "
        "AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET environment variables."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "list_vms", "vm_status", "list_storage_accounts",
                    "blob_upload", "blob_download",
                ],
                "description": "Azure action to perform.",
            },
            "subscription_id": {
                "type": "string",
                "description": "Azure subscription ID.",
            },
            "resource_group": {
                "type": "string",
                "description": "Resource group name (for vm_status).",
            },
            "vm_name": {
                "type": "string",
                "description": "VM name (for vm_status).",
            },
            "account": {
                "type": "string",
                "description": "Storage account name (for blob operations).",
            },
            "container": {
                "type": "string",
                "description": "Blob container name.",
            },
            "blob_name": {
                "type": "string",
                "description": "Blob name.",
            },
            "data": {
                "type": "string",
                "description": "Data to upload (for blob_upload).",
            },
        },
        "required": ["action"],
    }

    def _get_credentials(self) -> tuple[str, str, str] | None:
        tenant = os.environ.get("AZURE_TENANT_ID")
        client_id = os.environ.get("AZURE_CLIENT_ID")
        client_secret = os.environ.get("AZURE_CLIENT_SECRET")
        if not all([tenant, client_id, client_secret]):
            return None
        return tenant, client_id, client_secret  # type: ignore

    async def _get_mgmt_token(self) -> str:
        """Acquire OAuth2 token for Azure Management API."""
        creds = self._get_credentials()
        if not creds:
            raise ValueError(
                "Missing Azure credentials. Set AZURE_TENANT_ID, "
                "AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET."
            )
        tenant_id, client_id, client_secret = creds

        url = f"{AZURE_LOGIN_URL}/{tenant_id}/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": f"{AZURE_MGMT_URL}/.default",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data=data)
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def _get_storage_token(self) -> str:
        """Acquire OAuth2 token for Azure Storage."""
        creds = self._get_credentials()
        if not creds:
            raise ValueError("Missing Azure credentials.")
        tenant_id, client_id, client_secret = creds

        url = f"{AZURE_LOGIN_URL}/{tenant_id}/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://storage.azure.com/.default",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data=data)
            resp.raise_for_status()
            return resp.json()["access_token"]

    def _mgmt_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        logger.info("azure_execute", action=action)

        try:
            if action == "list_vms":
                return await self._list_vms(kwargs)
            elif action == "vm_status":
                return await self._vm_status(kwargs)
            elif action == "list_storage_accounts":
                return await self._list_storage_accounts(kwargs)
            elif action == "blob_upload":
                return await self._blob_upload(kwargs)
            elif action == "blob_download":
                return await self._blob_download(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except ValueError as e:
            return json.dumps({"error": str(e)})
        except httpx.TimeoutException:
            return json.dumps({"error": "Azure API request timed out"})
        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:500]
            return json.dumps({"error": f"HTTP {e.response.status_code}: {error_text}"})
        except Exception as e:
            logger.error("azure_error", error=str(e))
            return json.dumps({"error": f"Azure operation failed: {e}"})

    async def _list_vms(self, kwargs: dict) -> str:
        subscription_id = kwargs.get("subscription_id")
        if not subscription_id:
            return json.dumps({"error": "subscription_id is required"})

        token = await self._get_mgmt_token()
        url = (
            f"{AZURE_MGMT_URL}/subscriptions/{subscription_id}"
            f"/providers/Microsoft.Compute/virtualMachines"
            f"?api-version={API_VERSION_COMPUTE}"
        )

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._mgmt_headers(token))
            resp.raise_for_status()
            data = resp.json()

        vms = [
            {
                "name": vm.get("name"),
                "location": vm.get("location"),
                "vm_size": vm.get("properties", {}).get("hardwareProfile", {}).get("vmSize"),
                "os_type": vm.get("properties", {}).get("storageProfile", {})
                    .get("osDisk", {}).get("osType"),
                "provisioning_state": vm.get("properties", {}).get("provisioningState"),
                "resource_group": vm.get("id", "").split("/")[4] if vm.get("id") else "",
            }
            for vm in data.get("value", [])
        ]

        logger.info("azure_vms_listed", count=len(vms))
        return _truncate(json.dumps({"vms": vms, "count": len(vms)}))

    async def _vm_status(self, kwargs: dict) -> str:
        subscription_id = kwargs.get("subscription_id")
        resource_group = kwargs.get("resource_group")
        vm_name = kwargs.get("vm_name")

        if not all([subscription_id, resource_group, vm_name]):
            return json.dumps({"error": "subscription_id, resource_group, and vm_name are required"})

        token = await self._get_mgmt_token()
        url = (
            f"{AZURE_MGMT_URL}/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group}"
            f"/providers/Microsoft.Compute/virtualMachines/{vm_name}"
            f"/instanceView?api-version={API_VERSION_COMPUTE}"
        )

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._mgmt_headers(token))
            resp.raise_for_status()
            data = resp.json()

        statuses = data.get("statuses", [])
        result = {
            "vm_name": vm_name,
            "resource_group": resource_group,
            "statuses": [
                {
                    "code": s.get("code"),
                    "level": s.get("level"),
                    "display_status": s.get("displayStatus"),
                    "time": s.get("time"),
                }
                for s in statuses
            ],
            "vm_agent": {
                "status": data.get("vmAgent", {}).get("vmAgentVersion"),
            },
        }

        logger.info("azure_vm_status", vm=vm_name, statuses=len(statuses))
        return json.dumps(result)

    async def _list_storage_accounts(self, kwargs: dict) -> str:
        subscription_id = kwargs.get("subscription_id")
        if not subscription_id:
            return json.dumps({"error": "subscription_id is required"})

        token = await self._get_mgmt_token()
        url = (
            f"{AZURE_MGMT_URL}/subscriptions/{subscription_id}"
            f"/providers/Microsoft.Storage/storageAccounts"
            f"?api-version={API_VERSION_STORAGE}"
        )

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._mgmt_headers(token))
            resp.raise_for_status()
            data = resp.json()

        accounts = [
            {
                "name": sa.get("name"),
                "location": sa.get("location"),
                "kind": sa.get("kind"),
                "sku": sa.get("sku", {}).get("name"),
                "provisioning_state": sa.get("properties", {}).get("provisioningState"),
            }
            for sa in data.get("value", [])
        ]

        logger.info("azure_storage_listed", count=len(accounts))
        return _truncate(json.dumps({"storage_accounts": accounts, "count": len(accounts)}))

    async def _blob_upload(self, kwargs: dict) -> str:
        account = kwargs.get("account")
        container = kwargs.get("container")
        blob_name = kwargs.get("blob_name")
        data_str = kwargs.get("data", "")

        if not all([account, container, blob_name]):
            return json.dumps({"error": "account, container, and blob_name are required"})
        if not data_str:
            return json.dumps({"error": "data is required for upload"})

        token = await self._get_storage_token()
        url = f"https://{account}.blob.core.windows.net/{container}/{blob_name}"
        headers = {
            "Authorization": f"Bearer {token}",
            "x-ms-blob-type": "BlockBlob",
            "x-ms-version": "2021-08-06",
            "Content-Type": "application/octet-stream",
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.put(url, headers=headers, content=data_str.encode())
            resp.raise_for_status()

        logger.info("azure_blob_uploaded", account=account, blob=blob_name)
        return json.dumps({
            "success": True,
            "account": account,
            "container": container,
            "blob_name": blob_name,
            "size_bytes": len(data_str.encode()),
        })

    async def _blob_download(self, kwargs: dict) -> str:
        account = kwargs.get("account")
        container = kwargs.get("container")
        blob_name = kwargs.get("blob_name")

        if not all([account, container, blob_name]):
            return json.dumps({"error": "account, container, and blob_name are required"})

        token = await self._get_storage_token()
        url = f"https://{account}.blob.core.windows.net/{container}/{blob_name}"
        headers = {
            "Authorization": f"Bearer {token}",
            "x-ms-version": "2021-08-06",
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        content = resp.text
        logger.info("azure_blob_downloaded", account=account, blob=blob_name)
        return _truncate(json.dumps({
            "account": account,
            "container": container,
            "blob_name": blob_name,
            "content": content,
            "size_bytes": len(resp.content),
        }))
