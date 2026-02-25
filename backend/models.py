"""
models.py — SQLAlchemy Database Models
=======================================

Defines the data schema for the SaaS platform:
  • User — authentication & billing info
  • Job  — video processing jobs
  • Payment — Stripe payment records
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime,
    ForeignKey, JSON, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from database import Base

import enum


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    FINDING_HOOK = "finding_hook"
    CROPPING = "cropping"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanType(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    AGENCY = "agency"


# ─────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    image = Column(String, nullable=True)

    # Billing
    plan = Column(String, default=PlanType.FREE.value)
    credits_remaining = Column(Integer, default=3)  # Free users get 3 credits
    stripe_customer_id = Column(String, nullable=True, unique=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    jobs = relationship("Job", back_populates="user", lazy="dynamic")
    payments = relationship("Payment", back_populates="user", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.email} plan={self.plan} credits={self.credits_remaining}>"


# ─────────────────────────────────────────────────────────────
# Job
# ─────────────────────────────────────────────────────────────

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Status tracking
    status = Column(String, default=JobStatus.PENDING.value, index=True)
    progress = Column(Integer, default=0)  # 0-100 percentage
    error_message = Column(Text, nullable=True)

    # Input
    input_path = Column(String, nullable=False)
    source_type = Column(String, default="upload")  # "upload" or "youtube"
    youtube_url = Column(String, nullable=True)

    # Output
    output_path = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)

    # Processing results
    transcript_json = Column(JSON, nullable=True)
    hook_json = Column(JSON, nullable=True)
    hook_title = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Duration
    duration_seconds = Column(Float, nullable=True)

    # Relationships
    user = relationship("User", back_populates="jobs")

    def __repr__(self):
        return f"<Job {self.id[:8]} status={self.status}>"


# ─────────────────────────────────────────────────────────────
# Payment
# ─────────────────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Stripe
    stripe_session_id = Column(String, unique=True, nullable=True)
    stripe_payment_intent = Column(String, nullable=True)

    # Amount
    amount_cents = Column(Integer, nullable=False)  # in cents
    currency = Column(String, default="usd")
    plan = Column(String, nullable=False)
    credits_purchased = Column(Integer, nullable=False)

    # Status
    status = Column(String, default="pending")  # pending, completed, refunded

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.id[:8]} ${self.amount_cents / 100:.2f}>"
