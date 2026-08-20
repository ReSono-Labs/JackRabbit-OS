from __future__ import annotations

import ipaddress
import socket


class UnsafeOutboundHost(ValueError):
    pass


def validate_public_host(host: str, port: int) -> str:
    """Resolve a provider host and reject every non-public destination."""
    normalized, _ = resolve_public_host(host, port)
    return normalized


def resolve_public_host(host: str, port: int) -> tuple[str, tuple[str, ...]]:
    """Return only public resolved addresses so callers can pin their socket."""
    normalized = host.strip().rstrip(".").casefold()
    if not normalized or normalized == "localhost":
        raise UnsafeOutboundHost("Provider host must resolve only to public addresses.")
    try:
        addresses = socket.getaddrinfo(normalized, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise UnsafeOutboundHost("Provider host could not be resolved.") from error
    if not addresses:
        raise UnsafeOutboundHost("Provider host could not be resolved.")
    resolved = tuple(sorted({item[4][0] for item in addresses}))
    for address in resolved:
        parsed = ipaddress.ip_address(address)
        if not parsed.is_global:
            raise UnsafeOutboundHost("Provider host must resolve only to public addresses.")
    return normalized, resolved
