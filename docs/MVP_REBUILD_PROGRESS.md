# MVP Rebuild Progress
**Branch:** `feature/mvp-teacher-initiated`
**Date:** February 16, 2026
**Status:** Phase 1 Foundation - 60% Complete

---

## 🎯 Objective

Rebuild GapSense MVP to match the **actual specification** from MVP Blueprint:
- Teacher-initiated platform (not parent-initiated)
- Exercise book scanner with multimodal AI
- Twi voice notes for parents
- Teacher conversation partner

---

## ✅ Phase 1: Foundation (COMPLETED)

### 1. Database Schema Updates
- [x] **Teacher Model**: Added `conversation_state`, `conversation_history`, `class_name`
- [x] **Student Model**: Made `primary_parent_id` nullable (teachers create students before parents link)
- [x] **School Model**: Already existed, no changes needed
- [x] **Migrations**: 2 new migrations created and run
  - `eb4eab32e503`: Add teacher conversation state
  - `9308455ddbbd`: Make primary_parent_id nullable

### 2. Teacher Onboarding Flow
- [x] **Created**: `src/gapsense/engagement/teacher_flows.py`
- [x] **Implemented**: Complete FLOW-TEACHER-ONBOARD
  - Teacher sends "START"
  - System collects: school name, class name, student count
  - Teacher uploads student list (text format)
  - System creates all student profiles
  - Teacher marked as onboarded

### 3. Student Name Parsing
- [x] Handles numbered lists: "1. Name\n2. Name"
- [x] Handles plain lists: "Name\nName\nName"
- [x] Handles comma-separated: "Name, Name, Name"
- [x] Removes numbering automatically

---

## 🚧 Phase 2: Webhook Integration (IN PROGRESS)

### Current Task: Route Teacher vs Parent Messages

**Challenge:** Need to distinguish teacher from parent when message arrives.

**Solution Options:**
1. **Phone Number Lookup**: Check if phone exists in `teachers` or `parents` table
2. **Conversation Context**: Track user type in first interaction
3. **Role Selection**: Ask "Are you a teacher or parent?" on first contact

**Recommended:** Option 1 (phone lookup) + Option 3 (fallback)

**Files to Modify:**
- `src/gapsense/webhooks/whatsapp.py` - Main webhook handler
- `src/gapsense/api/v1/webhooks.py` - API endpoint

**Next Steps:**
1. Add user type detection in webhook
2. Route to `TeacherFlowExecutor` or `FlowExecutor` based on user type
3. Handle unknown users (ask role)

---

## 📋 Phase 3: Parent Linking (PENDING)

### Current Problem: Parent Creates Student
```python
# WRONG (current):
Parent sends "Hi"
→ System asks for child name, age, grade
→ Creates NEW student
→ No link to teacher/school

# CORRECT (spec):
Parent sends "START"
→ System asks: "Which child is yours?"
→ Shows list of students from teacher's class (no parent linked yet)
→ Parent selects from list
→ Links to existing student
```

### Implementation Required:
1. Rewrite `_start_onboarding()` in `flow_executor.py`
2. Query students where `primary_parent_id IS NULL`
3. Generate student selection list (numbered buttons or text)
4. On selection, link parent to student:
   ```python
   student.primary_parent_id = parent.id
   parent.onboarded_at = datetime.now(UTC)
   ```

**Files to Modify:**
- `src/gapsense/engagement/flow_executor.py`

---

## 🗑️ Phase 4: Dead Code Removal (PENDING)

### Code to Remove (No Longer Needed):

1. **Diagnostic Questionnaire Flow**
   - MVP uses exercise book scanning, not questionnaires
   - Can keep API endpoints for future, but remove WhatsApp flow

2. **Student Creation in Parent Onboarding**
   - Parents should only LINK to existing students
   - Remove student creation logic from `flow_executor.py`

3. **Activity Delivery Flow (OLD)**
   - Will be replaced by voice note delivery
   - Keep activity generation prompts, remove text-based delivery

**Files to Clean:**
- `src/gapsense/engagement/flow_executor.py` - Remove student creation
- `src/gapsense/api/v1/diagnostics.py` - Keep but document as "API only"

---

## 📊 Phase 5: Testing (PENDING)

### Tests to Update:
1. **Teacher Onboarding Tests**
   - Test FLOW-TEACHER-ONBOARD
   - Test student list parsing
   - Test school creation

2. **Parent Linking Tests**
   - Test parent selects student from list
   - Test linking updates `primary_parent_id`
   - Test multiple parents can't link to same student

3. **Integration Tests**
   - Test full flow: Teacher onboards → Parent links → Student has both

### Tests to Remove/Update:
- Remove tests that create students during parent onboarding
- Update tests for nullable `primary_parent_id`

**Files to Modify:**
- `tests/unit/test_flow_executor.py`
- `tests/unit/test_onboard_spec_compliant.py`
- `tests/integration/test_whatsapp_flow_integration.py`

---

## 🔮 Future Phases (NOT IN SCOPE YET)

### Phase 6: Exercise Book Scanner (Week 3-4)
- Multimodal AI integration (Claude Sonnet 4.5 with vision)
- Image message handling in WhatsApp
- NaCCA prerequisite knowledge base
- Gap profile creation from scans

### Phase 7: Parent Voice Notes (Week 5-6)
- TTS integration (Google Cloud TTS or ElevenLabs)
- STT integration (Whisper API)
- Twi language support
- Daily 6:30 PM scheduled delivery (Celery + Redis)

### Phase 8: Teacher Conversation Partner (Week 7-8)
- Integrate TEACHER-003 prompt
- Context loading (all diagnosed students)
- Conversation history persistence
- Weekly Gap Map generation

---

## 📈 Overall Progress

```
MVP Rebuild Status:

Phase 1: Foundation           ████████████████████ 100%
Phase 2: Webhook Routing      ██████░░░░░░░░░░░░░░  30%
Phase 3: Parent Linking       ░░░░░░░░░░░░░░░░░░░░   0%
Phase 4: Dead Code Removal    ░░░░░░░░░░░░░░░░░░░░   0%
Phase 5: Testing              ░░░░░░░░░░░░░░░░░░░░   0%

OVERALL: ████████░░░░░░░░░░░░ 40%
```

**Estimated Time to MVP (Phases 1-5):** 3-5 days
**Estimated Time to Full MVP (Phases 1-8):** 8-10 weeks

---

## 🚀 How to Continue

### Immediate Next Steps:
1. **Complete Phase 2**: Update webhook to route teacher vs parent messages
   - Modify `src/gapsense/webhooks/whatsapp.py`
   - Add phone lookup logic
   - Route to appropriate flow executor

2. **Start Phase 3**: Rewrite parent onboarding
   - Modify `src/gapsense/engagement/flow_executor.py`
   - Replace student creation with student selection
   - Test with real parent flow

3. **Run Tests**: Ensure existing tests still pass
   - Fix broken tests due to nullable `primary_parent_id`
   - Add new tests for teacher flows

### Commands to Run:
```bash
# Run tests
poetry run pytest tests/ -v

# Check for issues
poetry run ruff check src/
poetry run mypy src/

# Run database migrations (already done)
poetry run alembic upgrade head
```

---

## 📝 Key Files Modified

### New Files:
- `src/gapsense/engagement/teacher_flows.py` (502 lines)
- `alembic/versions/20260216_1204_eb4eab32e503_*.py`
- `alembic/versions/20260216_1214_9308455ddbbd_*.py`
- `docs/mvp_specification_audit_CRITICAL.md`
- `docs/mvp_user_flows_realistic_status.md`

### Modified Files:
- `src/gapsense/core/models/users.py` (Teacher model)
- `src/gapsense/core/models/students.py` (Student model)

### Files to Modify Next:
- `src/gapsense/webhooks/whatsapp.py`
- `src/gapsense/engagement/flow_executor.py`
- `tests/unit/test_flow_executor.py`

---

## 🎓 What We Learned

### Critical Insights:
1. **MVP Blueprint is THE specification** - Not our assumptions
2. **Teacher-initiated platform** - Teachers create students first, parents link later
3. **Exercise book scanning is core** - Not questionnaires
4. **Voice notes in Twi are essential** - Not text messages
5. **Real-world deployment** - School → Teacher → Students → Parents

### Architectural Changes:
- `primary_parent_id` must be nullable (teachers create students)
- Teachers need `conversation_state` (multi-step onboarding)
- Need to distinguish teacher vs parent messages in webhook
- Parent onboarding = linking, not creating

---

**Last Updated:** February 16, 2026
**Next Update:** After Phase 2 complete
