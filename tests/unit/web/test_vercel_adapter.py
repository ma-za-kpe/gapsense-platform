"""Production adapter tests for Vercel's single Python function."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from gapsense.web.vercel import preserve_forwarded_path


def _backend() -> FastAPI:
    backend = FastAPI()

    @backend.get("/v1/health/ready")
    async def readiness() -> dict[str, str]:
        return {"status": "ready"}

    return backend


async def test_vercel_adapter_restores_forwarded_api_path() -> None:
    """The Vercel function rewrite must preserve the public API contract."""
    transport = ASGITransport(app=preserve_forwarded_path(_backend()))
    async with AsyncClient(transport=transport, base_url="https://gapsense.org") as client:
        response = await client.get("/api/index", params={"_path": "v1/health/ready"})

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_vercel_adapter_preserves_unforwarded_requests() -> None:
    """A missing forwarding parameter must not invent an application route."""
    transport = ASGITransport(app=preserve_forwarded_path(_backend()))
    async with AsyncClient(transport=transport, base_url="https://gapsense.org") as client:
        response = await client.get("/api/index")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
