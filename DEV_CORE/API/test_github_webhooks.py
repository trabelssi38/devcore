import hashlib
import hmac
import sys
from pathlib import Path

from fastapi.testclient import TestClient


API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def github_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_github_webhook_accepts_valid_signed_ping(monkeypatch) -> None:
    from devcore_api import create_app

    body = b'{"zen":"Keep it logically awesome."}'
    secret = "local-test-secret"
    monkeypatch.setenv("DEVCORE_GITHUB_WEBHOOK_SECRET", secret)

    client = TestClient(create_app())
    response = client.post(
        "/api/v1/integrations/github/webhook",
        content=body,
        headers={
            "content-type": "application/json",
            "x-github-event": "ping",
            "x-github-delivery": "delivery-1",
            "x-hub-signature-256": github_signature(secret, body),
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "schema_version": 1,
        "provider": "github",
        "event": "ping",
        "delivery_id": "delivery-1",
        "accepted": True,
    }


def test_github_webhook_rejects_invalid_signature(monkeypatch) -> None:
    from devcore_api import create_app

    monkeypatch.setenv("DEVCORE_GITHUB_WEBHOOK_SECRET", "local-test-secret")

    client = TestClient(create_app())
    response = client.post(
        "/api/v1/integrations/github/webhook",
        content=b'{"action":"opened"}',
        headers={
            "content-type": "application/json",
            "x-github-event": "pull_request",
            "x-github-delivery": "delivery-2",
            "x-hub-signature-256": "sha256=bad",
        },
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "invalid_github_signature"


def test_github_webhook_requires_configured_secret(monkeypatch) -> None:
    from devcore_api import create_app

    monkeypatch.delenv("DEVCORE_GITHUB_WEBHOOK_SECRET", raising=False)

    client = TestClient(create_app())
    response = client.post(
        "/api/v1/integrations/github/webhook",
        content=b"{}",
        headers={
            "content-type": "application/json",
            "x-github-event": "ping",
            "x-github-delivery": "delivery-3",
            "x-hub-signature-256": "sha256=unused",
        },
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "github_webhook_secret_missing"
