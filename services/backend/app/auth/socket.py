"""Socket.IO needs the same session cookie: an ASGI gate in front of /socket.io refuses the
HTTP long-poll and the WebSocket upgrade before the Socket.IO server sees them."""

from __future__ import annotations

from typing import Any

from app.auth.tokens import cookie_from_header, decode

ASGIApp = Any


def _cookie(scope: dict) -> str | None:
    for name, value in scope.get("headers") or []:
        if name == b"cookie":
            return cookie_from_header(value.decode("latin-1"))
    return None


class SocketAuthGate:
    def __init__(self, app: ASGIApp, path: str = "/socket.io") -> None:
        self.app = app
        self.path = path.rstrip("/")

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        path = str(scope.get("path") or "")
        guarded = scope.get("type") in ("http", "websocket") and (
            path == self.path or path.startswith(self.path + "/")
        )
        if guarded and decode(_cookie(scope)) is None:
            if scope["type"] == "websocket":
                await receive()  # websocket.connect; closing before accept rejects the handshake (403)
                await send({"type": "websocket.close", "code": 1008})
                return
            body = b'{"detail":"authentication required"}'
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)
