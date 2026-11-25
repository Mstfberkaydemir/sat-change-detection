"""Pydantic şemaları (istek / yanıt modelleri). Swagger bunlardan otomatik üretilir."""
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$", examples=["berkay"])
    email: str = Field(max_length=255, examples=["berkay@example.com"])
    password: str = Field(min_length=8, max_length=128, examples=["en-az-8-karakter"])

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Geçersiz e-posta adresi")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AnalysisCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["Hatay deprem sonrası analiz"])
    region_name: str = Field(min_length=1, max_length=100, examples=["Hatay"])


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    t1_image_path: str
    t2_image_path: str
    crs_projection: Optional[str] = None
    bounding_box: Optional[str] = None


class ChangeMaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mask_path: str
    geojson_path: Optional[str] = None
    detected_change_pixels: int


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    region_name: str
    status: str
    change_percentage: Optional[float] = None
    mean_iou: Optional[float] = None
    analysis_date: datetime
    image: Optional[ImageOut] = None
    change_mask: Optional[ChangeMaskOut] = None
