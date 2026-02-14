# GapSense Implementation Plan
## What We're Building (7-Day Sprint to UNICEF Demo)

---

## What GapSense Actually Is

**An AI-powered diagnostic reasoning engine** that makes invisible learning gaps visible by:
1. Analyzing existing artifacts (exercise books, not new tests)
2. Tracing backward through a prerequisite graph to find root causes
3. Engaging parents via WhatsApp with dignity-preserving, evidence-based activities
4. Giving teachers a conversational diagnostic partner

---

## The Core Technical Challenge

**Can AI reason about learning gaps the way an expert teacher would?**

Not "can AI grade answers" (trivial). Can it:
- See a student write "347 = 3 + 4 + 7" and recognize **unitary place value thinking** (MC-B2.1.1.1-01)
- Trace that error backward: B4 failure → test B2 → find B2.1.1.1 gap → identify "Place Value Collapse" cascade (CP-001)
- Know this affects ~55% of Ghanaian students (evidence: Abugri & Mereku 2024)
- Generate a parent activity using bottle caps (not "place value blocks") in 3 minutes (Wolf/Aurino)
- Validate that message NEVER says "behind" or "struggling" (GUARD-001 at temp=0.0)
- Deliver in Twi if parent's L1 is Twi

**This is the entire system.**

---

## The Architecture We're Building

```
INBOUND (Parent sends WhatsApp message)
  ↓
WhatsApp Cloud API webhook → FastAPI /webhooks/whatsapp
  ↓ (validate, enqueue to SQS, return 200 in <3s)
SQS FIFO Queue
  ↓ (worker polls)
Worker Service
  ↓ (route by message type)

If PHOTO → ANALYSIS-001 (exercise book analyzer)
  ↓ Claude Sonnet analyzes handwriting, error patterns
  ↓ Updates gap_profile in DB
  ↓ Triggers parent report generation

If TEXT → Conversation router
  ↓ Load parent state (onboarding? activity_cycle? dormant?)
  ↓ Generate response (PARENT-002/003)
  ↓ Run GUARD-001 compliance check
  ↓ If rejected → regenerate with feedback
  ↓ If approved → send via WhatsApp

DIAGNOSTIC SESSION (teacher-initiated)
  ↓
POST /diagnostics/sessions {student_id, entry_grade}
  ↓ Load prerequisite graph
  ↓ Call DIAG-001 (generate first question from priority screening nodes)
  ↓ Return question to teacher

Teacher submits answer → POST /diagnostics/sessions/{id}/respond
  ↓ Call DIAG-002 (analyze response, detect error pattern)
  ↓ If gap detected → backward trace through graph
  ↓ If mastered → continue forward
  ↓ Call DIAG-001 again (adaptive next question)
  ↓ Repeat until root gap found with confidence >= 0.80
  ↓ Call DIAG-003 (generate final gap profile)
  ↓ Store in gap_profiles table
  ↓ Trigger PARENT-001 (diagnostic report message)
  ↓ Run GUARD-001
  ↓ Send to parent via WhatsApp
```

---

## The Proprietary IP We're Implementing

### 1. Prerequisite Graph (gapsense_prerequisite_graph_v1.2.json)
**35 nodes, 6 cascade paths**

Loaded into PostgreSQL at startup:
- `curriculum_nodes` table (B1.1.1.1 through B9.x.x.x)
- `curriculum_prerequisites` table (directed edges)
- `curriculum_misconceptions` table (error patterns per node)
- `cascade_paths` table (critical failure sequences)

**Graph traversal algorithms** (src/curriculum/service.py):
```python
def backward_trace(node_code: str, max_depth: int = 4) -> list[str]:
    """Trace backward to find prerequisite nodes"""
    # B4.1.3.1 → B3.1.3.1 → B2.1.3.1 → B1.1.3.1

def find_cascade_path(gap_nodes: list[str]) -> str | None:
    """Match detected gaps to known cascades"""
    # [B2.1.1.1, B4.1.1.1] → "Place Value Collapse" (CP-001)

def priority_screening_order(grade: str) -> list[str]:
    """Get priority nodes for initial assessment"""
    # B5 student → test [B2.1.1.1, B1.1.2.2, B2.1.2.2, B2.1.3.1, ...]
```

### 2. Prompt Library (gapsense_prompt_library_v1.1.json)
**13 prompts with system prompts, templates, output schemas**

Loaded by AI service:
```python
class AIService:
    def __init__(self):
        self.prompts = json.load(open('data/prompts/prompt_library.json'))

    async def invoke_prompt(self, prompt_id: str, variables: dict) -> dict:
        prompt = self.prompts['prompts'][prompt_id]

        # Render template
        system_prompt = prompt['system_prompt']  # Static, cacheable
        user_prompt = prompt['user_template'].format(**variables)

        # Call Anthropic with caching
        response = await self.anthropic.messages.create(
            model=prompt['model'],
            temperature=prompt['temperature'],
            system=[
                {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": json.dumps(prerequisite_graph), "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": user_prompt}]
        )

        # Validate against output_schema
        result = json.loads(response.content[0].text)
        validate(result, prompt['output_schema'])
        return result
```

### 3. Wolf/Aurino Compliance Engine (GUARD-001)
**Runs at temperature 0.0 on EVERY parent message**

```python
async def send_to_parent(parent: Parent, message: str) -> None:
    # GUARD-001 validation
    guard_result = await ai_service.invoke_prompt('GUARD-001', {
        'message_text': message,
        'parent_name': parent.preferred_name,
        'literacy_level': parent.literacy_level,
        'preferred_language': parent.preferred_language
    })

    if not guard_result['approved']:
        # Regenerate with feedback
        logger.warning("guard_rejection", issues=guard_result['issues'])
        message = await regenerate_with_feedback(message, guard_result['issues'])

        # Re-check
        guard_result = await ai_service.invoke_prompt('GUARD-001', {...})

        if not guard_result['approved']:
            # BLOCK SEND - flag for human review
            logger.error("guard_double_rejection")
            raise ComplianceError("Message failed compliance check twice")

    # Send via WhatsApp
    await whatsapp_service.send_text(parent.phone, message)
```

---

## The Database Schema We're Implementing

**From gapsense_data_model.sql (742 lines)**

Key tables:
- `curriculum_nodes` - The 35-node graph
- `curriculum_prerequisites` - Directed edges
- `curriculum_misconceptions` - Error patterns
- `cascade_paths` - Critical failure sequences
- `students` - Student records (minimal data)
- `gap_profiles` - Current diagnostic state per student
- `diagnostic_sessions` - Question/response history
- `parents` - Parent records with language preferences
- `parent_interactions` - All WhatsApp messages sent/received
- `parent_activities` - Activity delivery tracking
- `teachers` - Teacher records
- `schools` - School records
- `ai_reasoning_log` - Audit trail of all AI decisions

**All use UUID primary keys, TIMESTAMPTZ, JSONB for flexible data**

---

## The WhatsApp Integration We're Building

**From gapsense_whatsapp_flows.json**

### Webhook Handler
```python
@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    payload = await request.json()

    # ALWAYS return 200 within 3 seconds (Meta requirement)
    await sqs_service.send_message(
        queue_url=settings.SQS_QUEUE_URL,
        message_body=json.dumps({
            "type": "inbound_whatsapp",
            "payload": payload
        }),
        message_group_id=extract_phone(payload)  # FIFO ordering per parent
    )

    return Response(status_code=200)
```

### Message Sender
```python
class WhatsAppService:
    async def send_text(self, phone: str, text: str) -> str:
        """Send text message"""
        response = await self.http_client.post(
            f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages",
            headers={"Authorization": f"Bearer {self.api_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": text}
            }
        )
        return response.json()['messages'][0]['id']

    async def send_template(self, phone: str, template_name: str, params: list) -> str:
        """Send pre-approved template (for conversation initiation)"""
        # Used for TMPL-ONBOARD-001, TMPL-ACTIVITY-001, etc.
```

---

## What We're Proving in 7 Days

**To UNICEF:** This isn't vaporware. We have:
1. Working diagnostic engine (upload exercise book photo → gap identified)
2. Working parent message generation (strength-first, Twi/Ewe/Ga, 3-minute activities)
3. Working compliance validation (GUARD-001 blocks deficit language)
4. Deployed to AWS (not localhost demo)
5. Real WhatsApp integration (not simulated)

**Technical demo flow:**
1. Teacher uploads exercise book photo via API
2. ANALYSIS-001 analyzes → identifies B2.1.1.1 place value gap
3. System generates parent report (PARENT-001) in Twi
4. GUARD-001 validates (no "behind", "struggling" detected)
5. Message sent to parent's WhatsApp
6. Parent receives: "Kwame ankasa nim sɛ..." (strength-first framing)

This proves the entire value chain works.

---

## What Success Looks Like

**By Feb 20:**
- ✅ System running on AWS (Fargate + RDS + SQS)
- ✅ Prerequisite graph loaded (35 nodes)
- ✅ Can analyze 1 exercise book photo
- ✅ Can send 1 WhatsApp message that passes GUARD-001
- ✅ Can run 1 diagnostic session (6-12 questions)
- ✅ Teacher can see gap profile output
- ✅ Video demo for UNICEF showing real WhatsApp delivery

This is buildable in 7 days because:
- Every component is specified
- No design decisions needed
- Straight implementation from specs
- Claude Code system prompt synthesizes everything

---

## Implementation Priority Order

### Day 1-2: Foundation
1. Project structure setup
2. SQLAlchemy models from data_model.sql
3. Database migrations (Alembic)
4. Load prerequisite graph into DB
5. Basic FastAPI app with health endpoints

### Day 3-4: Core Services
1. Graph traversal service (backward_trace, find_cascade_path)
2. AI service (Anthropic integration, prompt loading)
3. Diagnostic engine (DIAG-001/002/003 orchestration)
4. Exercise book analysis (ANALYSIS-001)

### Day 5-6: WhatsApp Integration
1. WhatsApp webhook handler
2. SQS integration
3. Worker service
4. Parent message generation (PARENT-001/002/003)
5. Compliance validation (GUARD-001)

### Day 7: Deployment & Testing
1. AWS CDK deployment
2. End-to-end testing with real exercise book photo
3. WhatsApp delivery verification
4. Video demo recording

---

## Technical Specifications We're Following

**All implementation must match:**
- `gapsense_data_model.sql` (742 lines) - Database schema
- `gapsense_api_spec.json` (200+ lines) - API contracts
- `gapsense_prompt_library_v1.1.json` (54KB) - AI prompts
- `gapsense_prerequisite_graph_v1.2.json` (71KB) - Curriculum graph
- `gapsense_whatsapp_flows.json` (17KB) - Conversation flows
- `gapsense_project_structure.md` - Module organization
- `gapsense_adr.md` - Architecture decisions

**No improvisation. Pure implementation.**
