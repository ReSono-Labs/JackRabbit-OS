from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


_ALLOWED_SCHEMES = {"http", "https"}
_METADATA_ADDRESSES = {ipaddress.ip_address("169.254.169.254")}


def validate_public_url(raw_url: str, *, target: str = "url") -> str:
    candidate = raw_url.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in _ALLOWED_SCHEMES or not parsed.hostname:
        raise ValueError(f"{target} must use http or https with a valid host.")
    validate_public_host(parsed.hostname, target=target)
    return candidate


def validate_public_host(host: str, *, target: str = "host") -> str:
    candidate = host.strip().strip("[]").casefold()
    if not candidate:
        raise ValueError(f"{target} is required.")
    if candidate in {"localhost", "localhost.localdomain"} or candidate.endswith(".localhost"):
        raise ValueError(f"{target} must not resolve to a local or private network.")
    try:
        literal = ipaddress.ip_address(candidate)
    except ValueError:
        literal = None
    if literal is not None:
        _reject_private(literal, target)
        return candidate
    try:
        results = socket.getaddrinfo(candidate, None, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise ValueError(f"{target} could not be resolved.") from error
    addresses = {item[4][0] for item in results if item and item[4]}
    if not addresses:
        raise ValueError(f"{target} could not be resolved.")
    for address in addresses:
        _reject_private(ipaddress.ip_address(address), target)
    return candidate


def assert_redirect_safe(
    original_url: str,
    redirect_url: str,
    *,
    allow_host_change: bool = True,
    target: str = "url",
) -> str:
    safe_url = validate_public_url(redirect_url, target=target)
    if not allow_host_change:
        original = (urlparse(original_url).hostname or "").casefold()
        redirected = (urlparse(safe_url).hostname or "").casefold()
        if original != redirected:
            raise ValueError(f"{target} redirect changed hosts.")
    return safe_url


def _reject_private(address: ipaddress.IPv4Address | ipaddress.IPv6Address, target: str) -> None:
    if (
        address in _METADATA_ADDRESSES
        or address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise ValueError(f"{target} must not resolve to a local or private network.")
