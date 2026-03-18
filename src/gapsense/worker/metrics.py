"""
GapSense Worker Metrics (Phase 4)

Emit structured log events that can be aggregated into operational dashboards.
All events follow the pattern: {metric_name, value, dimensions, timestamp}

Key metrics tracked:
  - task_processing_time_ms (by task_type)
  - task_success_rate (by task_type)
  - task_retry_count (by task_type)
  - curriculum_nodes_injected (per analysis)
  - transcription_quality (legibility distribution)
  - ai_cost_per_analysis_usd (rolling average)
  - vector_search_fallback_rate (indicates embedding job staleness)
  - prerequisite_edges_traversed (per analysis)
  - dlq_depth (alert if > 10 sustained)

Usage:
    from gapsense.worker.metrics import emit_analysis_metrics

    # At the end of image analysis pipeline:
    emit_analysis_metrics(ctx, success=True, latency_ms=12340.5)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from gapsense.services.image_analysis_context import ImageAnalysisContext

logger = structlog.get_logger(__name__)


def emit_analysis_metrics(
    ctx: ImageAnalysisContext,
    success: bool,
    latency_ms: float,
) -> None:
    """Emit structured metrics after each image analysis.

    This function is called at the end of the image analysis pipeline
    (success or failure) to emit operational metrics for dashboards.

    Args:
        ctx: The ImageAnalysisContext containing all pipeline state
        success: Whether the analysis completed successfully
        latency_ms: Total pipeline latency in milliseconds

    Example structured log output:
        {
            "event": "analysis_metrics",
            "student_id": "123e4567-e89b-12d3-a456-426614174000",
            "country": "ghana",
            "subject": "mathematics",
            "grade": "B7",
            "success": true,
            "latency_ms": 12340.5,
            "nodes_injected": 15,
            "seed_nodes": 8,
            "prerequisite_nodes": 7,
            "transcription_legibility": "high",
            "questions_transcribed": 5,
            "gaps_found": 3,
            "ai_confidence": 0.85
        }
    """
    # Extract gaps from AI response if available
    gaps_found = 0
    ai_confidence = None

    if ctx.ai_response and hasattr(ctx.ai_response, "json_parsed") and ctx.ai_response.json_parsed:
        gap_node_ids = ctx.ai_response.json_parsed.get("gap_node_ids", [])
        gaps_found = len(gap_node_ids) if gap_node_ids else 0
        ai_confidence = ctx.ai_response.json_parsed.get("confidence")

    # Extract transcription metadata
    transcription_legibility = None
    questions_transcribed = 0

    if ctx.transcription_result:
        transcription_legibility = ctx.transcription_result.get("overall_legibility")
        questions = ctx.transcription_result.get("questions", [])
        questions_transcribed = len(questions) if questions else 0

    # Extract curriculum retrieval metadata
    nodes_injected = ctx.retrieval_metadata.get("total_nodes_injected", 0)
    seed_nodes = len(ctx.retrieval_metadata.get("seed_node_ids", []))
    prerequisite_nodes = len(ctx.retrieval_metadata.get("prerequisite_node_ids", []))

    logger.info(
        "analysis_metrics",
        student_id=str(ctx.student_id),
        country=ctx.country_key,
        subject=ctx.subject,
        grade=ctx.student_grade,
        success=success,
        latency_ms=round(latency_ms, 2),
        nodes_injected=nodes_injected,
        seed_nodes=seed_nodes,
        prerequisite_nodes=prerequisite_nodes,
        transcription_legibility=transcription_legibility,
        questions_transcribed=questions_transcribed,
        gaps_found=gaps_found,
        ai_confidence=ai_confidence,
    )


def emit_task_metrics(
    task_type: str,
    success: bool,
    latency_ms: float,
    retry_count: int = 0,
    **extra_dimensions: Any,
) -> None:
    """Emit structured metrics for any worker task.

    This is a more general version of emit_analysis_metrics that can be
    used for any task type (not just image_analyze).

    Args:
        task_type: The type of task (e.g., "image_analyze", "send_notification")
        success: Whether the task completed successfully
        latency_ms: Total task latency in milliseconds
        retry_count: Number of retries attempted (0 for first attempt)
        **extra_dimensions: Additional dimensions to include in the log event

    Example usage:
        emit_task_metrics(
            task_type="image_analyze",
            success=True,
            latency_ms=12340.5,
            retry_count=0,
            country="ghana",
            subject="mathematics"
        )
    """
    logger.info(
        "task_metrics",
        task_type=task_type,
        success=success,
        latency_ms=round(latency_ms, 2),
        retry_count=retry_count,
        **extra_dimensions,
    )


def emit_vector_search_fallback(
    country: str,
    subject: str,
    grade: str | None = None,
    reason: str = "no_embeddings",
) -> None:
    """Emit metric when vector search falls back to code-ordered retrieval.

    High fallback rate indicates that the embedding job is stale or failed.

    Args:
        country: Country code (e.g., "ghana", "uganda")
        subject: Subject (e.g., "mathematics")
        grade: Student grade (e.g., "B7")
        reason: Why fallback occurred (e.g., "no_embeddings", "zero_results")
    """
    logger.warning(
        "vector_search_fallback",
        country=country,
        subject=subject,
        grade=grade,
        reason=reason,
        message="Vector search yielded no results. Using code-ordered fallback.",
    )


def emit_dlq_depth(queue_name: str, depth: int) -> None:
    """Emit metric for dead-letter queue depth.

    Alert if depth > 10 sustained.

    Args:
        queue_name: Name of the DLQ (e.g., "gapsense-worker-dlq")
        depth: Number of messages in the DLQ
    """
    level = "warning" if depth > 10 else "info"

    logger.log(
        level,
        "dlq_depth",
        queue_name=queue_name,
        depth=depth,
        message=f"DLQ depth: {depth} messages",
    )


def emit_ai_cost(
    task_type: str,
    model: str,
    cost_usd: float,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Emit AI cost metrics for billing and budgeting.

    Args:
        task_type: The task that incurred the cost (e.g., "image_analyze")
        model: The AI model used (e.g., "claude-3-sonnet-20240229")
        cost_usd: Total cost in USD
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
    """
    logger.info(
        "ai_cost",
        task_type=task_type,
        model=model,
        cost_usd=round(cost_usd, 4),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def emit_heartbeat_event(
    task_type: str,
    message_id: str,
    visibility_extension_seconds: int,
) -> None:
    """Emit heartbeat event when SQS visibility timeout is extended.

    Used to verify that the heartbeat mechanism is working correctly.

    Args:
        task_type: The task type being processed
        message_id: SQS message ID
        visibility_extension_seconds: How many seconds visibility was extended
    """
    logger.debug(
        "sqs_heartbeat",
        task_type=task_type,
        message_id=message_id,
        visibility_extension_seconds=visibility_extension_seconds,
    )
