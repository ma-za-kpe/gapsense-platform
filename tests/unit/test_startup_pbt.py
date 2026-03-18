"""
Property-based tests for Application Startup and Health Check.

# Feature: mvp-core-services, Property 19: Health Check Response Completeness
# Feature: mvp-core-services, Property 20: Startup Failure Blocks Application
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Property 19: Health Check Response Completeness
# **Validates: Requirements 13.4**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
@given(
    db_healthy=st.booleans(),
    prompt_healthy=st.booleans(),
    ai_ready=st.booleans(),
    s3_healthy=st.booleans(),
)
async def test_health_check_response_completeness(
    db_healthy: bool,
    prompt_healthy: bool,
    ai_ready: bool,
    s3_healthy: bool,
):
    """Property 19: Health Check Response Completeness

    For any health check call, response contains status entries for:
    database, prompt_library (version + count), AI client readiness, S3 connectivity.
    """
    from fastapi.testclient import TestClient

    # Mock the engine and prompt library
    with (
        patch("gapsense.main.engine") as mock_engine,
        patch("gapsense.main.get_prompt_library") as mock_get_pl,
    ):
        # Setup database mock
        mock_conn = AsyncMock()
        if db_healthy:
            mock_conn.execute = AsyncMock(return_value=None)
        else:
            mock_conn.execute = AsyncMock(side_effect=Exception("DB down"))
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_engine.connect.return_value = mock_conn

        # Setup prompt library mock
        if prompt_healthy:
            mock_pl = MagicMock()
            mock_pl.__len__ = MagicMock(return_value=13)
            mock_pl.metadata = {"version": "2.0"}
            mock_get_pl.return_value = mock_pl
        else:
            mock_get_pl.side_effect = Exception("Prompt library failed")

        # Create app without running lifespan
        from gapsense.main import create_app

        app = create_app()

        # Set app.state for AI client and S3
        app.state.ai_client = MagicMock() if ai_ready else None
        app.state.s3_healthy = s3_healthy
        app.state.media_service = MagicMock() if s3_healthy else None

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/health")
        data = response.json()

        # Verify all required sections are present
        checks = data.get("checks", {})
        assert "database" in checks, f"Missing 'database' in health checks: {checks}"
        assert "prompt_library" in checks, f"Missing 'prompt_library' in health checks: {checks}"
        assert "ai_client" in checks, f"Missing 'ai_client' in health checks: {checks}"
        assert "s3" in checks, f"Missing 's3' in health checks: {checks}"

        # Verify prompt_library has version and count when healthy
        if prompt_healthy:
            pl = checks["prompt_library"]
            assert "version" in pl, f"Missing 'version' in prompt_library check: {pl}"
            assert "prompts" in pl, f"Missing 'prompts' in prompt_library check: {pl}"

        # Verify ai_client has readiness info
        ai = checks["ai_client"]
        assert "ready" in ai or "status" in ai, f"Missing readiness info in ai_client: {ai}"


# ---------------------------------------------------------------------------
# Property 20: Startup Failure Blocks Application
# **Validates: Requirements 13.6**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=30, deadline=None)
@given(
    db_fails=st.just(True),
)
async def test_startup_db_failure_blocks_application(db_fails: bool):
    """Property 20a: When database fails to initialize, application raises exception."""
    from gapsense.main import create_app, lifespan

    app = create_app()

    with patch("gapsense.main.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("DB unreachable"))
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_engine.connect.return_value = mock_conn

        with pytest.raises(Exception, match="DB unreachable"):
            async with lifespan(app):
                pass  # Should not reach here


@pytest.mark.asyncio
@settings(max_examples=30, deadline=None)
@given(
    prompt_fails=st.just(True),
)
async def test_startup_prompt_failure_blocks_application(prompt_fails: bool):
    """Property 20b: When prompt library fails, application raises exception."""
    from gapsense.main import create_app, lifespan

    app = create_app()

    with (
        patch("gapsense.main.engine") as mock_engine,
        patch("gapsense.main.get_prompt_library") as mock_get_pl,
    ):
        # DB succeeds
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_engine.connect.return_value = mock_conn

        # Prompt library fails
        mock_get_pl.side_effect = Exception("Prompt library file missing")

        with pytest.raises(Exception, match="Prompt library file missing"):
            async with lifespan(app):
                pass
