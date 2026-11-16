"""Request and response shapes.

These are what show up in the /docs page. The database models stay separate
so a response can't accidentally include a password hash or an email address
on a craft post.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class HealthOut(BaseModel):
    status: str


class CounterOut(BaseModel):
    count: int


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str


class TokenOut(BaseModel):
    token: str
    user: UserOut
    # Filled in on register, so the stubbed email check is visible in /docs.
    note: str | None = None


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("display_name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Display name is required.")
        return cleaned


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class CraftIn(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    description: str = Field(default="", max_length=4000)
    image_url: str = Field(default="", max_length=500)
    category: str = Field(default="", max_length=80)
    tags: list[str] = Field(default_factory=list)
    dimensions: str = Field(default="", max_length=120)
    colors: str = Field(default="", max_length=200)
    tools: str = Field(default="", max_length=300)
    backstory: str = Field(default="", max_length=4000)
    note: str = Field(default="", max_length=4000)
    location_text: str = Field(default="", max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    status: Literal["published", "draft"] = "published"

    @field_validator(
        "title",
        "description",
        "category",
        "dimensions",
        "colors",
        "tools",
        "backstory",
        "note",
        "location_text",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("image_url")
    @classmethod
    def image_url_http(cls, value: str) -> str:
        value = value.strip()
        if value and not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("Image URL should start with http:// or https://.")
        return value

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for tag in value:
            tag = tag.strip().lower().lstrip("#")
            if tag and tag not in cleaned:
                cleaned.append(tag)
        return cleaned


class CraftOut(BaseModel):
    id: int
    title: str
    description: str
    image_url: str
    category: str
    tags: list[str]
    dimensions: str
    colors: str
    tools: str
    backstory: str
    note: str
    location_text: str
    latitude: float | None
    longitude: float | None
    status: str
    card_height: int
    author_name: str
    # True when the logged-in user wrote this post. The UI uses it for Edit.
    owner: bool
    favorited: bool
    created_at: datetime


class FavoriteOut(BaseModel):
    favorited: bool


class ReportIn(BaseModel):
    reason: str = Field(min_length=3, max_length=200)
    details: str = Field(min_length=3, max_length=2000)

    @field_validator("reason", "details")
    @classmethod
    def strip_report(cls, value: str) -> str:
        return value.strip()


class ReportOut(BaseModel):
    id: int
    craft_id: int
    reason: str
    details: str
    created_at: datetime
