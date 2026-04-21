from typing import Optional

from pydantic import BaseModel, Field


class UpdateTenantInfoRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant ID")
    llm_id: Optional[str] = Field(None, description="LLM ID")
    embd_id: Optional[str] = Field(None, description="Embedding ID")
    asr_id: Optional[str] = Field(None, description="ASR ID")
    img2txt_id: Optional[str] = Field(None, description="Image to Text ID")


class UpdateUserSettingRequest(BaseModel):
    nickname: Optional[str] = Field(None, description="User nickname")
    avatar: Optional[str] = Field(None, description="User avatar")
    language: Optional[str] = Field(None, description="User language")
    color_schema: Optional[str] = Field(None, description="Color schema")
    timezone: Optional[str] = Field(None, description="Timezone")
    password: Optional[str] = Field(None, description="Current password")
    new_password: Optional[str] = Field(None, description="New password")


class UserInfoResponse(BaseModel):
    id: str = Field(..., description="User ID")
    nickname: str = Field(..., description="User nickname")
    email: str = Field(..., description="User email")
    avatar: Optional[str] = Field(None, description="User avatar")
    language: Optional[str] = Field(None, description="User language")
    color_schema: Optional[str] = Field(None, description="Color schema")
    timezone: Optional[str] = Field(None, description="Timezone")
    last_login_time: Optional[str] = Field(None, description="Last login timestamp")
    is_superuser: bool = Field(False, description="Is superuser")
