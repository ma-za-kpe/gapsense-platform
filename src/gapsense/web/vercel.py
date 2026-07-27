"""Small ASGI adapter for Vercel's file-function rewrite boundary."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import parse_qs

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send


def preserve_forwarded_path(backend: ASGIApp) -> ASGIApp:
    """Restore the public path carried through the single Python function."""

    async def application(scope: Scope, receive: Receive, send: Send) -> None:
        query = parse_qs(scope.get("query_string", b"").decode("utf-8"))
        forwarded_path = query.get("_path")
        if forwarded_path:
            route_path = f"/{forwarded_path[0].lstrip('/')}"
            scope = {**scope, "path": route_path, "raw_path": route_path.encode("utf-8")}
        await backend(scope, receive, send)

    return application
