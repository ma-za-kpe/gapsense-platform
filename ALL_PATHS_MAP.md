# GapSense - Complete Path Map (v2 AI-Native Redesign)

**Generated:** 2026-02-17
**Purpose:** Comprehensive build specification for v2 AI-Native architecture
**Alignment:** GapSense v2.0 — The AI-Native Redesign (`docs/gapsense_claude_code_prompt_v2.md`)

**Build Order:** This document is organized in **dependency order** - each section builds on previous sections.

---

## ARCHITECTURE OVERVIEW

### **v2 Core Principle: Invisible Assessment Paradigm**

> "The PRIMARY diagnostic pathway is NOT an explicit test session. It is exercise book photos, teacher conversations, and voice notes. The explicit diagnostic (DIAG-001/002/003) exists as an OPTIONAL deep dive."

### **Current vs. v2 Architecture**

| Aspect | Current (v1) | v2 AI-Native | Status |
|--------|--------------|--------------|--------|
| **Primary Diagnostic** | Explicit quiz | Exercise book photos | ❌ Inverted |
| **Teacher UX** | Roster upload | Conversational partner | ❌ Missing |
| **Gap Updates** | Session-based | Multi-source incremental | ❌ Missing |
| **Parent Value** | Quiz proxy | Personalized activities | ❌ Missing |
| **Compliance** | None | GUARD-001 mandatory | ❌ Missing |

### **Build Sequence Philosophy**

```
LAYER 1: Foundation (AI infrastructure, database, compliance)
  ↓
LAYER 2: Core Value (Activity delivery, gap profile updates)
  ↓
LAYER 3: Diagnostic Sources (Exercise books, conversations, explicit tests)
  ↓
LAYER 4: User Onboarding (Parents, teachers, schools)
  ↓
LAYER 5: Background Processing (SQS workers, scalability)
  ↓
LAYER 6: Teacher Tools (Reports, roster management, dashboard)
  ↓
LAYER 7: Advanced Features (Literacy, re-engagement, analytics)
  ↓
LAYER 8: Governance (Audit, evaluation, analytics)
  ↓
LAYER 9: Future (Phase 2 on-device)
```

---

# LAYER 1: FOUNDATION INFRASTRUCTURE

These must exist before anything else can be built.

---

## FLOW-1: Async AI Client with JSON Mode

**Status:** ❌ **0% Implemented** (Priority #1 - FOUNDATION)

**Entry:** Any service needs to call AI
**Exit:** Structured response returned
**v2 File:** `src/gapsense/ai/client.py` (needs rewrite)

**Why First:** Every AI flow depends on this. Current client is synchronous, returns strings, no JSON mode.

**Architecture:**
```python
class AIClient:
    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str = "claude-sonnet-4-5",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        response_format: Literal["text", "json"] = "text"
    ) -> str:
        """Async AI call with proper error handling."""

        # Try Anthropic first
        try:
            return await self._call_anthropic(...)
        except AnthropicAPIError as e:
            logger.warning(f"Anthropic failed: {e}")

        # Fallback to Grok
        try:
            return await self._call_grok(...)
        except GrokAPIError as e:
            logger.warning(f"Grok failed: {e}")

        # All providers failed
        raise AIProviderUnavailableError("All AI providers failed")
```

**Requirements:**
- Async/await throughout (no blocking)
- JSON mode support (`response_format="json"`)
- Provider fallback (Anthropic → Grok)
- Retry logic (3 attempts with exponential backoff)
- Timeout handling (30s max)
- Rate limiting (50 req/min Anthropic)
- Token counting and logging
- Cost tracking per call

**Error Handling:**
- API down: Retry with backoff, then fail gracefully
- Rate limited: Queue request, retry after delay
- Timeout: Return error, log incident
- Invalid response: Parse error, regenerate once

**Test Cases:**
- `test_async_call_succeeds()`
- `test_fallback_to_grok()`
- `test_json_mode_parsing()`
- `test_timeout_handling()`
- `test_rate_limit_handling()`

---

## FLOW-2: Prompt Library Integration

**Status:** ⚠️ **70% Implemented** (Priority #2 - FOUNDATION)

**Entry:** Service needs to invoke a prompt
**Exit:** AI response with validated schema

**Current:** Prompt library loads ✅, but NO integration with AI client ❌

**What's Missing:**
```python
# Current (WRONG):
client = AIClient()
response = client.generate_completion(
    model="claude-sonnet-4-5",
    system="You are...",  # Hardcoded prompt
    messages=[...]
)

# v2 (CORRECT):
lib = get_prompt_library()
prompt = lib.get_prompt("GUARD-001")

response = await ai_client.generate(
    messages=[
        {"role": "system", "content": prompt["system_prompt"]},
        {"role": "user", "content": formatted_user_message}
    ],
    model=prompt["model"],
    temperature=prompt["temperature"],
    max_tokens=prompt["max_tokens"],
    response_format="json"  # From prompt config
)

# Validate response against prompt["output_schema"]
validated_data = validate_json_schema(response, prompt["output_schema"])
```

**Service Layer:**
```python
class PromptService:
    """High-level prompt invocation with validation."""

    async def invoke(
        self,
        prompt_id: str,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Invoke prompt with context, return validated result."""

        # Load prompt
        prompt = self.prompt_lib.get_prompt(prompt_id)

        # Format user message from template
        user_message = self._format_template(
            prompt["user_template"],
            context
        )

        # Call AI
        response = await self.ai_client.generate(
            messages=[
                {"role": "system", "content": prompt["system_prompt"]},
                {"role": "user", "content": user_message}
            ],
            model=prompt["model"],
            temperature=prompt["temperature"],
            max_tokens=prompt["max_tokens"],
            response_format="json"
        )

        # Validate and parse
        return self._validate_response(response, prompt["output_schema"])
```

**Completion Criteria:**
- ✅ Prompt library loads
- ❌ Service layer exists
- ❌ Template formatting works
- ❌ Schema validation works
- ❌ Integration tests pass

---

## FLOW-3: Multi-Source Gap Profile Updates

**Status:** ❌ **20% Implemented** (Priority #3 - KEY ARCHITECTURE)

**Entry:** Any diagnostic source completes analysis
**Exit:** Gap profile updated incrementally

**Why This First:** All diagnostic flows write to gap profiles. This must exist before any diagnostic flows.

**5 Update Sources:**
```
1. Exercise Book Photo      → source="exercise_book"
2. Teacher Conversation     → source="teacher_observation"
3. Parent Voice Note        → source="parent_observation"
4. Explicit Diagnostic      → source="explicit_diagnostic"  ✅ Only current source
5. Activity Engagement      → source="activity_engagement"
```

**Database Schema:**
```sql
CREATE TABLE gap_profiles (
  id UUID PRIMARY KEY,
  student_id UUID REFERENCES students(id),

  -- Multi-source tracking
  source TEXT CHECK (source IN (
    'exercise_book',
    'teacher_observation',
    'parent_observation',
    'explicit_diagnostic',
    'activity_engagement'
  )),

  -- Gap data (arrays support incremental merge)
  nodes_tested UUID[] DEFAULT '{}',
  nodes_mastered UUID[] DEFAULT '{}',
  nodes_gap UUID[] DEFAULT '{}',

  -- Analysis metadata
  primary_gap_node UUID REFERENCES curriculum_nodes(id),
  primary_cascade TEXT,
  overall_confidence FLOAT CHECK (overall_confidence BETWEEN 0 AND 1),

  -- Lifecycle
  is_current BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Only one current profile per student (PostgreSQL partial index)
CREATE UNIQUE INDEX idx_one_current_per_student
  ON gap_profiles(student_id)
  WHERE is_current = TRUE;
```

**Service Implementation:**
```python
class GapProfileService:
    """Multi-source gap profile management."""

    async def update_from_source(
        self,
        student_id: UUID,
        source: str,
        nodes_tested: list[UUID],
        nodes_gap: list[UUID],
        nodes_mastered: list[UUID],
        confidence: float = 0.7
    ) -> GapProfile:
        """Incrementally update gap profile from any source."""

        # Get current profile (or create if first time)
        profile = await self._get_or_create_current_profile(student_id)

        # Merge new data (set union, not replacement)
        profile.nodes_tested = list(set(profile.nodes_tested + nodes_tested))
        profile.nodes_gap = list(set(profile.nodes_gap + nodes_gap))
        profile.nodes_mastered = list(set(profile.nodes_mastered + nodes_mastered))

        # Remove mastered nodes from gap list (they're fixed)
        profile.nodes_gap = [
            n for n in profile.nodes_gap
            if n not in profile.nodes_mastered
        ]

        # Update metadata
        profile.source = source  # Last update source
        profile.updated_at = datetime.now(UTC)

        # Re-calculate primary gap and confidence
        profile.primary_gap_node = await self._identify_primary_gap(profile)
        profile.overall_confidence = await self._calculate_confidence(profile)

        await self.db.commit()
        return profile

    async def _get_or_create_current_profile(
        self,
        student_id: UUID
    ) -> GapProfile:
        """Get current profile or create new one."""

        result = await self.db.execute(
            select(GapProfile)
            .where(
                GapProfile.student_id == student_id,
                GapProfile.is_current == True
            )
        )
        profile = result.scalar_one_or_none()

        if profile is None:
            # First profile for this student
            profile = GapProfile(
                student_id=student_id,
                nodes_tested=[],
                nodes_mastered=[],
                nodes_gap=[],
                is_current=True
            )
            self.db.add(profile)

        return profile
```

**Completion Criteria:**
- ✅ Database schema with partial index
- ❌ Service layer with incremental merge
- ❌ Handles all 5 sources
- ❌ Confidence calculation
- ❌ Primary gap identification
- ❌ Integration tests

---

## FLOW-4: AI Reasoning Log

**Status:** ⚠️ **30% Implemented** (Priority #4 - COMPLIANCE)

**Entry:** Every AI API call
**Exit:** Full reasoning logged to database

**Why Now:** Before any AI flows go to production, audit trail must exist (Ghana Data Protection Act compliance).

**Database Schema:**
```sql
CREATE TABLE ai_reasoning_log (
  id UUID PRIMARY KEY,

  -- Request
  prompt_id TEXT NOT NULL,  -- e.g., "GUARD-001"
  model TEXT NOT NULL,
  temperature FLOAT,
  max_tokens INTEGER,
  input_context JSONB,  -- Variables passed to template

  -- Response
  response_text TEXT,
  response_json JSONB,  -- Parsed if JSON mode

  -- Metrics
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  cached_tokens INTEGER,
  latency_ms INTEGER,
  cost_usd NUMERIC(10, 6),

  -- Audit
  student_id UUID REFERENCES students(id),  -- For student privacy tracking
  parent_id UUID REFERENCES parents(id),
  teacher_id UUID REFERENCES teachers(id),

  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Encrypted at rest (compliance requirement)
-- Indexes for audit queries
CREATE INDEX idx_ai_log_prompt ON ai_reasoning_log(prompt_id, created_at);
CREATE INDEX idx_ai_log_student ON ai_reasoning_log(student_id);
```

**Integration:**
```python
class AIClient:
    async def generate(self, ...) -> str:
        # Before call
        log_entry = AIReasoningLog(
            prompt_id=prompt_id,
            model=model,
            temperature=temperature,
            input_context=context
        )

        start_time = time.time()

        # Make call
        response = await self._call_api(...)

        # After call
        log_entry.response_text = response
        log_entry.latency_ms = int((time.time() - start_time) * 1000)
        log_entry.cost_usd = self._calculate_cost(usage)

        await self.db.add(log_entry)
        await self.db.commit()

        return response
```

**Use Cases:**
- Regulatory compliance (data audit trail)
- Debugging ("Why did AI say this?")
- Cost tracking (per-student AI spend)
- Prompt refinement (which prompts perform well?)

---

# LAYER 2: SAFETY & VALUE DELIVERY

Core systems that enable safe parent engagement.

---

## FLOW-5: GUARD-001 Compliance Gate 🚨

**Status:** ❌ **0% Implemented** (Priority #5 - PRODUCTION BLOCKER)

**Entry:** ANY parent-facing message generated
**Exit:** Message approved OR blocked

**Why Critical:** Wolf/Aurino research proves deficit messaging destroys engagement (2x retention difference). Without this, GapSense causes harm.

**Compliance Rules (Non-Negotiable):**
```
❌ NEVER USE (Deficit Language):
  "behind", "struggling", "failing", "weak", "poor"
  "below grade level", "deficit", "needs improvement"
  "slow learner", "not ready", "can't do"

❌ NEVER USE (Jargon):
  "diagnostic", "assessment", "remediation"
  "curriculum", "prerequisite", "misconception"
  "intervention", "scaffolding", "differentiation"

❌ NEVER MENTION:
  Other children ("Kwame is behind the class")
  Grade-level expectations ("should be at JHS 1 level")
  Parent's literacy level

✅ ALWAYS DO:
  Lead with strength ("Kwame can count to 20!")
  Use parent's L1 language
  Local materials only (bottle caps, stones, beans, paper)
  200-300 words max
  ONE activity, not multiple
  Encouraging, dignifying tone
```

**Implementation:**
```python
class ComplianceGuard:
    """GUARD-001 implementation with regeneration loop."""

    async def validate_with_regeneration(
        self,
        message_text: str,
        parent_name: str,
        child_name: str,
        current_grade: str,
        regenerate_callback: Callable,
        max_attempts: int = 2
    ) -> tuple[bool, str | None]:
        """
        Validate message, regenerate if needed, block if double-reject.

        Returns:
            (approved, final_message_or_None)
            If None: BLOCKED - human review required
        """

        # Initial validation
        result = await self._check_compliance(
            message_text, parent_name, child_name, current_grade
        )

        if result["approved"]:
            logger.info("GUARD-001: Message approved on first check")
            return True, message_text

        # Rejected - attempt regeneration
        logger.warning(f"GUARD-001 rejected: {result['issues']}")

        for attempt in range(max_attempts):
            # Regenerate with feedback
            regenerated = await regenerate_callback(
                original=message_text,
                feedback=result["issues"]
            )

            # Re-check
            result = await self._check_compliance(
                regenerated, parent_name, child_name, current_grade
            )

            if result["approved"]:
                logger.info(f"GUARD-001: Approved after regeneration #{attempt+1}")
                return True, regenerated

        # Double-reject: BLOCK SEND
        logger.error(
            f"GUARD-001 BLOCKED after {max_attempts} attempts. "
            f"Reasons: {result['issues']}. MANUAL REVIEW REQUIRED."
        )

        # Alert admin
        await self._alert_admin_blocked_message(
            message_text, result["issues"]
        )

        return False, None  # BLOCKED

    async def _check_compliance(
        self,
        message_text: str,
        parent_name: str,
        child_name: str,
        current_grade: str
    ) -> dict[str, Any]:
        """Call GUARD-001 prompt (temp=0.0 for determinism)."""

        prompt = self.prompt_lib.get_prompt("GUARD-001")

        # Format context
        context = {
            "message_text": message_text,
            "parent_name": parent_name,
            "child_name": child_name,
            "current_grade": current_grade,
            "literacy_level": "medium",  # TODO: Get from parent profile
            "preferred_language": "en"   # TODO: Get from parent profile
        }

        # Call AI (temp=0.0 for consistency)
        response = await self.prompt_service.invoke("GUARD-001", context)

        return {
            "approved": response["approved"],
            "issues": response.get("issues", [])
        }
```

**Flow:**
```
Message generated (ACT-001 + PARENT-001)
  ↓
GUARD-001 check (temp=0.0)
  ↓
IF approved → Send message
  ↓
IF rejected → Regenerate with feedback
  ↓
Re-check with GUARD-001
  ↓
IF approved → Send regenerated message
  ↓
IF double-reject → BLOCK SEND + alert admin
```

**Test Cases:**
```python
# Should REJECT
test_rejects_deficit_language()  # "Kwame is behind"
test_rejects_jargon()            # "diagnostic assessment"
test_rejects_no_strength()       # Doesn't lead with strength
test_rejects_word_limit()        # 350 words

# Should APPROVE
test_approves_compliant_english()
test_approves_compliant_twi()
test_approves_local_materials()
```

**Completion Criteria:**
- ❌ Service implementation
- ❌ Regeneration loop
- ❌ Admin alerting
- ❌ All test cases pass
- ❌ Integration with activity delivery

---

## FLOW-6: Activity Delivery Pipeline

**Status:** ❌ **0% Implemented** (Priority #6 - PRODUCTION BLOCKER)

**Entry:** Gap profile exists with identified gap
**Exit:** Parent receives personalized, compliant activity

**Why Blocker:** Without this, parents get diagnostic quiz but NO value. Platform is useless.

**Pipeline:**
```
Gap profile trigger (OR daily scheduled send)
  ↓
ACT-001: Generate 3-minute activity
  ├─ Input: gap node, student age, home language, literacy level
  ├─ Output: Activity using bottle caps/stones/sticks/coins/beans ONLY
  └─ Requirements: Parent can facilitate, no teacher expertise
  ↓
PARENT-001: Format message in L1
  ├─ Translate to Twi/Ewe/Ga/Dagbani
  ├─ Adjust for literacy (200-300 words)
  └─ Structure: Strength-first → Activity → Encouragement
  ↓
🚨 GUARD-001: MANDATORY compliance check (temp=0.0)
  ├─ IF approved → Continue
  └─ IF rejected → Regenerate → Re-check → IF double-reject: BLOCK
  ↓
Send via WhatsApp
  ↓
Log to parent_activities table
  ↓
Schedule check-in for 3-5 days later
```

**Implementation:**
```python
class ActivityDeliveryService:
    """Activity generation → formatting → compliance → send."""

    async def send_activity_for_gap(
        self,
        parent_id: UUID,
        student_id: UUID,
        gap_node_id: UUID
    ) -> dict[str, Any]:
        """Generate and send activity for specific gap."""

        # Load context
        parent = await self.db.get(Parent, parent_id)
        student = await self.db.get(Student, student_id)
        gap_node = await self.db.get(CurriculumNode, gap_node_id)

        # Generate activity (ACT-001)
        activity_data = await self.prompt_service.invoke("ACT-001", {
            "child_name": student.first_name,
            "current_grade": student.current_grade,
            "age": student.age,
            "node_code": gap_node.code,
            "node_title": gap_node.title,
            "misconception_description": gap_node.common_misconceptions[0]
                if gap_node.common_misconceptions else ""
        })

        # Format in L1 language (PARENT-001)
        message_text = await self.prompt_service.invoke("PARENT-001", {
            "parent_preferred_name": parent.preferred_name,
            "parent_preferred_language": parent.preferred_language,
            "student_first_name": student.first_name,
            "current_grade": student.current_grade,
            "strength_statement": f"{student.first_name} can count well!",
            "focus_node_code": gap_node.code,
            "activity_from_graph": activity_data["activity_title"]
        })

        # GUARD-001 compliance check with regeneration
        async def regenerate(original, feedback):
            """Regenerate message with feedback."""
            return await self.prompt_service.invoke("PARENT-001", {
                **context,
                "avoid_issues": feedback  # Pass rejection reasons
            })

        guard = ComplianceGuard(self.prompt_service)
        approved, final_message = await guard.validate_with_regeneration(
            message_text=message_text,
            parent_name=parent.preferred_name,
            child_name=student.first_name,
            current_grade=student.current_grade,
            regenerate_callback=regenerate
        )

        if not approved:
            # BLOCKED - manual review required
            return {
                "status": "blocked",
                "message": "GUARD-001 double-rejected",
                "activity_id": None
            }

        # Send via WhatsApp
        whatsapp = WhatsAppClient()
        message_id = await whatsapp.send_text_message(
            to=parent.phone,
            text=final_message
        )

        # Log activity
        activity = ParentActivity(
            parent_id=parent_id,
            student_id=student_id,
            gap_node_id=gap_node_id,
            message_text=final_message,
            message_id=message_id,
            scheduled_for=datetime.now(UTC),
            sent_at=datetime.now(UTC)
        )
        self.db.add(activity)

        # Schedule check-in
        await self._schedule_check_in(activity.id, days=3)

        await self.db.commit()

        return {
            "status": "sent",
            "activity_id": activity.id,
            "message_id": message_id
        }
```

**API Endpoint:**
```python
@router.post("/api/v1/activities/send")
async def send_activity(
    parent_id: UUID,
    student_id: UUID,
    gap_node: str,  # Node code
    db: AsyncSession = Depends(get_db)
):
    service = ActivityDeliveryService(db)
    result = await service.send_activity_for_gap(
        parent_id, student_id, gap_node_id
    )
    return result
```

**Completion Criteria:**
- ❌ ACT-001 integration
- ❌ PARENT-001 integration
- ❌ GUARD-001 integration with regeneration
- ❌ WhatsApp sending
- ❌ Activity logging
- ❌ Check-in scheduling
- ❌ End-to-end test passes

---

## FLOW-7: Check-in Cycle

**Status:** ❌ **0% Implemented** (Priority #7 - ENGAGEMENT LOOP)

**Entry:** 3-5 days after activity sent
**Exit:** Parent response analyzed, next activity adjusted

**Flow:**
```
3-5 days after activity → Scheduled trigger
  ↓
PARENT-002: Generate check-in message
  ├─ Reference specific activity
  ├─ Open-ended question (voice note encouraged)
  └─ Gentle, non-judgmental
  ↓
Send check-in
  "Akwaaba, Ama! 👋
   How did the bottle cap activity go with Kwame?
   Send voice note or text!"
  ↓
Parent responds:
  ├─ "He loved it!" → Continue to next gap
  ├─ "Too hard" → Send easier variation
  ├─ "No time" → Send shorter activity next
  └─ [No response] → Gentle reminder after 2 days, then pause
  ↓
Update parent_activities table
  ├─ Set completed_at
  ├─ Set parent_response
  └─ Set ai_sentiment_analysis
```

**Adaptive Logic:**
```python
class CheckInService:
    async def analyze_response(
        self,
        activity_id: UUID,
        parent_response: str
    ) -> dict[str, Any]:
        """Analyze parent response and determine next step."""

        # Sentiment analysis
        sentiment = await self.prompt_service.invoke("ANALYSIS-002", {
            "transcription_text": parent_response,
            "last_activity_title": activity.title
        })

        # Determine next action
        if sentiment["intent"] == "activity_feedback_positive":
            # Success! Move to next gap
            next_action = "continue_to_next_gap"
            difficulty_adjustment = 0

        elif sentiment["intent"] == "activity_feedback_negative":
            # Struggled - make easier
            next_action = "retry_easier"
            difficulty_adjustment = -1

        elif "no time" in parent_response.lower():
            # Busy parent - send shorter activities
            next_action = "reduce_length"
            difficulty_adjustment = 0

        else:
            # Unclear - send neutral encouragement
            next_action = "encourage_and_retry"
            difficulty_adjustment = 0

        return {
            "sentiment": sentiment,
            "next_action": next_action,
            "difficulty_adjustment": difficulty_adjustment
        }
```

**Completion Criteria:**
- ❌ PARENT-002 integration
- ❌ Sentiment analysis
- ❌ Adaptive difficulty logic
- ❌ Scheduling system
- ❌ No-response handling

---

# LAYER 3: DIAGNOSTIC SOURCES

Multiple pathways to understand student gaps.

---

## FLOW-8: Exercise Book Photo Analysis (v2 PRIMARY)

**Status:** ❌ **0% Implemented** (Priority #8 - v2 CORE)

**Entry:** Teacher uploads exercise book photo
**Exit:** Gap profile updated with photo analysis

**Why v2 Primary:** Uses artifacts that already exist. Teacher takes 30s photo vs 30min test administration.

**Flow:**
```
Teacher uploads photo → S3 storage
  ↓
ANALYSIS-001 prompt: Exercise book analysis
  ├─ Detect computational errors (wrong algorithm)
  ├─ Identify misconceptions (systematic patterns)
  ├─ Distinguish handwriting vs understanding
  └─ Assess incomplete work (engagement vs comprehension)
  ↓
Parse AI response:
  {
    "problems_extracted": [...],
    "suspected_gaps": ["B1.1.2.2", "B2.1.1.1"],
    "confidence": 0.85
  }
  ↓
Update gap profile (FLOW-3: Multi-source)
  source="exercise_book"
  nodes_gap += suspected_gaps
  ↓
Notify teacher with insights
  "Analysis complete for Kwame! 📚
   Detected gap: B1.1.2.2 (subtraction within 100)
   Pattern: Reverses digits in 2-digit problems
   Suggested: Place value review first"
```

**API Endpoint:**
```python
@router.post("/api/v1/exercise-books/upload")
async def upload_exercise_book(
    student_id: UUID,
    image: UploadFile,
    subject: Literal["math", "english"],
    date_of_work: date,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    # Upload to S3
    s3_url = await s3_service.upload_file(
        file=image.file,
        bucket="gapsense-media",
        key=f"exercise-books/{student_id}/{date_of_work}.jpg"
    )

    # Create analysis record
    analysis = ExerciseBookAnalysis(
        student_id=student_id,
        image_url=s3_url,
        subject=subject,
        date_of_work=date_of_work,
        status="pending"
    )
    db.add(analysis)
    await db.commit()

    # Queue background job (returns 202 ACCEPTED)
    background_tasks.add_task(
        analyze_exercise_book,
        analysis_id=analysis.id
    )

    return {
        "analysis_id": analysis.id,
        "status": "pending",
        "message": "Analysis started. Teacher will be notified when complete."
    }
```

**Background Job:**
```python
async def analyze_exercise_book(analysis_id: UUID):
    """Background worker for exercise book analysis."""

    analysis = await db.get(ExerciseBookAnalysis, analysis_id)

    # Download image from S3
    image_data = await s3_service.download_file(analysis.image_url)

    # Call ANALYSIS-001 (with image)
    result = await prompt_service.invoke("ANALYSIS-001", {
        "student_first_name": student.first_name,
        "current_grade": student.current_grade,
        "image_base64": base64.b64encode(image_data).decode()
    })

    # Update gap profile
    if result["confidence"] >= 0.70:  # Accuracy threshold
        await gap_profile_service.update_from_source(
            student_id=analysis.student_id,
            source="exercise_book",
            nodes_tested=result["nodes_tested"],
            nodes_gap=result["suspected_gaps"],
            nodes_mastered=[],
            confidence=result["confidence"]
        )

        # Notify teacher
        await notify_teacher(analysis, result)
    else:
        # Low confidence - flag for manual review
        analysis.status = "requires_review"
        analysis.confidence = result["confidence"]
```

**Accuracy Handling:**
- IF confidence >= 0.80: Auto-update gap profile
- IF 0.70 ≤ confidence < 0.80: Update + flag for teacher review
- IF confidence < 0.70: Don't update, recommend explicit diagnostic

**Completion Criteria:**
- ❌ S3 integration
- ❌ ANALYSIS-001 with vision
- ❌ Confidence threshold logic
- ❌ Gap profile update
- ❌ Teacher notification
- ❌ Background job processing

---

## FLOW-9: Teacher Conversation Interface (v2 PRIMARY TEACHER UX)

**Status:** ❌ **0% Implemented** (Priority #9 - v2 CORE)

**Entry:** Teacher sends message via WhatsApp
**Exit:** AI responds with diagnostic insights + actions

**Conversation Modes:**

### **Mode 1: Lesson Planning**
```
Teacher: "I'm teaching fractions next week"
  ↓
AI (TEACHER-003):
  "Based on your class profiles:
   - 12 students have B2.1.3.1 gap (fraction concept)
   - 4 need place value first (B2.1.1.1)
   - 18 ready for B4 fractions

   Suggested 3-day sequence:
   Day 1: Visual fraction strips (whole class)
   Day 2: Differentiate - Group A (fraction notation), Group B (place value)
   Day 3: Practice + check understanding

   Would you like specific activities for each group?"
```

### **Mode 2: Student Concern**
```
Teacher: "Why does Kwame keep failing subtraction?"
  ↓
AI loads Kwame's:
  ├─ Gap profile (B2.1.1.1 place value gap confirmed)
  ├─ Exercise books (reverses digits pattern)
  └─ Parent engagement (mother completing activities)
  ↓
AI response:
  "Kwame's exercise books show he reverses digits in 2-digit subtraction.
   Root cause: B2.1.1.1 (place value to 100) - he doesn't anchor tens vs ones.

   The subtraction failures are a SYMPTOM, not the problem.

   Try: 1 week bottle cap place value games, then retry subtraction.
   His mother is engaged (4/5 activities complete), so home support is strong.

   I'll track his progress - expect improvement in 10-14 days."
```

### **Mode 3: Progress Check**
```
Teacher: "How's my class doing?"
  ↓
AI aggregates all student profiles:
  ↓
"Your class shows strong place value (85% B1.1.1.1 mastered).
 Class-wide gap: B2.1.2.2 (multiplication) - only 3/25 mastered.

 Priority: Next 2 weeks, focus multiplication concept.
 17 students are ready (prerequisites met).
 8 students need B1.1.2.1 (repeated addition) first.

 Would you like differentiation groups?"
```

**Implementation:**
```python
class TeacherConversationService:
    async def respond_to_teacher(
        self,
        teacher_id: UUID,
        message: str,
        conversation_history: list[dict]
    ) -> dict[str, Any]:
        """TEACHER-003 conversational interface."""

        # Load context
        teacher = await self.db.get(Teacher, teacher_id)
        students = await self.get_teacher_students(teacher_id)
        gap_profiles = await self.get_class_gap_profiles(students)

        # Call TEACHER-003
        response = await self.prompt_service.invoke("TEACHER-003", {
            "teacher_name": teacher.full_name,
            "school_name": teacher.school.name,
            "grade": teacher.class_name,
            "total_students": len(students),
            "students_diagnosed": len(gap_profiles),
            "class_gap_summary_json": json.dumps(
                self._summarize_class_gaps(gap_profiles)
            ),
            "teacher_message": message,
            "conversation_history_json": json.dumps(conversation_history)
        })

        return {
            "response_text": response["response_text"],
            "referenced_students": response["referenced_students"],
            "suggested_actions": response["suggested_actions"],
            "follow_up_questions": response.get("follow_up_questions", [])
        }
```

**API Endpoint:**
```python
@router.post("/api/v1/teacher/chat")
async def teacher_chat(
    teacher_id: UUID,
    message: str,
    conversation_history: list[dict] = [],
    db: AsyncSession = Depends(get_db)
):
    service = TeacherConversationService(db)
    return await service.respond_to_teacher(
        teacher_id, message, conversation_history
    )
```

**Completion Criteria:**
- ❌ TEACHER-003 integration
- ❌ Class context loading
- ❌ All 4 conversation modes work
- ❌ Conversation history tracking
- ❌ WhatsApp integration
- ❌ Teacher finds it useful (user testing)

---

## FLOW-10: Parent Voice Note Analysis

**Status:** ❌ **0% Implemented** (Priority #10)

**Entry:** Parent sends voice note about child's learning
**Exit:** Gap profile updated with home observation

**Flow:**
```
Parent sends voice note → WhatsApp auto-transcribes
  ↓
ANALYSIS-002: Cognitive process extraction
  ├─ How does child explain the problem?
  ├─ What language? (L1 vs English)
  ├─ What errors reveal thinking patterns?
  └─ Conceptual or procedural gap?
  ↓
Update gap profile
  source="parent_observation"
  home_observation metadata
  ↓
Respond with encouragement
```

**Example:**
```
Parent (Twi voice): "Kwame se, 15 ne 8 yɛ 7. Ɔde ne nsateaa na ɔkan."
Translation: "Kwame says 15 take away 8 is 7. He uses his fingers to count."
  ↓
AI analysis:
  - Strategy: Counting-back (procedural)
  - Gap: Not using place value (conceptual)
  - Pattern: Finger dependence
  ↓
Update: B1.1.2.2 gap confirmed
Recommended: Number sense activities
```

**Completion Criteria:**
- ❌ WhatsApp voice transcription
- ❌ ANALYSIS-002 integration
- ❌ Gap profile update
- ❌ Parent response generation

---

## FLOW-11: Explicit Diagnostic Session (v2 SECONDARY)

**Status:** ✅ **85% Implemented** (Priority #11 - OPTIONAL)

**Entry:** Teacher explicitly triggers OR parent consents
**Exit:** DiagnosticSession completed, GapProfile generated

**v2 Note:** This should be ONE of FOUR diagnostic sources, not THE ONLY source.

**Current Implementation:** `src/gapsense/engagement/flow_executor.py:1484-1757`

**State Transitions:**
```
PENDING → IN_PROGRESS → AWAITING_ANSWER → PROCESS_ANSWER
  ↓                ↑_______________|
  ↓
COMPLETE → Generate gap profile (DIAG-003)
```

**What Works:**
- ✅ Adaptive question selection
- ✅ Backward prerequisite tracing
- ✅ 6 priority screening nodes
- ✅ Max 15 questions
- ✅ Gap profile generation

**What's Wrong:**
- ❌ Positioned as PRIMARY (should be optional)
- ❌ Auto-triggers after onboarding (should be teacher-triggered)
- ❌ Gap profile REPLACES (should incrementally merge)

**v2 Fix:**
```python
# Current (WRONG):
async def complete_onboarding(...):
    # Line 494: Auto-create diagnostic
    if parent.diagnostic_consent:
        session = DiagnosticSession(...)  # Auto-trigger

# v2 (CORRECT):
async def complete_onboarding(...):
    # Don't auto-trigger
    # Wait for teacher to explicitly request
    # OR trigger activity delivery immediately
    pass

# Trigger only when teacher asks:
@router.post("/api/v1/diagnostics/trigger")
async def trigger_diagnostic(
    student_id: UUID,
    teacher_id: UUID  # Only teachers can trigger
):
    # Create session
    # Notify parent
    # Begin explicit diagnostic
```

**Completion Criteria:**
- ✅ Core diagnostic engine works
- ❌ Change from auto-trigger to teacher-triggered
- ❌ Integrate with multi-source gap updates

---

# LAYER 4: USER ONBOARDING

Getting users into the system.

---

## FLOW-12: School Registration (Web/API)

**Status:** ✅ **100% Implemented**

**Entry:** Headmaster uses web interface
**Exit:** School registered, invitation code generated

**API:**
```
GET /api/v1/schools/search?q=<name>
  → Search GES schools database

POST /api/v1/schools/register
  → Create school + generate invitation code
```

**File:** `src/gapsense/api/v1/schools.py`

**No changes needed - works correctly.**

---

## FLOW-13: Teacher Onboarding

**Status:** ✅ **90% Implemented**

**Entry:** Teacher sends invitation code OR school name
**Exit:** Teacher linked to school, roster uploaded

**State Transitions:**
```
COLLECT_SCHOOL → VALIDATE_CODE → COLLECT_CLASS → UPLOAD_ROSTER → COMPLETE
```

**File:** `src/gapsense/engagement/teacher_flows.py:141-838`

**What Works:**
- ✅ Invitation code validation
- ✅ CSV roster parsing
- ✅ Student record creation
- ✅ OCR photo parsing

**Minor Fix Needed:**
- ⚠️ Line 813: Onboarding message mentions "parents message START" - this is outdated

**Completion Criteria:**
- ✅ Core flow works
- ❌ Update onboarding message
- ✅ Roster upload works

---

## FLOW-14: Parent Onboarding

**Status:** ✅ **90% Implemented**

**Entry:** Parent sends first message
**Exit:** Parent linked to student, language set

**State Transitions:**
```
AWAITING_OPT_IN → AWAITING_STUDENT_SELECTION → CONFIRM_STUDENT →
AWAITING_DIAGNOSTIC_CONSENT → AWAITING_LANGUAGE → COMPLETE
```

**File:** `src/gapsense/engagement/flow_executor.py:370-1389`

**What Works:**
- ✅ Welcome message with buttons
- ✅ Student selection from roster
- ✅ Consent collection
- ✅ Language preference
- ✅ Student linking

**v2 Fix:**
```python
# Current (line 494): Auto-triggers diagnostic
if parent.diagnostic_consent:
    session = DiagnosticSession(...)

# v2: Trigger activity delivery instead
if parent.diagnostic_consent:
    # Send first activity
    await activity_service.send_activity_for_gap(
        parent_id=parent.id,
        student_id=student.id,
        gap_node_id=most_common_gap  # From class patterns
    )
```

**Completion Criteria:**
- ✅ Core onboarding works
- ❌ Replace diagnostic auto-trigger with activity delivery

---

## FLOW-15: Opt-out Flow

**Status:** ✅ **100% Implemented**

**Entry:** Parent sends opt-out keyword
**Exit:** Parent opted out, all messages stopped

**File:** `src/gapsense/engagement/flow_executor.py:218-272`

**Keywords:** STOP, gyae, tɔtɔ, tsia, nyɛli

**Instant opt-out (Wolf/Aurino dignity principle):**
```
Detect keyword → Immediate opt-out → Confirmation message
```

**No changes needed - works correctly.**

---

# LAYER 5: BACKGROUND PROCESSING

Scalability infrastructure for async work.

---

## FLOW-16: SQS Worker Architecture

**Status:** ❌ **0% Implemented** (Priority #12 - SCALABILITY)

**Why Now:** Exercise book analysis, activity delivery, all need background processing. Must exist before those flows scale.

**Architecture:**
```
┌─────────────┐
│  FastAPI    │  Returns 200 immediately (< 200ms)
│  Webhook    │
└──────┬──────┘
       │
       ↓ Send message to queue
┌─────────────┐
│  SQS FIFO   │  Ordered per parent (message_group_id = phone)
│  Queue      │  Deduplication (message_id)
└──────┬──────┘
       │
       ↓ Worker polls
┌─────────────┐
│  Background │  Separate process/Lambda
│  Worker     │  Process job → Update DB → Send WhatsApp
└─────────────┘
```

**Job Types:**
```python
class JobType(str, Enum):
    INBOUND_WHATSAPP = "inbound_whatsapp"
    EXERCISE_BOOK_ANALYSIS = "exercise_book_analysis"
    SEND_ACTIVITY = "send_activity"
    SEND_CHECK_IN = "send_check_in"
    SCHEDULED_REMINDER = "scheduled_reminder"
    DIAGNOSTIC_COMPLETE = "diagnostic_complete"
```

**Implementation:**
```python
# Web service (FastAPI)
@router.post("/api/v1/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    payload = await request.json()

    # Return 200 IMMEDIATELY
    background_tasks.add_task(
        queue_message,
        job_type=JobType.INBOUND_WHATSAPP,
        payload=payload
    )

    return {"status": "accepted"}

async def queue_message(job_type: JobType, payload: dict):
    """Send to SQS FIFO."""

    sqs = boto3.client("sqs", region_name="af-south-1")

    sqs.send_message(
        QueueUrl=settings.SQS_QUEUE_URL,
        MessageBody=json.dumps({
            "job_type": job_type,
            "payload": payload
        }),
        MessageGroupId=payload.get("phone", "default"),  # FIFO ordering per parent
        MessageDeduplicationId=payload.get("message_id", str(uuid4()))
    )

# Worker (separate process)
async def worker_main():
    """Poll SQS and process jobs."""

    sqs = boto3.client("sqs", region_name="af-south-1")

    while True:
        response = sqs.receive_message(
            QueueUrl=settings.SQS_QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20  # Long polling
        )

        messages = response.get("Messages", [])

        for message in messages:
            job = json.loads(message["Body"])

            # Route to handler
            await handle_job(job)

            # Delete from queue
            sqs.delete_message(
                QueueUrl=settings.SQS_QUEUE_URL,
                ReceiptHandle=message["ReceiptHandle"]
            )

async def handle_job(job: dict):
    """Route job to appropriate handler."""

    job_type = job["job_type"]
    payload = job["payload"]

    handlers = {
        JobType.INBOUND_WHATSAPP: handle_inbound_whatsapp,
        JobType.EXERCISE_BOOK_ANALYSIS: analyze_exercise_book,
        JobType.SEND_ACTIVITY: send_activity_job,
        JobType.SEND_CHECK_IN: send_check_in_job,
    }

    handler = handlers.get(job_type)
    if handler:
        await handler(payload)
    else:
        logger.error(f"Unknown job type: {job_type}")
```

**Completion Criteria:**
- ❌ SQS FIFO queue setup (CloudFormation/Terraform)
- ❌ Web service queuing logic
- ❌ Worker polling logic
- ❌ Job routing
- ❌ Error handling + DLQ
- ❌ Deployment (Docker + ECS OR Lambda)

---

## FLOW-17-21: Background Job Handlers

**Status:** ❌ **0% Implemented**

All background jobs follow same pattern:
```python
async def job_handler(payload: dict):
    """
    1. Load context from DB
    2. Do work (call AI, update DB, send WhatsApp)
    3. Handle errors (retry, DLQ, alert)
    """
    try:
        # Work
        result = await do_work(payload)

        # Log success
        logger.info(f"Job completed: {result}")

    except RetryableError as e:
        # Let SQS retry (message goes back to queue)
        raise

    except FatalError as e:
        # Log and send to DLQ
        logger.error(f"Fatal error: {e}")
        await alert_admin(e)
```

**Jobs:**
- FLOW-17: Inbound WhatsApp routing
- FLOW-18: Exercise book processing
- FLOW-19: Send activity
- FLOW-20: Send check-in
- FLOW-21: Diagnostic complete

All depend on FLOW-16 (SQS infrastructure).

---

# LAYER 6: TEACHER TOOLS

Reports and roster management.

---

## FLOW-22: Teacher Roster Updates

**Status:** ⚠️ **20% Implemented**

**Entry:** Teacher needs to update roster
**Exit:** Changes reflected in database

**Sub-flows:**

### Add Student
```
Teacher: "/add student Kofi Mensah"
  → Create Student record → Link to teacher
```

### Remove Student
```
Teacher: "/remove student Ama"
  → Confirm → Set is_active=False (soft delete)
```

### Re-upload Roster
```
Teacher uploads new photo
  → OCR → Detect changes → Confirm with teacher
```

**Status:** Only initial upload works. Updates not implemented.

---

## FLOW-23: Report Generation (On-Demand)

**Status:** ❌ **0% Implemented**

**Entry:** Teacher requests report
**Exit:** PDF/document generated

**Commands:**
```
/report class → TEACHER-001 (class summary)
/report student Kwame → TEACHER-002 (individual)
```

**TEACHER-001 Output:**
- Class-wide gap distribution
- Student groupings for differentiation
- Recommended interventions
- Progress tracking

**TEACHER-002 Output:**
- Student gap profile
- Prerequisite trace
- Exercise book summary
- Parent engagement status
- Recommended next steps

**v2 Note:** Reports are ON DEMAND, not automatic. TEACHER-003 conversation is primary UX.

---

## FLOW-24: Teacher Dashboard (Web)

**Status:** ❌ **0% Implemented** (Phase 2)

**Entry:** Teacher logs into web UI
**Exit:** Visual class overview

**Features:**
- Gap distribution heatmap (25 students × 27 nodes)
- Class strengths/gaps
- Individual student cards (clickable)
- Export reports (PDF)

**Phase 2 - after MVP proven.**

---

# LAYER 7: ADVANCED FEATURES

Engagement optimization and literacy support.

---

## FLOW-25: Activity Response Conversation

**Status:** ❌ **0% Implemented**

**Entry:** Parent sends immediate response to activity
**Exit:** AI responds with encouragement/adjustment

**Flow:**
```
Parent receives activity → Immediate response
  "Kwame couldn't do this one"
  ↓
AI analyzes → Responds immediately
  "That's okay! Let's try easier version first.
   [Simpler activity] No rush - Kwame will get there!"
```

**Not a check-in (those are scheduled). This is immediate support.**

---

## FLOW-26: Re-engagement After Inactivity

**Status:** ❌ **0% Implemented**

**Entry:** Parent inactive > 2 weeks
**Exit:** Gentle reminder OR parent paused

**Flow:**
```
Detect inactivity → Wait 1 week cooldown
  ↓
Send gentle re-engagement (NOT pushy)
  "Hi Ama! Life gets busy. Kwame's activities are here
   when you're ready. Send 'Hi' to continue or 'STOP' to pause."
  ↓
Parent responds OR stays silent
```

**Key:** Respect parent capacity. Never guilt-trip.

---

## FLOW-27-29: Literacy-Specific Flows

**Status:** ❌ **0% Implemented**

**FLOW-27: Writing Analysis**
- Exercise book composition → ANALYSIS-001 (literacy mode)
- Detect: L1 interference, spelling patterns, sentence structure

**FLOW-28: Comprehension Assessment**
- Reading exercise answers → Distinguish decoding vs comprehension gaps

**FLOW-29: L1 vs English Distinction**
- Determine: Language learning need vs fundamental literacy deficit
- Critical for multilingual Ghana context

**All use ANALYSIS-001 in literacy mode.**

---

# LAYER 8: GOVERNANCE

Risk management and continuous improvement.

---

## FLOW-30: Compliance Audit Trail

**Status:** ❌ **0% Implemented**

**Entry:** Weekly scheduled job
**Exit:** Compliance report

**Flow:**
```
Weekly trigger
  ↓
Query all messages sent
  ↓
Re-run GUARD-001 on batch
  ↓
Detect drift:
  - Rejection rates increasing?
  - Specific issues recurring?
  ↓
Generate report
  "Messages sent: 1,234
   Approval rate: 87%
   Double-rejection: 3%
   Common issues: Deficit language (45)"
  ↓
Alert admin if red flags
```

**Why:** Catch prompt drift, ensure compliance doesn't degrade.

---

## FLOW-31: Prompt Evaluation Pipeline

**Status:** ❌ **0% Implemented**

**Entry:** Weekly scheduled OR before deployment
**Exit:** Prompt performance report

**Flow:**
```
Load test cases from prompt_library.json
  ↓
FOR EACH prompt:
  Call API with test inputs
  Compare to expected outputs
  Validate schema
  ↓
Generate report
  DIAG-001: 92% ✅
  GUARD-001: 95% ✅
  TEACHER-003: 78% ⚠️
  ↓
IF < 85%: Alert admin + block deployment
```

**Critical:** GUARD-001 < 95% = deployment blocker.

---

## FLOW-32: Cross-School Analytics

**Status:** ❌ **0% Implemented** (Phase 2)

**Entry:** Admin dashboard OR scheduled report
**Exit:** System-wide insights

**Aggregations:**
- By region (Greater Accra, Northern, etc.)
- By grade level
- By cascade path
- Gap prevalence patterns

**Feedback to:**
- NaCCA (curriculum policy)
- Teacher training programs
- Content development

**Requires: 1000+ students for statistical significance. Phase 2.**

---

## FLOW-33: Prompt Management

**Status:** ❌ **0% Implemented**

**Entry:** Admin updates prompt
**Exit:** New version deployed

**Flow:**
```
Admin edits prompt_library.json
  ↓
Run FLOW-31 (evaluation)
  ↓
A/B test (optional)
  10% traffic → new version
  Compare metrics
  ↓
IF passes: Deploy
IF fails: Rollback
```

---

## FLOW-34: Parent Web Portal

**Status:** ❌ **0% Implemented** (Phase 2)

**Entry:** Parent clicks link in WhatsApp
**Exit:** Child progress page

**Features:**
- Strength-first summary
- Activity history
- Gap profile (parent-friendly language)
- Encouragement

**Phase 2 - after WhatsApp proven.**

---

# LAYER 9: FUTURE (Phase 2)

On-device capabilities for offline operation.

---

## FLOW-35-37: On-Device Phase 2

**Status:** ❌ **Future**

**FLOW-35: On-Device Exercise Book Analysis**
- Teacher phone (offline) → Gemma 3n SLM
- Local analysis → Sync when online

**FLOW-36: Peer Diagnostic Games**
- On-device SLM facilitates student games
- Extract diagnostic signals from play

**FLOW-37: TTS Voice Coaching**
- Cloud generates script → TTS → Cache audio → Works offline

**Why Phase 2:** Need labeled training data from Phase 1 cloud model first.

---

# API ENDPOINTS

## Implemented ✅

**Health:**
- `GET /` - Health check
- `GET /health` - Detailed status
- `GET /docs` - Swagger UI

**Schools:**
- `GET /api/v1/schools/search?q={query}`
- `POST /api/v1/schools/register`

**Teachers:**
- `POST /api/v1/teachers/`
- `GET /api/v1/teachers/{id}`
- `PUT /api/v1/teachers/{id}`
- `GET /api/v1/teachers/{id}/students`

**Parents:**
- `POST /api/v1/parents/`
- `GET /api/v1/parents/{id}`
- `GET /api/v1/parents/{id}/children`

**Diagnostics:**
- `POST /api/v1/diagnostics/sessions`
- `GET /api/v1/diagnostics/sessions/{id}`
- `GET /api/v1/diagnostics/gap-profiles/{student_id}`

**WhatsApp:**
- `GET /api/v1/webhook/whatsapp` - Verification
- `POST /api/v1/webhook/whatsapp` - Incoming messages

## Missing (v2) ❌

**Exercise Books:**
```
POST /api/v1/exercise-books/upload
GET /api/v1/exercise-books/{analysis_id}
```

**Teacher Chat:**
```
POST /api/v1/teacher/chat
```

**Activities:**
```
POST /api/v1/activities/send
GET /api/v1/activities/{activity_id}
POST /api/v1/activities/{activity_id}/respond
```

**Reports:**
```
POST /api/v1/reports/class/{teacher_id}
POST /api/v1/reports/student/{student_id}
```

**Compliance:**
```
GET /api/v1/compliance/audit?start_date=X&end_date=Y
```

**Prompts:**
```
GET /api/v1/prompts
PUT /api/v1/prompts/{prompt_id}
POST /api/v1/prompts/{prompt_id}/evaluate
```

---

# DECISION TREE

## WhatsApp Message Router

```
Incoming WhatsApp Message
  │
  ├─ Opt-out keyword? → FLOW-15 (Instant opt-out)
  │
  ├─ Command? (/restart, /help, /status) → Handle command
  │
  ├─ Has active conversation_state?
  │   ├─ FLOW-ONBOARD → FLOW-14 (Continue parent onboarding)
  │   ├─ FLOW-DIAGNOSTIC → FLOW-11 (Continue explicit diagnostic)
  │   ├─ FLOW-TEACHER-ONBOARD → FLOW-13 (Continue teacher onboarding)
  │   └─ FLOW-ACTIVITY → FLOW-25 (Activity response)
  │
  ├─ Is teacher?
  │   ├─ Exercise book photo? → FLOW-8 (Exercise book analysis)
  │   ├─ Text question? → FLOW-9 (Teacher conversation)
  │   └─ Command? (/add, /remove, /report) → FLOW-22 or FLOW-23
  │
  ├─ Is parent?
  │   ├─ Not onboarded? → FLOW-14 (Parent onboarding)
  │   ├─ Has pending activity? → FLOW-25 (Activity response)
  │   ├─ Voice note? → FLOW-10 (Voice analysis)
  │   └─ Text? → Context-aware response
  │
  └─ Unknown → Help message
```

---

# COMPREHENSIVE FLOW COVERAGE MATRIX

| # | Flow Name | Priority | Status | Blocking? |
|---|-----------|----------|--------|-----------|
| **LAYER 1: FOUNDATION** | | | | |
| 1 | Async AI Client | #1 | ❌ Missing | 🚨 Foundation |
| 2 | Prompt Library Integration | #2 | ⚠️ 70% | 🚨 Foundation |
| 3 | Multi-Source Gap Updates | #3 | ⚠️ 20% | 🚨 Key Architecture |
| 4 | AI Reasoning Log | #4 | ⚠️ 30% | ⚠️ Compliance |
| **LAYER 2: SAFETY & VALUE** | | | | |
| 5 | GUARD-001 Compliance | #5 | ❌ Missing | 🚨 Blocker |
| 6 | Activity Delivery | #6 | ❌ Missing | 🚨 Blocker |
| 7 | Check-in Cycle | #7 | ❌ Missing | ⚠️ Engagement |
| **LAYER 3: DIAGNOSTICS** | | | | |
| 8 | Exercise Book Analysis | #8 | ❌ Missing | ⚠️ v2 Core |
| 9 | Teacher Conversation | #9 | ❌ Missing | ⚠️ v2 Core |
| 10 | Voice Note Analysis | #10 | ❌ Missing | |
| 11 | Explicit Diagnostic | #11 | ✅ 85% | |
| **LAYER 4: ONBOARDING** | | | | |
| 12 | School Registration | - | ✅ 100% | |
| 13 | Teacher Onboarding | - | ✅ 90% | |
| 14 | Parent Onboarding | - | ✅ 90% | |
| 15 | Opt-out Flow | - | ✅ 100% | |
| **LAYER 5: BACKGROUND** | | | | |
| 16 | SQS Worker Architecture | #12 | ❌ Missing | ⚠️ Scalability |
| 17-21 | Job Handlers (5 types) | - | ❌ Missing | |
| **LAYER 6: TEACHER TOOLS** | | | | |
| 22 | Roster Updates | - | ⚠️ 20% | |
| 23 | Report Generation | - | ❌ Missing | |
| 24 | Teacher Dashboard | Phase 2 | ❌ Future | |
| **LAYER 7: ADVANCED** | | | | |
| 25 | Activity Response | - | ❌ Missing | |
| 26 | Re-engagement | - | ❌ Missing | |
| 27-29 | Literacy Flows (3) | - | ❌ Missing | |
| **LAYER 8: GOVERNANCE** | | | | |
| 30 | Compliance Audit | - | ❌ Missing | |
| 31 | Prompt Evaluation | - | ❌ Missing | |
| 32 | Cross-School Analytics | Phase 2 | ❌ Future | |
| 33 | Prompt Management | - | ❌ Missing | |
| 34 | Parent Web Portal | Phase 2 | ❌ Future | |
| **LAYER 9: FUTURE** | | | | |
| 35-37 | On-Device (3 flows) | Phase 2 | ❌ Future | |

**TOTALS:**
- **Total Flows:** 37
- **Fully Implemented:** 4 (FLOW-11, 12, 13, 14, 15)
- **Partially Implemented:** 5 (FLOW-2, 3, 4, 13, 14, 22)
- **Missing:** 28
- **Overall v2 Completion:** **~15%**

**PRODUCTION BLOCKERS:**
1. 🚨 **FLOW-1:** Async AI Client (foundation)
2. 🚨 **FLOW-3:** Multi-source gap updates (architecture)
3. 🚨 **FLOW-5:** GUARD-001 compliance (ethics)
4. 🚨 **FLOW-6:** Activity delivery (value proposition)

---

# CRITICAL PATH FOR v2 MVP

**Build Order (No Circular Dependencies):**

```
Week 1-2: LAYER 1 (Foundation)
  1. Async AI client
  2. Prompt library integration
  3. Multi-source gap updates
  4. AI reasoning log

Week 3-4: LAYER 2 (Safety & Value)
  5. GUARD-001 compliance gate
  6. Activity delivery pipeline
  7. Check-in cycle

Week 5-6: LAYER 3 (Diagnostics)
  8. Exercise book analysis
  9. Teacher conversation interface

Week 7: LAYER 4 (Onboarding fixes)
  10. Update parent onboarding (remove auto-diagnostic)
  11. Update teacher onboarding message

Week 8: LAYER 5 (Scalability)
  12. SQS worker architecture
  13. Migrate flows to background jobs

Week 9-10: Testing & Polish
  14. Integration tests
  15. User acceptance testing
  16. Bug fixes
```

**Total: 10 weeks to v2 MVP**

---

# BUILD PRINCIPLES

## 1. Dependency-First
Never build a flow that depends on a flow that doesn't exist yet.

## 2. Foundation Before Features
Infrastructure (AI client, SQS, compliance) before user-facing features.

## 3. Safety Before Scale
GUARD-001 must exist before any parent messages at scale.

## 4. Value Before Optimization
Activity delivery before analytics dashboards.

## 5. Test Before Ship
Every layer has integration tests before moving to next layer.

---

**Last Updated:** 2026-02-17
**Build Status:** Foundation complete, ready for LAYER 1 implementation
**Document Status:** Ordered by dependencies, ready to build

---

**🎯 Key Takeaway:** All 37 flows kept. Document reorganized in dependency order. Build Layer 1 → Layer 2 → Layer 3 → etc. No circular dependencies. Clear critical path.
