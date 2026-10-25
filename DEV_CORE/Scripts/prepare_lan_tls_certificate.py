"""Create a short-lived DevCore LAN TLS certificate in a private NTFS directory.

The public certificate can be copied to a pilot client for explicit trust.
The private key stays in the service's local Security root.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import ipaddress
import json
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from devcore_engine.security.private_store import check_store_protection
from devcore_engine.security.secret_files import (
    check_credential_file, protect_empty_directory, protect_reserved_file,
)


def private_lan_address(value: str):
    address = ipaddress.ip_address(value)
    blocks = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
    if address.version != 4 or not any(address in ipaddress.ip_network(block) for block in blocks):
        raise ValueError("An exact private IPv4 LAN address is required")
    return address


def create(local_root: Path, address_text: str) -> dict:
    local_root = Path(local_root)
    if not local_root.is_absolute() or local_root.is_symlink() or local_root.is_junction():
        raise ValueError("An ordinary absolute local root is required")
    address = private_lan_address(address_text)
    identity = local_root / "Security" / "identity.db"
    check_store_protection(identity)
    directory = identity.parent / "lan-tls"
    if directory.exists() or directory.is_symlink() or directory.is_junction():
        raise ValueError("LAN TLS directory already exists; refusing replacement")
    directory.mkdir()
    protect_empty_directory(directory)

    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"DevCore pilot {address}")])
    now = datetime.now(timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                   .public_key(key.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(now - timedelta(minutes=5))
                   .not_valid_after(now + timedelta(days=30))
                   .add_extension(x509.SubjectAlternativeName([x509.IPAddress(address)]), critical=False)
                   .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                   .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                   .sign(key, hashes.SHA256()))
    outputs = (
        (directory / "key.pem", key.private_bytes(serialization.Encoding.PEM,
                                                  serialization.PrivateFormat.PKCS8,
                                                  serialization.NoEncryption())),
        (directory / "cert.pem", certificate.public_bytes(serialization.Encoding.PEM)),
    )
    for path, data in outputs:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        protect_reserved_file(path)
        with path.open("wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        check_credential_file(path)
    return {"status": "lan_tls_certificate_created", "address": str(address),
            "certificate": str(directory / "cert.pem"), "key": str(directory / "key.pem"),
            "valid_until": certificate.not_valid_after_utc.isoformat(),
            "sha256_fingerprint": certificate.fingerprint(hashes.SHA256()).hex()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-root", type=Path, required=True)
    parser.add_argument("--address", required=True)
    args = parser.parse_args()
    print(json.dumps(create(args.local_root, args.address), separators=(",", ":")))


if __name__ == "__main__":
    main()
