"""SSRF guard for user-submitted URLs.

Only http/https. Hosts resolving to private, loopback, link-local, multicast or reserved
addresses are blocked, except the backend's own fixture origin (offline samples).
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlsplit

from app.config import Settings, get_settings

Resolver = Callable[[str, int], list[str]]


class BlockedURL(ValueError):
    pass


def _system_resolver(host: str, port: int) -> list[str]:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [info[4][0] for info in infos]


resolver: Resolver = _system_resolver


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def is_fixture_url(url: str, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    parts = urlsplit(url)
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError:
        return False
    return (parts.scheme, (parts.hostname or "").lower(), port) == settings.fixture_origin


def check_url(url: str, settings: Settings | None = None) -> None:
    """Raise BlockedURL unless `url` is safe to fetch."""
    settings = settings or get_settings()
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise BlockedURL("invalid url") from exc
    if parts.scheme not in ("http", "https"):
        raise BlockedURL("only http and https urls are allowed")
    host = (parts.hostname or "").lower()
    if not host:
        raise BlockedURL("url has no host")
    if parts.username or parts.password:
        raise BlockedURL("credentials in url are not allowed")
    if is_fixture_url(url, settings):
        return
    port = port or (443 if parts.scheme == "https" else 80)
    try:
        addresses = [str(ipaddress.ip_address(host))]
    except ValueError:
        try:
            addresses = resolver(host, port)
        except OSError as exc:
            raise BlockedURL("host cannot be resolved") from exc
    if not addresses:
        raise BlockedURL("host cannot be resolved")
    for address in addresses:
        try:
            public = _is_public(address)
        except ValueError:
            public = False
        if not public:
            raise BlockedURL("target address is not public")
