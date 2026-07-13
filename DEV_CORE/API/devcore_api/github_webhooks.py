from __future__ import annotations

import hashlib
import hmac
import os
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field


GITHUB_SIGNATURE_HEADER = "x-hub-signature-256"
GITHUB_SECRET_ENV = "DEVCORE_GITHUB_WEBHOOK_SECRET"


class GitHubWebhookAccepted(BaseModel):
    schema_version: Literal[1] = 1
    provider: Literal["github"] = "github"
    event: str = Field(min_length=1)
    delivery_id: str = Field(min_length=1)
    accepted: Literal[True] = True


def get_github_webhook_secret() -> str:
    secret = os.environ.get(GITHUB_SECRET_ENV, "").strip()
    if not secret:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "github_webhook_secret_missing",
                "message": "GitHub webhook secret is not configured",
                "details": {"env": GITHUB_SECRET_ENV},
            },
        )
    return secret


def expected_github_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_github_signature(*, secret: str, body: bytes, signature: str | None) -> None:
    if not signature:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "missing_github_signature",
                "message": "GitHub webhook signature is required",
                "details": {"header": GITHUB_SIGNATURE_HEADER},
            },
        )

    if not hmac.compare_digest(signature, expected_github_signature(secret, body)):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "invalid_github_signature",
                "message": "GitHub webhook signature is invalid",
                "details": {"header": GITHUB_SIGNATURE_HEADER},
            },
        )


def build_github_webhook_response(*, event: str | None, delivery_id: str | None) -> GitHubWebhookAccepted:
    if not event:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "missing_github_event",
                "message": "GitHub webhook event header is required",
                "details": {"header": "x-github-event"},
            },
        )
    if not delivery_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "missing_github_delivery",
                "message": "GitHub webhook delivery header is required",
                "details": {"header": "x-github-delivery"},
            },
        )
    return GitHubWebhookAccepted(event=event, delivery_id=delivery_id)
