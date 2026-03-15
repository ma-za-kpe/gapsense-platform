# Production Curriculum Data Issue

**Date:** March 15, 2026
**Status:** 🔴 CRITICAL BUG
**Impact:** Gap profiles are empty (gap_nodes_count=0)

---

## Problem Description

The production database does not have curriculum data loaded. This causes:

1. ✅ Image analysis completes successfully
2. ✅ AI identifies gaps correctly (`B7.1.2.1`, `B7.1.2.2`, `B8.2.1.3`, `B3.1.1.1.1`)
3. ❌ Database lookup returns 0 curriculum nodes
4. ❌ Gap profile saved with `gap_nodes_count=0`
5. ❌ Dashboard shows "No gaps identified yet"
6. ❌ Demo polling times out waiting for gap tags to appear

---

## Evidence

### Worker Logs (23:12:55 UTC)
```
[info] grok_analysis_response
    gap_node_ids=['B7.1.2.1', 'B7.1.2.2', 'B8.2.1.3', 'B3.1.1.1.1']
    gaps_found=4

[info] gap_profile_saved
    gap_nodes_count=0  ← SHOULD BE 4!
    student_name=Maame
```

### Dashboard Output
```html
<h2>📝 Latest Analysis: Maame</h2>
<div class="report-section">
    <h3>❌ Errors Found (3)</h3>
    <!-- Shows errors correctly -->
</div>

<div class="student-card">
    <div class="name">Maame Maame</div>
    <div class="info">✅ No gaps identified yet</div>  ← WRONG!
</div>
```

---

## Root Cause

**File:** `src/gapsense/engagement/exercise_book_scanner.py:198-201`

```python
gap_codes = analysis.get("gap_node_ids", [])
gap_nodes = []
if gap_codes:
    nodes_result = await self.db.execute(
        select(CurriculumNode.id).where(CurriculumNode.code.in_(gap_codes))
    )
    gap_nodes = [row[0] for row in nodes_result.fetchall()]  # Returns []
```

The `CurriculumNode` table is empty in production.

---

## Solutions

### Option 1: Load via API Endpoint (Recommended)
Create an admin endpoint to POST curriculum JSON directly.

### Option 2: Load via SSH Tunnel
```bash
# From EC2 bastion or via Systems Manager Session Manager
ssh -L 5432:gapsense-prod.c6d7rnvqrzeg.us-east-1.rds.amazonaws.com:5432 ec2-user@<bastion-ip>

# Then run locally
DATABASE_URL="postgresql+asyncpg://gapsense_admin:PASSWORD@localhost:5432/gapsense_prod" \  # pragma: allowlist secret
python load_curriculum_prod.py
```

### Option 3: ECS Exec into Running Task
```bash
aws ecs execute-command \
  --cluster gapsense-prod \
  --task <task-arn> \
  --container web \
  --interactive \
  --command "python scripts/load_curriculum.py --path=../gapsense-data/curriculum/gapsense_prerequisite_graph_v1.2.json" \
  --region us-east-1
```

### Option 4: One-Time ECS Task
Create a task definition that:
1. Mounts gapsense-data repo
2. Runs load_curriculum.py
3. Exits

---

## Immediate Workaround

For demo purposes, you can:
1. Manually refresh the dashboard at `http://PROD_URL/demo/reports/+233501234567`
2. The "Latest Analysis" section shows errors/patterns correctly
3. Ignore the "No gaps identified yet" message

---

## Priority

**P0 - CRITICAL**
Must be fixed before:
- ❌ Any real teacher testing
- ❌ Public demo sessions
- ❌ Investor presentations

**Current Status:** Demo mode works, but gaps don't show in student cards.

---

## Next Steps

1. Create `/admin/load-curriculum` POST endpoint
2. Upload curriculum JSON via HTTP
3. Verify gaps appear in dashboard
4. Test demo flow end-to-end
