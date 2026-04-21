from typing import Any, Dict, List

import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed

from ..base import BadRequestError, RagflowAPIBase, ServerError
from ..Tenant.tenant_dto import (
    InvitationEntity,
    InvitedUserResponse,
    InviteUserRequest,
    TenantMemberResponse,
)


class TenantRagflowAPI(RagflowAPIBase):
    """
    Tenant/team invitation and management API.

    Provides methods for inviting users to tenants, viewing invitations, and accepting invitations.
    """

    def __init__(self, hostname: str, public_key: str = None, public_key_path: str = None, version: str = "v1"):
        """Initialize the Tenant API client."""
        super().__init__(hostname, public_key, public_key_path, version)
        self.tenant_url = f"{hostname}/{version}/tenant"

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def invite_user(self, tenant_id: str, invite_user_request: InviteUserRequest, token: str, **kwargs) -> InvitedUserResponse:
        """
        Invite a user via email to join a tenant/team.

        Args:
            tenant_id: The tenant ID to invite the user to
            invite_user_request: InviteUserRequest containing the email address
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            Dictionary containing invitation result data

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If invitation fails

        Example:
            >>> from ragflow_api.Tenant import InviteUserRequest
            >>> api = TenantRagflowAPI("http://localhost:9380")
            >>> invite_req = InviteUserRequest(email="newuser@example.com")
            >>> result = await api.invite_user("tenant_123", invite_req, token)
        """
        url = f"{self.tenant_url}/{tenant_id}/user"
        headers = {"Authorization": f"{token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=invite_user_request.model_dump(exclude_none=True), headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Invite user failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Invite user failed: {res_json.get('message')}")
                data = res_json.get("data", {})
                return InvitedUserResponse(**data)

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def list_invitations(self, token: str, **kwargs) -> List[InvitationEntity]:
        """
        View all pending invitations for the current authenticated user.

        Args:
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            List of invitation dictionaries containing tenant_id, role, email, etc.

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If request fails

        Example:
            >>> api = TenantRagflowAPI("http://localhost:9380")
            >>> invitations = await api.list_invitations(token)
            >>> for inv in invitations:
            ...     print(f"Invited to tenant: {inv['tenant_id']}")
        """
        url = f"{self.tenant_url}/list"
        headers = {"Authorization": f"{token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"List invitations failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"List invitations failed: {res_json.get('message')}")
                invitations_data = res_json.get("data", [])
                return [InvitationEntity(**inv) for inv in invitations_data]

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def accept_invitation(self, tenant_id: str, token: str, **kwargs) -> bool:
        """
        Accept a pending invitation to join a tenant/team.

        Args:
            tenant_id: The tenant ID of the invitation to accept
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if invitation was successfully accepted

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If acceptance fails

        Example:
            >>> api = TenantRagflowAPI("http://localhost:9380")
            >>> invitations = await api.list_invitations(token)
            >>> tenant_id = invitations[0]["tenant_id"]
            >>> success = await api.accept_invitation(tenant_id, token)
        """
        url = f"{self.tenant_url}/agree/{tenant_id}"
        headers = {"Authorization": f"{token}"}
        async with aiohttp.ClientSession() as session:
            # PUT request with no body
            async with session.put(url, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Accept invitation failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Accept invitation failed: {res_json.get('message')}")
                return res_json.get("data") is True

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def list_users(self, tenant_id: str, token: str, **kwargs) -> List[TenantMemberResponse]:
        """
        List all users in a specific tenant/team.

        Args:
            tenant_id: The tenant ID to list users from
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            List of TenantMemberResponse objects

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If listing fails

        Example:
            >>> api = TenantRagflowAPI("http://localhost:9380")
            >>> users = await api.list_users("tenant_123", token)
            >>> for user in users:
            ...     print(f"User: {user.nickname}, Role: {user.role}")
        """
        url = f"{self.tenant_url}/{tenant_id}/user/list"
        headers = {"Authorization": f"{token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"List users failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"List users failed: {res_json.get('message')}")

                users_data = res_json.get("data", [])
                return [TenantMemberResponse(**user) for user in users_data]

    @RagflowAPIBase.requires_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def remove_user(self, tenant_id: str, user_id: str, token: str, **kwargs) -> bool:
        """
        Remove a user from a tenant/team.

        Args:
            tenant_id: The tenant ID to remove the user from
            user_id: The user ID to remove
            token: Valid authentication token
            **kwargs: Additional optional parameters

        Returns:
            True if user was successfully removed

        Raises:
            ServerError: If server returns non-200 status
            BadRequestError: If removal fails

        Example:
            >>> api = TenantRagflowAPI("http://localhost:9380")
            >>> success = await api.remove_user("tenant_123", "user_456", token)
        """
        url = f"{self.tenant_url}/{tenant_id}/user/{user_id}"
        headers = {"Authorization": f"{token}"}
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Remove user failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise BadRequestError(f"Remove user failed: {res_json.get('message')}")
                return res_json.get("data") is True
