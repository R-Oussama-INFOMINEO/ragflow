from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InviteUserRequest(BaseModel):
    email: str = Field(..., description="Email address of the user to invite")

class TenantUserResponse(BaseModel):
    id: str
    email: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    role: Optional[str] = None

class InvitedUserResponse(BaseModel):
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    nickname: Optional[str] = Field(None, description="User nickname")
    avatar: Optional[str] = Field(None, description="User avatar")


class TenantMemberResponse(BaseModel):
    id: str = Field(..., description="UserTenant relationship ID")
    user_id: str = Field(..., description="User ID")
    role: str = Field(..., description="User role in tenant")
    status: str = Field(..., description="Relationship status")
    nickname: str = Field(..., description="User nickname")
    email: str = Field(..., description="User email address")
    avatar: Optional[str] = Field(None, description="User avatar")
    is_authenticated: Optional[str] = Field(None, description="Authentication status")
    is_active: Optional[str] = Field(None, description="Active status")
    is_anonymous: Optional[str] = Field(None, description="Anonymous status")
    is_superuser: Optional[bool] = Field(None, description="Superuser flag")
    update_date: Optional[str] = Field(None, description="Last update date")
    delta_seconds: Optional[float] = Field(None, description="Seconds since last update")


class InvitationEntity(BaseModel):
    """Represents a pending invitation for a user to join a tenant."""
    tenant_id: str = Field(..., description="The unique identifier of the tenant")
    role: str = Field(..., description="The role assigned to the user (e.g., 'invite', 'normal')")
    nickname: str = Field(..., description="Nickname of the user/tenant")
    email: str = Field(..., description="Email address associated with the invitation")
    avatar: Optional[str] = Field(None, description="Avatar of the user/tenant")
    update_date: str = Field(..., description="The date the invitation was last updated")
    delta_seconds: Optional[float] = Field(None, description="Time difference in seconds since the last update")
