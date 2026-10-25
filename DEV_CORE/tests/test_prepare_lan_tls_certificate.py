"""The LAN certificate is created only in a protected local Security root."""
from __future__ import annotations

import ipaddress
from pathlib import Path

import pytest

from Scripts.prepare_lan_tls_certificate import create
from Scripts.launch_individual_candidate import lan_tls_settings
from devcore_engine.security.private_store import initialize_private_store


@pytest.mark.skipif(__import__("os").name != "nt", reason="NTFS protection required")
def test_create_private_lan_certificate_on_isolated_root(tmp_path):
    local = tmp_path / "local"
    security = local / "Security"
    security.mkdir(parents=True)
    initialize_private_store(security / "identity.db")

    result = create(local, "172.16.210.32")
    assert result["status"] == "lan_tls_certificate_created"
    assert result["address"] == "172.16.210.32"
    cert, key = Path(result["certificate"]), Path(result["key"])
    settings = lan_tls_settings("172.16.210.32", cert, key, 20129)
    assert settings["origin"] == "https://172.16.210.32:20129"
    from cryptography import x509
    certificate = x509.load_pem_x509_certificate(cert.read_bytes())
    san = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert ipaddress.ip_address("172.16.210.32") in san.get_values_for_type(x509.IPAddress)
    with pytest.raises(ValueError, match="already exists"):
        create(local, "172.16.210.32")
