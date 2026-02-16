# TDD Implementation Plan: Real-World Gap Fixes
**Date:** February 16, 2026
**Approach:** Test-Driven Development (Red → Green → Refactor)
**Source:** REAL_WORLD_GAP_ANALYSIS.md (627 lines, 47-point checklist)

---

## 🎯 Scope & Prioritization

### **What We Can TDD (Phases A-F):**
✅ Input validation
✅ Error recovery commands
✅ Confirmation steps
✅ Edge case handling
✅ School deduplication
✅ Session timeout

**Estimated Time:** 5-7 days (with tests)

### **What We Cannot TDD (Requires Infrastructure):**
❌ WhatsApp Business API setup
❌ Production hosting
❌ Monitoring/alerting
❌ CI/CD pipeline
❌ L1 translations (need actual translations, not code)

**Requires:** Separate infrastructure work (2-3 weeks)

---

## 📋 PHASE A: Input Validation (TDD)
**Priority:** 🔴 CRITICAL
**Time:** 1 day
**Test File:** `tests/unit/test_input_validation.py` (NEW)

### A1. Phone Number Validation

**Failing Tests to Write:**
```python
class TestPhoneValidation:
    def test_valid_ghana_phone_number(self):
        # +233501234567 → valid
        assert validate_phone_number("+233501234567") == "+233501234567"

    def test_reject_invalid_format(self):
        # "abc123" → ValidationError
        with pytest.raises(ValidationError):
            validate_phone_number("abc123")

    def test_normalize_ghana_phone(self):
        # "0501234567" → "+233501234567"
        assert validate_phone_number("0501234567") == "+233501234567"

    def test_reject_non_ghana_phone(self):
        # "+1234567890" → ValidationError (only Ghana for MVP)
        with pytest.raises(ValidationError):
            validate_phone_number("+1234567890")
```

**Implementation:**
- Create `src/gapsense/core/validation.py`
- Add `validate_phone_number()` function
- Support formats: +233XXXXXXXXX, 0XXXXXXXXX
- Raise `ValidationError` for invalid

### A2. School Name Validation

**Failing Tests:**
```python
class TestSchoolNameValidation:
    def test_valid_school_name(self):
        assert validate_school_name("St. Mary's JHS, Accra") is not None

    def test_reject_empty_school_name(self):
        with pytest.raises(ValidationError):
            validate_school_name("")

    def test_reject_too_short(self):
        with pytest.raises(ValidationError):
            validate_school_name("A")  # Must be at least 3 chars

    def test_reject_too_long(self):
        with pytest.raises(ValidationError):
            validate_school_name("A" * 201)  # Max 200 chars

    def test_strip_emoji(self):
        result = validate_school_name("St. Mary's 🏫")
        assert "🏫" not in result
        assert result == "St. Mary's"

    def test_normalize_whitespace(self):
        result = validate_school_name("St.  Mary's   JHS")
        assert result == "St. Mary's JHS"  # Single spaces
```

**Implementation:**
- Add `validate_school_name()` to validation.py
- Length: 3-200 characters
- Strip emoji, normalize whitespace
- Preserve apostrophes, hyphens, commas

### A3. Class Name Validation

**Failing Tests:**
```python
class TestClassNameValidation:
    def test_valid_class_names(self):
        assert validate_class_name("JHS 1A") is not None
        assert validate_class_name("B4") is not None
        assert validate_class_name("Primary 6") is not None

    def test_reject_empty(self):
        with pytest.raises(ValidationError):
            validate_class_name("")

    def test_reject_too_long(self):
        with pytest.raises(ValidationError):
            validate_class_name("A" * 51)  # Max 50 chars
```

### A4. Student Count Validation

**Failing Tests:**
```python
class TestStudentCountValidation:
    def test_valid_student_count(self):
        assert validate_student_count("42") == 42

    def test_reject_negative(self):
        with pytest.raises(ValidationError):
            validate_student_count("-5")

    def test_reject_zero(self):
        with pytest.raises(ValidationError):
            validate_student_count("0")

    def test_reject_too_large(self):
        with pytest.raises(ValidationError):
            validate_student_count("999")  # Max 100 for MVP

    def test_reject_non_numeric(self):
        with pytest.raises(ValidationError):
            validate_student_count("forty-two")
```

**Implementation:**
- Add `validate_student_count()` to validation.py
- Range: 1-100 (MVP limit)
- Convert string to int
- Raise ValidationError for invalid

### A5. Student Name Validation

**Failing Tests:**
```python
class TestStudentNameValidation:
    def test_valid_student_names(self):
        assert validate_student_name("Kwame") is not None
        assert validate_student_name("Akosua Addae-Mensah") is not None
        assert validate_student_name("O'Brien") is not None

    def test_reject_empty(self):
        with pytest.raises(ValidationError):
            validate_student_name("")

    def test_reject_too_short(self):
        with pytest.raises(ValidationError):
            validate_student_name("A")  # Min 2 chars

    def test_reject_numbers(self):
        with pytest.raises(ValidationError):
            validate_student_name("Kwame123")

    def test_strip_leading_numbers(self):
        # "1. Kwame" → "Kwame"
        result = validate_student_name("1. Kwame")
        assert result == "Kwame"

    def test_preserve_hyphens_apostrophes(self):
        result = validate_student_name("Addae-Mensah")
        assert result == "Addae-Mensah"
```

### A6. Integration with Flows

**Failing Tests:**
```python
# In existing test files
class TestTeacherFlowWithValidation:
    async def test_invalid_school_name_rejected(self, db_session):
        """Teacher sends empty school name → error message"""
        teacher = Teacher(...)
        executor = TeacherFlowExecutor(db=db_session)

        result = await executor._collect_school_name(teacher, "")

        assert result.error is not None
        assert "school name" in result.error.lower()

    async def test_invalid_student_count_rejected(self, db_session):
        """Teacher sends '-5' as count → error message"""
        # ...
```

**Implementation:**
- Integrate validation into teacher_flows.py
- Integrate validation into flow_executor.py
- Return friendly error messages
- Ask user to try again

---

## 📋 PHASE B: Error Recovery Commands (TDD)
**Priority:** 🔴 CRITICAL
**Time:** 1 day
**Test Files:**
- `tests/unit/test_error_recovery.py` (NEW)
- Update existing flow tests

### B1. RESTART Command

**Failing Tests:**
```python
class TestRestartCommand:
    @pytest.mark.asyncio
    async def test_parent_restart_during_onboarding(self, db_session):
        """Parent types RESTART mid-flow → returns to start"""
        parent = Parent(
            phone="+233501234567",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_STUDENT_SELECTION",
                "data": {"some": "data"}
            }
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)
        result = await executor.process_message(
            parent=parent,
            message_type="text",
            message_content="RESTART",
            message_id="wamid.restart1"
        )

        await db_session.refresh(parent)

        # Should reset conversation state
        assert parent.conversation_state is None
        # Should send welcome message
        assert result.message_sent is True
        assert "welcome" in result.message_id.lower()

    @pytest.mark.asyncio
    async def test_teacher_restart_during_onboarding(self, db_session):
        """Teacher types RESTART → clears state, restarts"""
        # ...

    @pytest.mark.asyncio
    async def test_restart_aliases(self, db_session):
        """'restart', 'RESTART', 'Restart', 'start over' all work"""
        # Test case-insensitive, alternative phrases
```

**Implementation:**
- Detect RESTART command in both executors
- Clear conversation_state
- Send welcome message
- Support aliases: "restart", "start over", "begin again"

### B2. CANCEL Command

**Failing Tests:**
```python
class TestCancelCommand:
    @pytest.mark.asyncio
    async def test_parent_cancel_onboarding(self, db_session):
        """Parent types CANCEL → stops flow, friendly message"""
        parent = Parent(conversation_state={...})

        result = await executor.process_message(..., "CANCEL", ...)

        await db_session.refresh(parent)
        assert parent.conversation_state is None
        assert "cancelled" in result.message_content.lower()

    @pytest.mark.asyncio
    async def test_cancel_aliases(self, db_session):
        """'cancel', 'stop', 'quit', 'exit' all work"""
```

**Implementation:**
- Detect CANCEL/STOP/QUIT/EXIT commands
- Clear conversation_state
- Send confirmation message
- Do not re-trigger onboarding

### B3. HELP Command

**Failing Tests:**
```python
class TestHelpCommand:
    @pytest.mark.asyncio
    async def test_help_during_onboarding(self, db_session):
        """Parent types HELP → explains current step"""
        parent = Parent(
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_STUDENT_SELECTION"
            }
        )

        result = await executor.process_message(..., "HELP", ...)

        # Should explain what to do
        assert "select" in result.message_content.lower()
        assert "number" in result.message_content.lower()
        # Should NOT clear conversation state
        await db_session.refresh(parent)
        assert parent.conversation_state is not None

    @pytest.mark.asyncio
    async def test_help_no_active_flow(self, db_session):
        """Parent types HELP with no active flow → general help"""
        # ...
```

**Implementation:**
- Add context-aware help
- Explain current step
- List available commands
- Do not disrupt flow

### B4. STATUS Command

**Failing Tests:**
```python
class TestStatusCommand:
    @pytest.mark.asyncio
    async def test_parent_check_status(self, db_session):
        """Parent types STATUS → shows current info"""
        parent = Parent(
            phone="+233501234567",
            opted_in=True,
            onboarded_at=datetime.now(UTC),
            preferred_language="en"
        )
        # Link to student
        student = Student(
            first_name="Kwame",
            current_grade="JHS1",
            primary_parent_id=parent.id
        )
        db_session.add_all([parent, student])
        await db_session.commit()

        result = await executor.process_message(..., "STATUS", ...)

        # Should show linked child
        assert "Kwame" in result.message_content
        assert "JHS1" in result.message_content

    @pytest.mark.asyncio
    async def test_teacher_check_status(self, db_session):
        """Teacher types STATUS → shows class info"""
        # Should show: school, class, student count
```

---

## 📋 PHASE C: Confirmation Steps (TDD)
**Priority:** 🔴 CRITICAL
**Time:** 1 day
**Test Files:** Update existing tests

### C1. Confirm Student Selection

**Failing Tests:**
```python
class TestStudentSelectionConfirmation:
    @pytest.mark.asyncio
    async def test_parent_must_confirm_student(self, db_session):
        """Parent selects student → asked to confirm before linking"""
        parent = Parent(conversation_state={
            "flow": "FLOW-ONBOARD",
            "step": "AWAITING_STUDENT_SELECTION",
            "data": {"student_ids_map": {"1": str(student_id)}}
        })

        # Parent selects "1"
        result = await executor.process_message(..., "1", ...)

        # Should ask for confirmation (NOT link yet)
        await db_session.refresh(parent)
        assert parent.conversation_state["step"] == "CONFIRM_STUDENT_SELECTION"
        assert "confirm" in result.message_content.lower()
        assert student.primary_parent_id is None  # Not linked yet

    @pytest.mark.asyncio
    async def test_parent_confirms_yes(self, db_session):
        """Parent confirms → link created"""
        parent = Parent(conversation_state={
            "step": "CONFIRM_STUDENT_SELECTION",
            "data": {"selected_student_id": str(student_id)}
        })

        # Parent confirms
        result = await executor.process_message(..., {"id": "confirm_yes"}, ...)

        # NOW should link
        await db_session.refresh(student)
        assert student.primary_parent_id == parent.id

    @pytest.mark.asyncio
    async def test_parent_declines_confirmation(self, db_session):
        """Parent says 'No' → back to selection"""
        # Should return to AWAITING_STUDENT_SELECTION
```

**Implementation:**
- Add CONFIRM_STUDENT_SELECTION step
- Send confirmation buttons
- On "Yes" → link student
- On "No" → return to selection

### C2. Confirm Teacher Onboarding Completion

**Failing Tests:**
```python
class TestTeacherOnboardingConfirmation:
    @pytest.mark.asyncio
    async def test_teacher_previews_before_creation(self, db_session):
        """Teacher completes roster → sees preview before creating students"""
        teacher = Teacher(conversation_state={
            "step": "AWAITING_STUDENT_LIST",
            "data": {
                "school_name": "St. Mary's",
                "class_name": "JHS 1A",
                "student_count": 3
            }
        })

        # Teacher sends student names
        result = await executor._collect_student_list(
            teacher,
            "1. Kwame\n2. Ama\n3. Kofi"
        )

        # Should show preview (NOT create yet)
        assert result.next_step == "CONFIRM_STUDENT_CREATION"
        assert "3 students" in result.message_content
        assert "confirm" in result.message_content.lower()

    @pytest.mark.asyncio
    async def test_teacher_confirms_creation(self, db_session):
        """Teacher confirms → students created"""
        # ...

    @pytest.mark.asyncio
    async def test_teacher_declines_asks_to_edit(self, db_session):
        """Teacher says 'No' → can resend student list"""
        # ...
```

---

## 📋 PHASE D: Edge Case Handling (TDD)
**Priority:** 🟡 HIGH
**Time:** 1-2 days
**Test Files:** Update existing + new edge case tests

### D1. Student Count Mismatch

**Failing Tests:**
```python
class TestStudentCountMismatch:
    @pytest.mark.asyncio
    async def test_teacher_count_50_sends_48_names(self, db_session):
        """Teacher says 50 students, sends 48 → warned + asked to confirm"""
        teacher = Teacher(conversation_state={
            "data": {"student_count": 50}
        })

        # Send 48 names
        names = "\n".join([f"{i}. Name{i}" for i in range(1, 49)])
        result = await executor._collect_student_list(teacher, names)

        # Should warn about mismatch
        assert "48 names" in result.message_content
        assert "expected 50" in result.message_content
        assert result.next_step == "CONFIRM_STUDENT_CREATION"
```

### D2. Duplicate Student Names

**Failing Tests:**
```python
class TestDuplicateStudentNames:
    @pytest.mark.asyncio
    async def test_detect_duplicate_names(self, db_session):
        """Teacher sends '1. Kwame 2. Kwame' → warned"""
        names = "1. Kwame\n2. Kwame"
        result = await executor._collect_student_list(teacher, names)

        assert "duplicate" in result.message_content.lower()
        assert "Kwame appears 2 times" in result.message_content
        # Ask for disambiguation or confirmation
```

### D3. Multiple Children Per Parent

**Failing Tests:**
```python
class TestMultipleChildren:
    @pytest.mark.asyncio
    async def test_parent_can_link_second_child(self, db_session):
        """Parent already has one child → can link to second"""
        parent = Parent(...)
        child1 = Student(primary_parent_id=parent.id, ...)
        child2 = Student(primary_parent_id=None, ...)  # Unlinked

        # Parent types "ADD CHILD"
        result = await executor.process_message(..., "ADD CHILD", ...)

        # Should show student selection (excluding child1)
        # ...
```

### D4. Child Name Misspelled (Fuzzy Match)

**Failing Tests:**
```python
class TestFuzzyStudentMatch:
    @pytest.mark.asyncio
    async def test_parent_searches_for_misspelled_name(self, db_session):
        """Parent can't find 'Kwame' (teacher typed 'Kwane') → fuzzy search helps"""
        students = [
            Student(full_name="Kwane Mensah", ...),  # Typo
            Student(full_name="Ama Osei", ...)
        ]

        # Parent types "SEARCH Kwame"
        result = await executor.process_message(..., "SEARCH Kwame", ...)

        # Should suggest "Kwane" (close match)
        assert "Did you mean" in result.message_content
        assert "Kwane" in result.message_content
```

### D5. Session Timeout

**Failing Tests:**
```python
class TestSessionTimeout:
    @pytest.mark.asyncio
    async def test_conversation_state_expires_after_24_hours(self, db_session):
        """Parent abandons flow → state expires after 24h"""
        old_time = datetime.now(UTC) - timedelta(hours=25)
        parent = Parent(
            conversation_state={"flow": "FLOW-ONBOARD", "step": "..."},
            last_message_at=old_time
        )
        db_session.add(parent)
        await db_session.commit()

        # Parent returns after 25 hours
        result = await executor.process_message(..., "Hi", ...)

        # Should have cleared expired state
        await db_session.refresh(parent)
        assert parent.conversation_state is None
        # Should start fresh
        assert "Welcome" in result.message_content
```

**Implementation:**
- Add `last_message_at` field to Parent and Teacher models
- Check expiry before processing message
- Clear expired states
- Send "Your session expired, let's start fresh" message

---

## 📋 PHASE E: School Deduplication (TDD)
**Priority:** 🟡 HIGH
**Time:** 1 day
**Test File:** `tests/unit/test_school_matching.py` (NEW)

### E1. Fuzzy School Name Matching

**Failing Tests:**
```python
class TestSchoolFuzzyMatching:
    @pytest.mark.asyncio
    async def test_find_exact_match(self, db_session):
        """'St. Mary's JHS' matches exactly"""
        existing = School(name="St. Mary's JHS, Accra", ...)
        db_session.add(existing)
        await db_session.commit()

        matches = await find_matching_schools(db_session, "St. Mary's JHS, Accra")
        assert len(matches) == 1
        assert matches[0].id == existing.id

    @pytest.mark.asyncio
    async def test_find_fuzzy_match_punctuation(self, db_session):
        """'St Marys JHS' matches 'St. Mary's JHS' (punctuation diff)"""
        existing = School(name="St. Mary's JHS, Accra", ...)
        db_session.add(existing)
        await db_session.commit()

        matches = await find_matching_schools(db_session, "St Marys JHS Accra")
        assert len(matches) == 1
        assert matches[0].id == existing.id

    @pytest.mark.asyncio
    async def test_find_fuzzy_match_capitalization(self, db_session):
        """'st. mary's jhs' matches 'St. Mary's JHS'"""
        # ...

    @pytest.mark.asyncio
    async def test_no_match_different_school(self, db_session):
        """'St. Paul's' does NOT match 'St. Mary's'"""
        existing = School(name="St. Mary's JHS", ...)
        db_session.add(existing)
        await db_session.commit()

        matches = await find_matching_schools(db_session, "St. Paul's JHS")
        assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_suggest_similar_schools(self, db_session):
        """Returns top 3 similar schools for user to choose"""
        schools = [
            School(name="St. Mary's JHS, Accra", ...),
            School(name="St. Mary's Primary, Accra", ...),
            School(name="St. Peter's JHS, Accra", ...),
        ]
        db_session.add_all(schools)
        await db_session.commit()

        # Teacher types "St Mary JHS Accra"
        suggestions = await find_matching_schools(
            db_session,
            "St Mary JHS Accra",
            max_results=3
        )

        # Should suggest top matches
        assert len(suggestions) <= 3
        assert schools[0] in suggestions  # Exact match should be first
```

**Implementation:**
- Create `src/gapsense/core/school_matching.py`
- Use `fuzzywuzzy` or `rapidfuzz` library
- Normalize: lowercase, remove punctuation, strip whitespace
- Score matches, return top N

### E2. Integration with Teacher Flow

**Failing Tests:**
```python
class TestTeacherSchoolSelection:
    @pytest.mark.asyncio
    async def test_teacher_school_name_suggests_matches(self, db_session):
        """Teacher enters school name → shown similar schools to choose from"""
        existing = School(name="St. Mary's JHS, Accra", ...)
        db_session.add(existing)
        await db_session.commit()

        teacher = Teacher(...)
        result = await executor._collect_school_name(teacher, "St Marys JHS")

        # Should show matches
        assert "found similar" in result.message_content.lower()
        assert "St. Mary's JHS, Accra" in result.message_content
        assert result.next_step == "CONFIRM_SCHOOL_SELECTION"

    @pytest.mark.asyncio
    async def test_teacher_confirms_existing_school(self, db_session):
        """Teacher confirms → uses existing school"""
        # ...

    @pytest.mark.asyncio
    async def test_teacher_creates_new_school(self, db_session):
        """Teacher says 'Create new' → creates school"""
        # ...
```

---

## 📋 PHASE F: Session Management (TDD)
**Priority:** 🟡 MEDIUM
**Time:** 4-6 hours
**Test File:** `tests/unit/test_session_management.py` (NEW)

### F1. Track Last Message Time

**Migration Required:**
```sql
ALTER TABLE parents ADD COLUMN last_message_at TIMESTAMPTZ;
ALTER TABLE teachers ADD COLUMN last_message_at TIMESTAMPTZ;
```

**Failing Tests:**
```python
class TestLastMessageTracking:
    @pytest.mark.asyncio
    async def test_updates_last_message_at_on_message(self, db_session):
        """Each message updates last_message_at"""
        before = datetime.now(UTC)
        parent = Parent(phone="+233501234567")
        db_session.add(parent)
        await db_session.commit()

        await executor.process_message(parent, "text", "Hi", "wamid.1")

        await db_session.refresh(parent)
        assert parent.last_message_at is not None
        assert parent.last_message_at >= before
```

### F2. Expire Old Sessions

**Failing Tests:**
```python
class TestSessionExpiry:
    @pytest.mark.asyncio
    async def test_clear_state_if_expired(self, db_session):
        """Session > 24h old → cleared before processing"""
        # Already tested in Phase D
```

---

## 📊 IMPLEMENTATION ORDER (Recommended)

### Week 1 (Days 1-5)
**Day 1:** Phase A - Input Validation
- Write all validation tests
- Implement validation functions
- Integrate into flows
- Run tests → all pass

**Day 2:** Phase B - Error Recovery
- Write RESTART/CANCEL/HELP/STATUS tests
- Implement command detection
- Integrate into both executors
- Run tests → all pass

**Day 3:** Phase C - Confirmation Steps
- Write confirmation tests
- Add confirmation steps to flows
- Update conversation state machine
- Run tests → all pass

**Day 4:** Phase D (Part 1) - Basic Edge Cases
- Student count mismatch
- Duplicate names detection
- Run tests → all pass

**Day 5:** Phase D (Part 2) - Session Timeout
- Write session tests
- Create migration for last_message_at
- Implement expiry logic
- Run tests → all pass

### Week 2 (Days 6-7)
**Day 6:** Phase E - School Deduplication
- Install fuzzywuzzy
- Write fuzzy matching tests
- Implement school matching
- Integrate into teacher flow
- Run tests → all pass

**Day 7:** Phase F - Polish & Testing
- Multiple children support
- Fuzzy student name search
- Full integration testing
- Fix any discovered issues

---

## 📈 SUCCESS METRICS

### Test Coverage Goals
- **Before:** ~60-66% coverage
- **After:** >80% coverage
- **New modules:** >90% coverage (validation, matching)

### Tests Added (Estimated)
- Phase A: ~20 tests
- Phase B: ~15 tests
- Phase C: ~10 tests
- Phase D: ~15 tests
- Phase E: ~12 tests
- Phase F: ~8 tests
- **Total: ~80 new tests**

### Edge Cases Resolved
- From gap analysis: 30+ edge cases
- **Resolved by this plan: ~20-25 edge cases** (80%)
- Remaining: Infrastructure-dependent (hosting, monitoring, etc.)

---

## 🚫 OUT OF SCOPE (Cannot TDD)

These require infrastructure work, not code:

1. **L1 Translations** - Need actual Twi translations from native speakers
2. **WhatsApp Business API** - Need Meta approval, production number
3. **Production Hosting** - Need AWS/GCP setup
4. **Monitoring** - Need Sentry, CloudWatch, etc.
5. **CI/CD** - Need GitHub Actions setup
6. **Security Audit** - Need external auditor
7. **Compliance Docs** - Need legal team

**Estimated Time for Out-of-Scope:** 2-3 weeks (parallel to TDD work)

---

## 📝 NOTES

### Why TDD for These Fixes?
1. **Edge cases are complex** - Easy to miss scenarios without tests
2. **Regression prevention** - Ensure fixes don't break existing flows
3. **Documentation** - Tests serve as living documentation
4. **Confidence** - Can refactor with confidence

### Red → Green → Refactor Cycle
For each test:
1. **Red:** Write failing test
2. **Green:** Write minimal code to pass
3. **Refactor:** Clean up, optimize, document
4. **Repeat:** Next test

### Running Tests
```bash
# Run all tests
poetry run pytest tests/ -v

# Run specific phase
poetry run pytest tests/unit/test_input_validation.py -v

# Run with coverage
poetry run pytest tests/ --cov=src/gapsense --cov-report=html
```

---

**Created:** February 16, 2026
**Ready to Start:** Phase A (Input Validation)
**Estimated Completion:** 7 days (with tests)
