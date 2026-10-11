"""Health must attest the configured route, not merely a listening service."""
from copy import deepcopy
import pytest
from devcore_engine.infra.llm_route_contract import profile, PORTS, validate_health


def health(route):
    return {"service": "headroom-devcore", "route": route, "status": "ready",
            "port": PORTS[route], "profile": profile(route)}


@pytest.mark.parametrize("route", ["native", "auxiliary"])
def test_complete_route_health(route):
    assert validate_health(health(route), route)
    assert not validate_health(health(route), "auxiliary" if route == "native" else "native")


@pytest.mark.parametrize("field,value", [("service", "headroom"), ("status", "healthy"),
    ("status", "not_ready"), ("route", "auxiliary"), ("port", "8787"),
    ("port", True), ("port", 8789), ("profile", {})])
def test_identity_alone_never_qualifies_route(field, value):
    payload = health("native")
    payload[field] = value
    assert not validate_health(payload, "native")


@pytest.mark.parametrize("route", ["native", "auxiliary"])
@pytest.mark.parametrize("field", list(profile("native")))
def test_every_profile_field_is_required_with_exact_type(route, field):
    payload = health(route)
    del payload["profile"][field]
    assert not validate_health(payload, route)
    payload = health(route)
    payload["profile"][field] = "incorrect"
    assert not validate_health(payload, route)


@pytest.mark.parametrize("value", [{}, [], None, "ready"])
def test_invalid_health_document(value):
    assert not validate_health(value, "native")


def test_native_upstream_cannot_be_replaced_by_router():
    payload = health("native")
    payload["profile"]["openai_api_url"] = "http://127.0.0.1:20130"
    assert not validate_health(payload, "native")
    payload = health("native")
    payload["profile"]["model_router"] = {"enabled": True}
    assert not validate_health(payload, "native")


def test_boolean_numbers_not_accepted_and_profile_copy_independent():
    payload = health("native")
    payload["profile"]["stateless"] = 1
    assert not validate_health(payload, "native")
    first = profile("native")
    first["openai_api_url"] = "fixture"
    assert profile("native")["openai_api_url"] == "https://api.openai.com"
