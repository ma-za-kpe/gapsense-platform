# gapsense-data ↔ gapsense-platform Architecture

**How the two repos communicate and why they're separated**

---

## The Two Repos Serve Different Purposes

### gapsense-data: STATIC DATA FILES (Proprietary IP)
- **What it is**: JSON files and business documents
- **What it's NOT**: No code, no application logic, no database
- **Purpose**: Version control for proprietary intellectual property
- **Access**: Private repo, restricted team only

**Contents:**
```
gapsense-data/
├── curriculum/
│   └── gapsense_prerequisite_graph_v1.2.json    # 35 nodes, relationships, misconceptions
├── prompts/
│   └── gapsense_prompt_library_v1.1.json        # 13 AI prompt templates
└── business/
    └── *.docx                                    # Strategy documents
```

**This is like a "data warehouse" - pure data, no processing.**

---

### gapsense-platform: APPLICATION CODE (Could be open-sourced later)
- **What it is**: Python/FastAPI application that processes data
- **What it's NOT**: No proprietary data hardcoded
- **Purpose**: The engine that makes GapSense work
- **Access**: Currently private, could be public in future

**Contents:**
```
gapsense-platform/
├── src/gapsense/
│   ├── core/models/         # SQLAlchemy table definitions (EMPTY)
│   ├── curriculum/          # Graph traversal algorithms
│   ├── diagnostic/          # Diagnostic engine
│   └── ...
├── scripts/
│   └── load_curriculum.py   # LOADER: JSON → PostgreSQL
└── infrastructure/
    └── cdk/                 # AWS deployment
```

**This is like the "application" - it loads and processes data.**

---

## Communication Flow

### 1. Development/Deployment Time (ONE-TIME LOAD)

```
┌─────────────────┐
│  gapsense-data  │  (JSON files on disk/S3)
│  (Static files) │
└────────┬────────┘
         │
         │ [1] Read JSON via GAPSENSE_DATA_PATH
         │
         ▼
┌─────────────────┐
│ Loader Scripts  │  (Python scripts in gapsense-platform)
│  - load_curriculum.py
│  - load_prompts.py
└────────┬────────┘
         │
         │ [2] Parse JSON, validate, insert
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │  (Runtime database)
│  curriculum_nodes
│  curriculum_prerequisites
│  curriculum_misconceptions
│  ...
└─────────────────┘
```

**This happens ONCE at startup or during migrations.**

---

### 2. Runtime (APPLICATION QUERIES DATABASE)

```
┌─────────────────┐
│   API Request   │  (GET /diagnostics/sessions)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI App    │  (gapsense-platform code)
│  - Diagnostic Engine
│  - Graph Traversal
└────────┬────────┘
         │
         │ [Query] SELECT * FROM curriculum_nodes WHERE code = 'B2.1.1.1'
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │  (Database with loaded data)
└─────────────────┘
```

**At runtime, application NEVER touches JSON files.**
**It only queries the database.**

---

## Why This Architecture?

### ✅ Security Benefits
1. **Proprietary IP protected**: Data repo can have different access control
2. **Can open-source platform later**: Code repo has no hardcoded IP
3. **Audit trail**: Data changes tracked separately from code changes
4. **Deployment safety**: Production can load data from encrypted S3, not from repo

### ✅ Development Benefits
1. **Data versioning**: Can rollback prerequisite graph independently of code
2. **Testing**: Can use test fixtures instead of real data
3. **Collaboration**: Business team can update .docx files without touching code
4. **CI/CD**: Can build platform repo without access to data repo

### ✅ Operational Benefits
1. **Data updates without redeployment**: Load new graph version to database
2. **A/B testing**: Can test different graph versions in same codebase
3. **Disaster recovery**: Data backup separate from code backup

---

## Configuration: How They Connect

### Local Development
```bash
# .env file in gapsense-platform
GAPSENSE_DATA_PATH=/Users/mac/Documents/projects/gapsense-data

# Loader script reads from this path
python scripts/load_curriculum.py
# → Reads $GAPSENSE_DATA_PATH/curriculum/gapsense_prerequisite_graph_v1.2.json
# → Inserts into PostgreSQL
```

### Production
```bash
# Data loaded from AWS Secrets Manager or encrypted S3
# Not from git repo (too slow, security risk)

# Option 1: S3
aws s3 cp s3://gapsense-data-encrypted/curriculum/prerequisite_graph_v1.2.json /tmp/
python scripts/load_curriculum.py --path /tmp/prerequisite_graph_v1.2.json

# Option 2: Baked into Docker image (encrypted layer)
COPY --from=data-repo /curriculum/*.json /app/data/
```

---

## The Missing Pieces (What We Need to Create)

### 1. Curriculum Loader (`scripts/load_curriculum.py`)
```python
# Reads: gapsense-data/curriculum/gapsense_prerequisite_graph_v1.2.json
# Writes: PostgreSQL curriculum_nodes, curriculum_prerequisites, etc.

async def load_prerequisite_graph():
    graph_path = settings.prerequisite_graph_path
    with open(graph_path) as f:
        data = json.load(f)

    # Parse and insert into database
    for node in data['nodes']:
        db_node = CurriculumNode(
            code=node['code'],
            title=node['title'],
            ...
        )
        session.add(db_node)

    await session.commit()
```

### 2. Prompt Loader (`src/gapsense/ai/prompt_loader.py`)
```python
# Reads: gapsense-data/prompts/gapsense_prompt_library_v1.1.json
# Keeps: In memory (loaded at app startup, not in database)

class PromptLibrary:
    def __init__(self):
        prompt_path = settings.prompt_library_path
        with open(prompt_path) as f:
            self.prompts = json.load(f)['prompts']

    def get_prompt(self, prompt_id: str) -> dict:
        return self.prompts[prompt_id]
```

**Prompts stay in memory (not database) because:**
- Small size (~50KB)
- Frequently accessed
- No complex queries needed
- Version tracked in code (not runtime data)

---

## When Data Changes

### Scenario: Update Prerequisite Graph (Add New Nodes)

```bash
# 1. Update data repo
cd gapsense-data
# Edit curriculum/gapsense_prerequisite_graph_v1.2.json
# Add 5 new literacy nodes
git commit -m "feat: add B3 literacy nodes (5 new nodes)"
git push origin main

# 2. Platform repo doesn't change (code is the same)
# But loader script needs to run again:
cd gapsense-platform
python scripts/load_curriculum.py --reload
# → Truncates old data
# → Loads new graph version
# → Database now has 40 nodes instead of 35

# 3. Application automatically uses new nodes
# No code changes needed!
```

---

## Summary Table

| Aspect | gapsense-data | gapsense-platform |
|--------|---------------|-------------------|
| **Type** | Static JSON files | Python application code |
| **Contains** | Proprietary IP (graph, prompts, docs) | Models, services, API endpoints |
| **Format** | JSON, .docx | Python, SQL |
| **At Runtime** | Not accessed | Runs and queries DB |
| **Version Control** | Track data changes | Track code changes |
| **Can Open Source?** | NEVER | Potentially (later) |
| **Access Pattern** | Read once at startup | Query continuously |
| **Updates** | Change JSON, reload DB | Deploy new code |

---

## Next Steps

1. ✅ Create `scripts/load_curriculum.py` - Load graph into DB
2. ✅ Create `src/gapsense/ai/prompt_loader.py` - Load prompts into memory
3. ✅ Test: JSON → DB → API query works end-to-end
4. Document deployment process (how production loads data)

---

**Key Insight**: The two repos are like "data warehouse" (gapsense-data) and "application" (gapsense-platform). They connect via loader scripts that run once, then the application queries the database, never touching the JSON files again.
