"""Authentication and user schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


from mailagent.users.models import User


class UserResponse(BaseModel):
    """User account response model matching API types specification."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str = Field(..., alias="name")
    display_name: str | None = None
    picture_url: str | None = None
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> UserResponse:
        display_name = user.display_name or ""
        email = user.email
        name = display_name if display_name else email.split("@")[0]
        return cls(
            id=user.id,
            email=email,
            name=name,
            display_name=display_name,
            picture_url=user.picture_url,
            created_at=user.created_at,
        )


class AuthStatusResponse(BaseModel):
    """Current authentication status."""

    authenticated: bool
    user: UserResponse | None = None
