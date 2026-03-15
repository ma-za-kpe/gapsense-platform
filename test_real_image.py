"""Test exercise book analysis with real image."""

import asyncio
import base64


async def test_real_image_analysis():
    """Test with actual mth.jpeg image."""
    from gapsense.ai.async_client import AsyncAIClient, ImageContent
    from gapsense.ai.prompt_service import PromptService
    from gapsense.config import settings

    # Read the real image
    image_path = "/app/mth.jpeg"
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    print(f"✅ Loaded image: {len(image_bytes)} bytes")

    # Encode to base64
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    # Initialize services
    ai_client = AsyncAIClient(
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        grok_api_key=settings.GROK_API_KEY,
    )

    prompt_service = PromptService(settings)
    print(f"✅ Loaded {len(prompt_service.list_prompts())} prompts")

    # Get ANALYSIS-001 prompt
    rendered = prompt_service.render_prompt(
        prompt_id="ANALYSIS-001",
        country="ghana",
        extra_context={
            "student_name": "Test Student",
            "current_grade": "JHS1",
            "school_name": "Test School",
            "curriculum_nodes_json": "[]",
        },
    )

    print(f"\n📝 Using prompt: {rendered.prompt_id}")
    print(f"   Model: {rendered.model}")
    print(f"   Temperature: {rendered.temperature}")

    # Create image content
    images = [ImageContent(data=image_base64, media_type="image/jpeg", source_type="base64")]

    # Call AI
    print("\n🤖 Calling Claude Haiku 4.5 with image...")
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

    # Show results
    if response:
        print("\n✅ Analysis completed!")
        print(f"   Provider: {response.provider}")
        print(f"   Model: {response.model}")
        print(f"   Latency: {response.latency_ms:.0f}ms")
        print(f"   Tokens: {response.input_tokens} in, {response.output_tokens} out")

        # Calculate cost
        from gapsense.ai.cost_calculator import calculate_cost, format_cost

        input_cost, output_cost, total_cost = calculate_cost(
            provider=response.provider,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
        print(
            f"   Cost: {format_cost(total_cost)} (input: {format_cost(input_cost)}, output: {format_cost(output_cost)})"
        )

        # Show analysis
        if response.json_parsed:
            print("\n📊 Analysis Result:")
            import json

            print(json.dumps(response.json_parsed, indent=2))
        else:
            print("\n📄 Raw Response:")
            print(response.text[:500])
    else:
        print("❌ Analysis failed - all providers unavailable")

    await ai_client.close()


if __name__ == "__main__":
    print("=" * 60)
    print("EXERCISE BOOK ANALYSIS - REAL IMAGE TEST")
    print("=" * 60)

    asyncio.run(test_real_image_analysis())

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
