from __future__ import annotations

from ipaddress import ip_address

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    Lấy IP client khi request có thể đi qua Nginx nội bộ.

    Chỉ tin X-Real-IP nếu peer trực tiếp là private/loopback. Nginx ghi đè
    header này bằng $remote_addr trước khi proxy tới backend.
    """

    peer_ip = request.client.host if request.client else "unknown"

    try:
        parsed_peer = ip_address(peer_ip)
        peer_is_trusted_proxy = (
            parsed_peer.is_private or parsed_peer.is_loopback
        )
    except ValueError:
        peer_is_trusted_proxy = False

    forwarded_ip = request.headers.get("X-Real-IP")
    if peer_is_trusted_proxy and forwarded_ip:
        try:
            return str(ip_address(forwarded_ip.strip()))
        except ValueError:
            pass

    return peer_ip


def get_user_agent(request: Request) -> str | None:
    value = request.headers.get("user-agent")
    if not value:
        return None
    return value[:300]
