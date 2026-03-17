"""
Context dataclass for the image analysis pipeline.

Carries all state through each orchestration step so each
step has a clear, explicit contract: receive context, mutate
its own fields, return nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ImageAnalysisContext:
    # ── Input (from SQS payload) ──────────────────────────────────────────
    s3_key: str
    student_id: str
    country_code: str
    language: str
    teacher_phone: str

    # ── Resolved in Step 1: load_student_context ──────────────────────────
    student: Any = None  # ORM Student instance
    country_key: str = ""  # ISO country code, e.g. "GH"
    subject: str = ""  # e.g. "mathematics"
    student_grade: str = ""  # e.g. "JHS1"

    # ── Resolved in Step 2: fetch_image ───────────────────────────────────
    image_bytes: bytes = b""
    media_type: str = "image/jpeg"

    # ── Resolved in Step 3: transcribe_image (NEW) ────────────────────────
    transcription_text: str = ""
    transcription_result: dict = field(default_factory=dict)

    # ── Resolved in Step 4: build_curriculum_graph ────────────────────────
    curriculum_graph_json: str = ""

    # ── Resolved in Step 4: build_curriculum_graph (Phase 2) ─────────────
    retrieval_metadata: dict[str, Any] = field(default_factory=dict)
    image_description: str = ""

    # ── Resolved in Step 5: render_prompt ─────────────────────────────────
    rendered_prompt: Any = None  # RenderedPrompt from PromptService

    # ── Resolved in Step 6: call_ai ───────────────────────────────────────
    ai_response: Any = None  # AIResponse from async_client

    # ── Metadata ──────────────────────────────────────────────────────────
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
