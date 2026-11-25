"""Veritabanı modelleri (ER diyagramıyla birebir).

ER diyagramına eklenen iki alan:
  - users.password_hash : kimlik doğrulama için zorunlu
  - analyses.status     : created -> images_uploaded -> completed akışını izlemek için
Görüntü ve maske dosya yolları storage klasörüne GÖRELİ saklanır (taşınabilirlik / güvenlik).
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # UTC, tz'siz (SQLite/PostgreSQL uyumu)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="analyst")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    analyses: Mapped[list["Analysis"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    region_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="created")
    change_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mean_iou: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    analysis_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="analyses")
    image: Mapped[Optional["Image"]] = relationship(
        back_populates="analysis", uselist=False, cascade="all, delete-orphan"
    )
    change_mask: Mapped[Optional["ChangeMask"]] = relationship(
        back_populates="analysis", uselist=False, cascade="all, delete-orphan"
    )


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), unique=True)
    t1_image_path: Mapped[str] = mapped_column(String(500))
    t2_image_path: Mapped[str] = mapped_column(String(500))
    crs_projection: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bounding_box: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    analysis: Mapped["Analysis"] = relationship(back_populates="image")


class ChangeMask(Base):
    __tablename__ = "change_masks"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), unique=True)
    mask_path: Mapped[str] = mapped_column(String(500))
    geojson_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    detected_change_pixels: Mapped[int] = mapped_column(Integer, default=0)

    analysis: Mapped["Analysis"] = relationship(back_populates="change_mask")
