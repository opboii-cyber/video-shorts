"""
payments.py — Polar Payments Router
=====================================

Uses Polar (polar.sh) for payments instead of Stripe.

Handles:
  POST /api/payments/checkout — create Polar Checkout session
  POST /api/payments/webhook  — handle Polar webhook events
  GET  /api/payments/usage    — get user's credits & payment history
  GET  /api/payments/plans    — list available plans (public)
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import User, Payment
from middleware.auth_middleware import get_current_user, CurrentUser

logger = logging.getLogger(__name__)
router = APIRouter()

# ─────────────────────────────────────────────────────────────
# Polar Configuration
# ─────────────────────────────────────────────────────────────

POLAR_ACCESS_TOKEN = os.getenv("POLAR_ACCESS_TOKEN", "")
POLAR_WEBHOOK_SECRET = os.getenv("POLAR_WEBHOOK_SECRET", "")
POLAR_API_URL = os.getenv("POLAR_API_URL", "https://api.polar.sh")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Plan definitions — replace product IDs with your actual Polar product IDs
# Create these in your Polar Dashboard → Products → Catalogue
PLANS = {
    "starter": {
        "name": "Starter",
        "price": 9.99,
        "credits": 15,
        "polar_product_id": os.getenv("POLAR_STARTER_PRODUCT_ID", ""),
    },
    "pro": {
        "name": "Pro",
        "price": 29.99,
        "credits": 50,
        "polar_product_id": os.getenv("POLAR_PRO_PRODUCT_ID", ""),
    },
    "agency": {
        "name": "Agency",
        "price": 79.99,
        "credits": 200,
        "polar_product_id": os.getenv("POLAR_AGENCY_PRODUCT_ID", ""),
    },
}


# ─────────────────────────────────────────────────────────────
# Helper: get or create user in DB
# ─────────────────────────────────────────────────────────────

def get_or_create_user(db: Session, user: CurrentUser) -> User:
    """Find existing user or create a new one."""
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        db_user = User(
            id=user.id,
            email=user.email,
            name=user.name,
            image=user.image,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    return db_user


# ─────────────────────────────────────────────────────────────
# Helper: Polar API call
# ─────────────────────────────────────────────────────────────

async def _polar_api(method: str, endpoint: str, data: dict = None) -> dict:
    """Make an authenticated request to the Polar API."""
    import httpx

    url = f"{POLAR_API_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {POLAR_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        if method == "POST":
            response = await client.post(url, json=data, headers=headers)
        else:
            response = await client.get(url, headers=headers)

        if response.status_code >= 400:
            logger.error(f"Polar API error: {response.status_code} {response.text}")
            raise HTTPException(response.status_code, f"Polar API error: {response.text}")

        return response.json()


# ─────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: str  # "starter", "pro", or "agency"


@router.post("/payments/checkout")
async def create_checkout_session(
    req: CheckoutRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Polar Checkout Session for the selected plan.
    Returns the checkout URL for the frontend to redirect to.

    Polar API: POST /v1/checkouts/
    Docs: https://polar.sh/docs/guides/create-checkout-session
    """
    if req.plan not in PLANS:
        raise HTTPException(400, f"Invalid plan: {req.plan}")

    if not POLAR_ACCESS_TOKEN:
        raise HTTPException(500, "Polar is not configured. Set POLAR_ACCESS_TOKEN.")

    plan = PLANS[req.plan]

    if not plan["polar_product_id"]:
        raise HTTPException(500, f"Product ID not configured for {req.plan} plan")

    db_user = get_or_create_user(db, user)

    # Create Polar Checkout Session
    checkout_data = {
        "products": [plan["polar_product_id"]],
        "success_url": f"{FRONTEND_URL}/dashboard?payment=success",
        "metadata": {
            "user_id": db_user.id,
            "user_email": db_user.email,
            "plan": req.plan,
            "credits": str(plan["credits"]),
        },
    }

    # If customer email is known, pre-fill it
    if db_user.email:
        checkout_data["customer_email"] = db_user.email

    result = await _polar_api("POST", "/v1/checkouts/", checkout_data)

    checkout_url = result.get("url", "")

    logger.info(f"Polar checkout created for {user.email}: plan={req.plan}")

    return {
        "checkout_url": checkout_url,
        "checkout_id": result.get("id", ""),
    }


def _verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify Polar webhook signature (Standard Webhooks spec).
    Uses HMAC-SHA256 with base64-encoded secret.
    """
    import base64

    try:
        # Standard Webhooks uses base64-encoded secret
        secret_bytes = base64.b64decode(secret)
        expected = hmac.new(secret_bytes, payload, hashlib.sha256).digest()
        expected_b64 = "v1," + __import__('base64').b64encode(expected).decode()
        return hmac.compare_digest(expected_b64, signature)
    except Exception:
        # Fallback: just try to parse — in dev, signature may not be set
        return not secret  # Pass if no secret configured (dev only)


@router.post("/payments/webhook")
async def polar_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Polar webhook events.

    Key event: order.paid → credit the user.

    Polar sends events to this endpoint when orders are completed.
    Configure it in your Polar Dashboard → Settings → Webhooks.
    """
    payload = await request.body()

    # Verify webhook signature if secret is configured
    if POLAR_WEBHOOK_SECRET:
        sig = request.headers.get("webhook-signature", "")
        if not _verify_webhook_signature(payload, sig, POLAR_WEBHOOK_SECRET):
            raise HTTPException(400, "Invalid webhook signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON payload")

    event_type = event.get("type", "")
    data = event.get("data", {})

    logger.info(f"Polar webhook received: {event_type}")

    # Handle order.paid — credit the user
    if event_type == "order.paid":
        metadata = data.get("metadata", {})
        user_id = metadata.get("user_id")
        plan = metadata.get("plan")
        credits = int(metadata.get("credits", 0))

        if user_id and credits > 0:
            db_user = db.query(User).filter(User.id == user_id).first()
            if db_user:
                db_user.credits_remaining += credits
                db_user.plan = plan

                # Record the payment
                payment = Payment(
                    user_id=user_id,
                    stripe_session_id=data.get("id", ""),  # reusing field for Polar order ID
                    stripe_payment_intent=None,
                    amount_cents=int(data.get("amount", 0)),
                    plan=plan,
                    credits_purchased=credits,
                    status="completed",
                )
                db.add(payment)
                db.commit()

                logger.info(
                    f"✓ Payment: user={user_id} plan={plan} "
                    f"credits=+{credits} (total={db_user.credits_remaining})"
                )
            else:
                logger.warning(f"User not found for webhook: {user_id}")

    return {"status": "ok"}


@router.get("/payments/usage")
async def get_usage(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's current credits and payment history."""
    db_user = get_or_create_user(db, user)

    payments = (
        db.query(Payment)
        .filter(Payment.user_id == db_user.id)
        .order_by(Payment.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "credits_remaining": db_user.credits_remaining,
        "plan": db_user.plan,
        "payments": [
            {
                "id": p.id,
                "plan": p.plan,
                "credits": p.credits_purchased,
                "amount": p.amount_cents / 100,
                "status": p.status,
                "date": p.created_at.isoformat() if p.created_at else None,
            }
            for p in payments
        ],
    }


@router.get("/payments/plans")
async def get_plans():
    """Return available plans (public endpoint)."""
    return {
        plan_id: {
            "name": plan["name"],
            "price": plan["price"],
            "credits": plan["credits"],
        }
        for plan_id, plan in PLANS.items()
    }
