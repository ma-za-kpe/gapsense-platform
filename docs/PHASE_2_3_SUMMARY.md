# Phases 2-3 Implementation Summary

**Branch:** `feature/mvp-teacher-initiated`
**Date:** February 16, 2026
**Status:** Phase 2 Complete ✅ | Phase 3 In Progress 🚧

---

## ✅ Phase 2: Webhook Routing (COMPLETE)

### What Was Built:

**File:** `src/gapsense/webhooks/whatsapp.py`

**New Function:** `_detect_user_type(db, phone)` →  `(user_type, user_entity)`
- Checks if phone exists in `teachers` table (→ "teacher")
- If not, checks if phone exists in `parents` table (→ "parent")
- If not, creates new parent (default for unknown users)

**Updated:** `_handle_message()`
- Routes teacher messages to `TeacherFlowExecutor`
- Routes parent messages to `FlowExecutor`
- Logs user type for debugging

**Removed:** `_get_or_create_parent()` (deprecated)

### Key Design Decision:

**Unknown users default to parent flow.**
- Teachers MUST be pre-registered (via admin or future teacher registration flow)
- This prevents random users from creating teacher accounts
- Parents can self-onboard

### Testing Plan:
1. Create teacher record manually (phone: +233501111111)
2. Send "START" from teacher phone → should route to TeacherFlowExecutor
3. Send "Hi" from unknown phone → should create parent, route to FlowExecutor

---

## 🚧 Phase 3: Parent Linking (IN PROGRESS)

### Current Problem:

**Old Flow (WRONG):**
```
Parent sends "Hi"
→ System asks: "What is your child's first name?"
→ Asks age, grade
→ Creates NEW student record
→ Links to parent
```

**This violates the spec:** Teachers create students first, parents link to existing students.

### Required New Flow (SPEC):

```
Parent sends "START"
→ System: "Which child is yours? Select from the list:"
→ Shows students where primary_parent_id IS NULL (from teacher's roster)
→ Parent selects child
→ System links student.primary_parent_id = parent.id
→ Done!
```

### Implementation Plan:

**Step 1:** Query Students Without Parents
```python
async def _get_available_students(db: AsyncSession) -> list[Student]:
    """Get students without linked parents."""
    stmt = (
        select(Student)
        .where(Student.primary_parent_id == None)  # noqa: E711
        .where(Student.is_active == True)  # noqa: E712
        .order_by(Student.first_name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
```

**Step 2:** Show Student List to Parent
```python
# Option A: Use WhatsApp List Message (up to 10 students)
await client.send_list_message(
    to=parent.phone,
    body="Which child is yours? Select from your teacher's class:",
    button_text="Select child",
    sections=[{
        "title": "Students",
        "rows": [
            {"id": str(student.id), "title": student.first_name, "description": f"Class {student.current_grade}"}
            for student in students[:10]
        ]
    }]
)

# Option B: For more than 10 students, use numbered text list
message = "Which child is yours? Reply with the number:\n\n"
for i, student in enumerate(students, 1):
    message += f"{i}. {student.first_name} (Class {student.current_grade})\n"
```

**Step 3:** Link Parent to Selected Student
```python
# When parent selects student
selected_student_id = message_content.get("id")  # from list reply
student = await db.get(Student, selected_student_id)

# Link parent to student
student.primary_parent_id = parent.id
parent.onboarded_at = datetime.now(UTC)
parent.conversation_state = None

await db.commit()
```

### Files to Modify:

**`src/gapsense/engagement/flow_executor.py`:**

**Remove:**
- `_onboard_collect_child_name()` (line ~470)
- `_onboard_collect_child_age()` (line ~580)
- `_onboard_collect_child_grade()` (line ~700)
- Student creation logic (line ~910)

**Replace with:**
- `_onboard_select_student()` - Query and show student list
- `_onboard_link_student()` - Link parent to selected student

**Update:**
- `_onboard_opt_in()` - After opt-in, go to student selection (not child name)
- `_continue_onboarding()` - Route to new step handlers

### Edge Cases to Handle:

1. **No Students Available:**
   ```
   "Sorry, I couldn't find any students in the system.
    Please ask your child's teacher to share the GapSense number."
   ```

2. **Student Already Has Parent:**
   ```
   "This student already has a parent linked.
    Please contact your child's teacher if this is a mistake."
   ```

3. **Multiple Children (Future):**
   - For MVP: One parent, one student
   - For Phase 2: Allow parent to link multiple students

### Simplified Flow Diagram:

```
BEFORE (Old - WRONG):
├─ AWAITING_OPT_IN
├─ AWAITING_CHILD_NAME ❌ (remove)
├─ AWAITING_CHILD_AGE ❌ (remove)
├─ AWAITING_CHILD_GRADE ❌ (remove)
├─ AWAITING_LANGUAGE
└─ Complete → Create Student ❌ (remove)

AFTER (New - CORRECT):
├─ AWAITING_OPT_IN
├─ AWAITING_STUDENT_SELECTION ✅ (new)
├─ AWAITING_LANGUAGE
└─ Complete → Link Student ✅ (new)
```

### Database Queries Needed:

```sql
-- Get students without parents (for selection)
SELECT * FROM students
WHERE primary_parent_id IS NULL
  AND is_active = TRUE
ORDER BY first_name;

-- Link parent to student
UPDATE students
SET primary_parent_id = '<parent_id>'
WHERE id = '<selected_student_id>'
  AND primary_parent_id IS NULL;  -- Prevent overwrite

-- Complete parent onboarding
UPDATE parents
SET onboarded_at = NOW(),
    conversation_state = NULL
WHERE id = '<parent_id>';
```

---

## 📊 Progress Update

```
Phase 1: Foundation           ████████████████████ 100%
Phase 2: Webhook Routing      ████████████████████ 100% ✅
Phase 3: Parent Linking       ████████░░░░░░░░░░░░  40%
Phase 4: Dead Code Removal    ░░░░░░░░░░░░░░░░░░░░   0%
Phase 5: Testing              ░░░░░░░░░░░░░░░░░░░░   0%

OVERALL: ████████████░░░░░░░░ 60%
```

**Estimated Time Remaining:** 2-3 hours for Phases 3-5

---

## 🧪 Testing Strategy (Phase 5)

### Unit Tests to Add:
1. Test `_detect_user_type()` with teacher phone
2. Test `_detect_user_type()` with parent phone
3. Test `_detect_user_type()` with unknown phone
4. Test student selection flow
5. Test student linking

### Integration Tests to Update:
1. Update `test_whatsapp_flow_integration.py` - Remove student creation assertions
2. Add teacher → student → parent flow test
3. Test edge case: No students available
4. Test edge case: Student already has parent

### Tests to Remove:
- Remove tests that create students during parent onboarding
- Remove tests for child name/age/grade collection

---

## 🐛 Known Issues

### Issue 1: WhatsApp List Message Limit
**Problem:** WhatsApp list messages support max 10 items
**Solution:** For classes > 10 students, use numbered text list + parse number reply

### Issue 2: Student Name Ambiguity
**Problem:** Multiple students with same first name
**Solution:** Show "First Name (Class X)" in list to disambiguate

### Issue 3: Parent Manually Created Student
**Problem:** Some parents might have created students before teacher onboarded
**Solution:** For MVP, ignore. Phase 2: Add admin tool to reassign students

---

## 📝 Next Actions

1. **Complete Phase 3** (1-2 hours):
   - Replace child collection functions with student selection
   - Add student linking logic
   - Test with mock data

2. **Start Phase 4** (30 min):
   - Remove unused code (child name/age/grade collection)
   - Remove old diagnostic questionnaire flows

3. **Complete Phase 5** (1 hour):
   - Update existing tests
   - Add new tests for teacher/parent routing
   - Run full test suite

4. **Merge to develop** (after all tests pass):
   - Create PR with summary
   - Update documentation
   - Deploy to staging

---

**Last Updated:** February 16, 2026
**Next Update:** After Phase 3 complete
