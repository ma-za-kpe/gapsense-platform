# Viztracer Guide for GapSense

**Interactive execution flow visualization and performance analysis**

---

## Quick Start

```bash
# Trace a test (most useful)
./scripts/trace.sh test tests/integration/test_diagnostic_flow.py

# View the trace
./scripts/trace.sh view traces/test_trace_20260214_120000.json
```

Browser opens at http://localhost:9001 with interactive timeline.

---

## Common Use Cases

### 1. Debug Slow Diagnostic Sessions

**Problem:** A diagnostic session is taking 2+ seconds

```bash
# Trace the full diagnostic flow test
./scripts/trace.sh test tests/integration/test_diagnostic_flow.py::test_full_diagnostic_session
```

**What to look for in viewer:**
- Claude API call duration (expected: 500-1000ms)
- Database queries (should be <50ms each)
- Graph traversal (should be <100ms)
- If you see:
  - Multiple DB queries: N+1 query problem
  - Long graph traversal: Algorithm inefficiency
  - Multiple Claude calls: Unexpected behavior

---

### 2. Optimize Prerequisite Graph Loading

**Problem:** `load_curriculum.py` script is slow

```bash
# Trace curriculum loading
./scripts/trace.sh script scripts/load_curriculum.py
```

**What to look for:**
- Time in `parse_json()`
- Time in `create_nodes()`
- Database bulk insert timing
- Memory allocation patterns

---

### 3. Analyze API Request Handling

**Problem:** Need to see how FastAPI handles concurrent requests

```bash
# Start traced server
./scripts/trace.sh server

# In another terminal, make requests
curl -X POST http://localhost:8000/v1/diagnostics/sessions/123/answer \
  -H "Content-Type: application/json" \
  -d '{"answer": "42"}'

# Stop server (Ctrl+C)
# View trace
./scripts/trace.sh view traces/server_trace_*.json
```

**What to look for:**
- Async task switching
- Database connection pool usage
- Concurrent request handling
- Middleware execution order

---

### 4. Find Dead Code Paths

**Problem:** Not sure if a function is actually being called

```bash
# Trace comprehensive test suite
./scripts/trace.sh test tests/

# Search in viewer for function name
# If not found → dead code
```

---

### 5. Compare Before/After Optimization

```bash
# Trace before optimization
./scripts/trace.sh test tests/integration/test_diagnostic_flow.py
# Save as: traces/before_optimization.json

# Make optimization changes

# Trace after optimization
./scripts/trace.sh test tests/integration/test_diagnostic_flow.py
# Save as: traces/after_optimization.json

# Compare in viewer
./scripts/trace.sh view traces/before_optimization.json
./scripts/trace.sh view traces/after_optimization.json
```

---

## Understanding the Viewer

### Timeline View

```
Time (ms) →
0    100   200   300   400   500
│────│─────│─────│─────│─────│
├─ POST /answer [0-500ms]
│  ├─ validate_answer [0-5ms]      ← Click to see details
│  ├─ get_session [5-25ms]         ← DB query
│  ├─ evaluate [25-30ms]
│  ├─ decide_next [30-450ms]       ← Longest - drill down
│  │  ├─ traverse_graph [30-50ms]
│  │  ├─ call_claude [50-400ms]    ← AI call (expected)
│  │  └─ select_question [400-450ms]
│  └─ save_result [450-500ms]
```

**Controls:**
- **Click & drag**: Zoom into time range
- **Click function**: See details (arguments, return, duration)
- **Right-click**: Filter out this function
- **Search bar**: Find all calls to specific function

---

### Flamegraph View

```
       ┌────────────────────────────────────┐
       │  decide_next_question (420ms)      │ ← Widest = most time
       └────────────────────────────────────┘
                    │
        ┌───────────┴──────────┐
        │                      │
  ┌─────────────┐      ┌──────────────┐
  │ call_claude │      │ traverse     │
  │   (370ms)   │      │   (50ms)     │
  └─────────────┘      └──────────────┘
```

**How to read:**
- Width = total time spent
- Height = call stack depth
- Click to drill down
- Aggregates all calls to same function

---

## GapSense-Specific Patterns

### Expected Diagnostic Flow

```
1. API endpoint           [1-5ms]
2. Request validation     [1-3ms]
3. DB session fetch       [10-30ms]    ← Single query
4. Answer evaluation      [1-5ms]
5. Next question logic    [400-900ms]  ← Most time here
   ├─ Graph traversal     [20-50ms]
   ├─ Claude API          [350-800ms]  ← Expected bottleneck
   └─ Question selection  [10-30ms]
6. DB session update      [10-30ms]    ← Single query
7. Response formatting    [1-5ms]
```

**Total:** 450-1000ms (acceptable)

---

### Red Flags

❌ **N+1 Query Problem**
```
get_session         [10ms]
get_student         [10ms]  ← Should be joined
get_parent          [10ms]  ← Should be joined
get_district        [10ms]  ← Should be joined
```

❌ **Multiple Claude Calls**
```
call_claude [800ms]
call_claude [800ms]  ← Why twice?
call_claude [800ms]
```

❌ **Slow Graph Traversal**
```
traverse_graph [500ms]  ← Should be <100ms
```

❌ **Blocking I/O in Async**
```
read_file [200ms]  ← Use aiofiles
```

---

## Advanced Options

### Trace Specific Function Only

```bash
viztracer \
  --include_files "src/gapsense/diagnostic/" \
  --output_file diagnostic_only.json \
  -m pytest tests/integration/test_diagnostic_flow.py
```

### Reduce Noise

```bash
viztracer \
  --max_stack_depth=10 \
  --ignore_frozen \
  --exclude_files "sqlalchemy,anthropic" \
  --min_duration=0.001 \
  --output_file clean_trace.json \
  script.py
```

### Memory Profiling

```bash
viztracer \
  --log_gc \
  --log_async \
  --output_file memory_trace.json \
  script.py
```

---

## Troubleshooting

### Trace File Too Large

```bash
# Use filters
viztracer --min_duration=0.01 script.py  # Only >10ms calls

# Or compress
gzip traces/large_trace.json
vizviewer traces/large_trace.json.gz  # Works with compressed
```

### Viewer Won't Open

```bash
# Check if port 9001 is in use
lsof -i :9001

# Use different port
vizviewer --port 9002 trace.json
```

### Missing Function Calls

```bash
# Increase stack depth
viztracer --max_stack_depth=30 script.py

# Check if function is inlined (C extensions)
# Some functions won't appear (compiled code)
```

---

## Integration with Development Workflow

### Pre-Optimization

```bash
# 1. Identify slow endpoint/feature
# 2. Write integration test for it
# 3. Trace the test
./scripts/trace.sh test tests/integration/test_slow_feature.py

# 4. Open viewer, find bottleneck
./scripts/trace.sh view traces/test_trace_*.json

# 5. Optimize
# 6. Trace again, compare
```

### Performance Regression Testing

```bash
# Baseline trace (commit to git LFS or document metrics)
./scripts/trace.sh test tests/integration/test_critical_path.py

# Record metrics:
# - Total time: 450ms
# - Claude API: 350ms
# - DB queries: 50ms

# After changes, re-trace and compare
```

---

## Performance Targets (GapSense)

| Operation | Target | Acceptable | Flag |
|-----------|--------|------------|------|
| Diagnostic answer | <1000ms | 1000-1500ms | >1500ms |
| Claude API | <800ms | 800-1200ms | >1200ms |
| DB query (single) | <30ms | 30-50ms | >50ms |
| Graph traversal | <50ms | 50-100ms | >100ms |
| Parent message gen | <200ms | 200-400ms | >400ms |

---

## Resources

- [Viztracer Documentation](https://viztracer.readthedocs.io/)
- [FastAPI Performance Best Practices](https://fastapi.tiangolo.com/async/)
- [Async SQLAlchemy Performance](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

---

**Pro Tip:** Trace frequently during development. Don't wait until performance becomes a problem. Understanding execution flow helps catch bugs early.
