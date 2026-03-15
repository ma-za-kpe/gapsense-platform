"""Generate complete exercise book analysis report with database audit trail."""
import asyncio
import base64
import json
from datetime import datetime


async def generate_report():
    """Generate full analysis report with database data."""
    from gapsense.ai.async_client import AsyncAIClient, ImageContent
    from gapsense.ai.cost_calculator import calculate_cost, format_cost
    from gapsense.ai.prompt_service import PromptService
    from gapsense.config import settings
    from gapsense.core.database import AsyncSessionLocal
    from gapsense.core.models import AIUsageLog, School, Student
    from sqlalchemy import select

    # Read the exercise book image
    image_path = "/app/exercise_book.png"
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # Initialize services
    ai_client = AsyncAIClient(
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        grok_api_key=settings.GROK_API_KEY,
    )

    prompt_service = PromptService(settings)

    # Get student from database
    async with AsyncSessionLocal() as db:
        # Get first Ghana student for demo
        result = await db.execute(
            select(Student)
            .join(School)
            .where(Student.is_active == True)
            .limit(1)
        )
        student = result.scalar_one_or_none()

        if not student:
            print("❌ No student found in database")
            return

        # Load school
        await db.refresh(student, ["school"])

        print(f"✅ Found student: {student.full_name}")
        print(f"   School: {student.school.name}")
        print(f"   Grade: {student.current_grade}")

        # Render prompt
        rendered = prompt_service.render_prompt(
            prompt_id="ANALYSIS-001",
            country="ghana",
            extra_context={
                "student_name": student.full_name,
                "current_grade": student.current_grade,
                "school_name": student.school.name,
                "curriculum_nodes_json": "[]",
            },
        )

        # Prepare image
        images = [
            ImageContent(
                data=base64.b64encode(image_bytes).decode("utf-8"),
                media_type="image/png",
                source_type="base64",
            )
        ]

        # Call AI
        print(f"\n🤖 Analyzing with {rendered.model}...")
        response = await ai_client.generate(
            prompt_id=rendered.prompt_id,
            system=rendered.system_prompt,
            messages=[{"role": "user", "content": rendered.user_template}],
            model=rendered.model,
            max_tokens=rendered.max_tokens,
            temperature=rendered.temperature,
            json_mode=True,
            images=images,
        )

        if not response:
            print("❌ AI analysis failed")
            return

        # Calculate cost
        input_cost, output_cost, total_cost = calculate_cost(
            provider=response.provider,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )

        # Log to database
        from gapsense.core.models import AIUsageLog

        usage_log = AIUsageLog(
            student_id=student.id,
            teacher_id=student.teacher_id,
            provider=response.provider,
            model=response.model,
            prompt_id=response.prompt_id,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            total_cost_usd=total_cost,
            latency_ms=response.latency_ms,
            success=True,
            error_message=None,
        )
        db.add(usage_log)
        await db.commit()
        await db.refresh(usage_log)

        print(f"✅ Logged to database: AIUsageLog ID {usage_log.id}")

        # Get recent AI usage for this student
        usage_result = await db.execute(
            select(AIUsageLog)
            .where(AIUsageLog.student_id == student.id)
            .order_by(AIUsageLog.created_at.desc())
            .limit(5)
        )
        recent_usage = usage_result.scalars().all()

        # Parse AI response
        ai_analysis = None
        if response.text:
            # Strip markdown code fences
            text = response.text.strip()
            if text.startswith("```json"):
                text = text.removeprefix("```json").removesuffix("```").strip()
            elif text.startswith("```"):
                text = text.removeprefix("```").removesuffix("```").strip()

            try:
                ai_analysis = json.loads(text)
            except json.JSONDecodeError:
                ai_analysis = {"raw_text": response.text}

        # Generate report
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("GAPSENSE EXERCISE BOOK ANALYSIS REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report_lines.append(f"Report ID: {usage_log.id}")
        report_lines.append("")

        # SECTION 1: Student Information (from database)
        report_lines.append("=" * 80)
        report_lines.append("STUDENT INFORMATION (Database)")
        report_lines.append("=" * 80)
        report_lines.append(f"Student ID: {student.id}")
        report_lines.append(f"Name: {student.full_name}")
        report_lines.append(f"Age: {student.age or 'N/A'}")
        report_lines.append(f"Gender: {student.gender or 'N/A'}")
        report_lines.append(f"Current Grade: {student.current_grade}")
        report_lines.append(f"School: {student.school.name}")
        report_lines.append(f"School Type: {student.school.school_type}")
        report_lines.append(f"Home Language: {student.home_language or 'N/A'}")
        report_lines.append(f"School Language: {student.school_language or 'English'}")
        report_lines.append(f"Previous Diagnoses: {student.diagnosis_count}")
        if student.last_diagnosed_at:
            report_lines.append(
                f"Last Diagnosed: {student.last_diagnosed_at.strftime('%Y-%m-%d')}"
            )
        report_lines.append("")

        # SECTION 2: AI Analysis Details (from database)
        report_lines.append("=" * 80)
        report_lines.append("AI ANALYSIS METADATA (Database)")
        report_lines.append("=" * 80)
        report_lines.append(f"Analysis ID: {usage_log.id}")
        report_lines.append(f"Timestamp: {usage_log.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report_lines.append(f"Provider: {usage_log.provider}")
        report_lines.append(f"Model: {usage_log.model}")
        report_lines.append(f"Prompt: {usage_log.prompt_id}")
        report_lines.append(f"Input Tokens: {usage_log.input_tokens:,}")
        report_lines.append(f"Output Tokens: {usage_log.output_tokens:,}")
        report_lines.append(f"Total Tokens: {usage_log.input_tokens + usage_log.output_tokens:,}")
        report_lines.append(f"Latency: {usage_log.latency_ms:.0f}ms ({usage_log.latency_ms/1000:.1f}s)")
        report_lines.append(f"Input Cost: {format_cost(usage_log.input_cost_usd)}")
        report_lines.append(f"Output Cost: {format_cost(usage_log.output_cost_usd)}")
        report_lines.append(f"Total Cost: {format_cost(usage_log.total_cost_usd)}")
        report_lines.append(f"Success: {usage_log.success}")
        report_lines.append("")

        # SECTION 3: AI Analysis Results
        if ai_analysis:
            report_lines.append("=" * 80)
            report_lines.append("ANALYSIS RESULTS")
            report_lines.append("=" * 80)
            report_lines.append(f"Topic: {ai_analysis.get('topic_identified', 'N/A')}")
            report_lines.append(f"Readable: {not ai_analysis.get('unreadable', True)}")
            report_lines.append(f"Confidence: {ai_analysis.get('confidence', 0) * 100:.0f}%")
            report_lines.append(f"Student Approach: {ai_analysis.get('student_approach', 'N/A')}")
            report_lines.append("")

            # Errors
            errors = ai_analysis.get("errors", [])
            if errors:
                report_lines.append("ERRORS IDENTIFIED:")
                for i, err in enumerate(errors, 1):
                    report_lines.append(f"\n{i}. {err.get('error_type', 'Unknown').upper()}")
                    report_lines.append(f"   Line {err.get('line_number', 'N/A')}")
                    report_lines.append(f"   {err.get('description', 'N/A')}")
                report_lines.append("")

            # Patterns
            patterns = ai_analysis.get("patterns", [])
            if patterns:
                report_lines.append("ERROR PATTERNS:")
                for pattern in patterns:
                    report_lines.append(f"  • {pattern}")
                report_lines.append("")

            # Gap nodes
            gap_nodes = ai_analysis.get("gap_node_ids", [])
            if gap_nodes:
                report_lines.append("CURRICULUM GAP NODES (NaCCA):")
                for code in gap_nodes:
                    report_lines.append(f"  • {code}")
                report_lines.append("")

            # Focus areas
            focus_areas = ai_analysis.get("focus_areas", [])
            if focus_areas:
                report_lines.append("REMEDIATION FOCUS AREAS:")
                for area in focus_areas:
                    report_lines.append(f"  • {area}")
                report_lines.append("")

            # Reasoning
            reasoning = ai_analysis.get("reasoning", "")
            if reasoning:
                report_lines.append("AI REASONING:")
                report_lines.append(reasoning)
                report_lines.append("")

        # SECTION 4: Historical AI Usage (from database)
        report_lines.append("=" * 80)
        report_lines.append("HISTORICAL AI USAGE (Last 5 analyses for this student)")
        report_lines.append("=" * 80)
        if recent_usage:
            for i, log in enumerate(recent_usage, 1):
                report_lines.append(
                    f"{i}. {log.created_at.strftime('%Y-%m-%d %H:%M')} | "
                    f"{log.model} | {log.prompt_id} | "
                    f"{format_cost(log.total_cost_usd)} | "
                    f"{log.latency_ms:.0f}ms | "
                    f"{'✓' if log.success else '✗'}"
                )
        else:
            report_lines.append("No previous analyses found.")
        report_lines.append("")

        # SECTION 5: Raw JSON
        report_lines.append("=" * 80)
        report_lines.append("RAW AI RESPONSE (JSON)")
        report_lines.append("=" * 80)
        if ai_analysis:
            report_lines.append(json.dumps(ai_analysis, indent=2))
        else:
            report_lines.append(response.text)
        report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)

        # Write report
        report_text = "\n".join(report_lines)
        report_filename = f"/app/exercise_book_analysis_report_{usage_log.id}.txt"
        with open(report_filename, "w") as f:
            f.write(report_text)

        print(f"\n✅ Report saved: {report_filename}")
        print(f"\n{report_text}")

        await ai_client.close()
        return report_filename


if __name__ == "__main__":
    asyncio.run(generate_report())
