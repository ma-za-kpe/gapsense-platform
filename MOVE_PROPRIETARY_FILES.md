# Moving Proprietary Files to gapsense-data Repo

**CRITICAL: These files contain GapSense's core IP and must NEVER be in the platform repo.**

---

## Current Situation

Proprietary files are currently in `/Users/mac/Documents/projects/gapsense/` (platform repo location).

They need to be moved to a separate location and organized properly in the `gapsense-data` repo structure.

---

## Step 1: Set Up gapsense-data Repo Structure

```bash
# Navigate to parent directory
cd /Users/mac/Documents/projects

# Create gapsense-data directory structure
mkdir -p gapsense-data/{curriculum,prompts,business,seed_data}

# Initialize git repo (already done, but for reference)
cd gapsense-data
git init
git remote add origin https://github.com/ma-za-kpe/gapsense-data.git
```

---

## Step 2: Move Proprietary Files

### From gapsense/ directory, run:

```bash
cd /Users/mac/Documents/projects/gapsense

# Move curriculum data (CORE IP - prerequisite graph)
mv gapsense_prerequisite_graph.json ../gapsense-data/curriculum/
mv gapsense_prerequisite_graph_v1.1.json ../gapsense-data/curriculum/
mv gapsense_prerequisite_graph_v1.2.json ../gapsense-data/curriculum/
mv gapsense_prerequisite_graph_visual.mermaid ../gapsense-data/curriculum/

# Move prompt library (CORE IP - AI prompts)
mv gapsense_prompt_library.json ../gapsense-data/prompts/
mv gapsense_prompt_library_v1.1.json ../gapsense-data/prompts/

# Move business documents (CONFIDENTIAL)
mv GapSense_*.docx ../gapsense-data/business/

# Verify moves
echo "✅ Files moved. Checking platform repo is clean:"
ls -la gapsense_* 2>/dev/null || echo "✅ No gapsense_* files remaining in platform repo"
ls -la *.docx 2>/dev/null || echo "✅ No .docx files remaining in platform repo"
```

---

## Step 3: Commit to gapsense-data Repo

```bash
cd ../gapsense-data

# Create README explaining the structure
cat > README.md << 'EOF'
# GapSense Proprietary Data

**PRIVATE REPOSITORY - CORE INTELLECTUAL PROPERTY**

This repository contains GapSense's proprietary IP:
- NaCCA prerequisite graph (35 nodes, 6 cascade paths)
- AI prompt library (13 prompts)
- Business strategy documents

## Structure

```
gapsense-data/
├── curriculum/
│   ├── prerequisite_graph_v1.2.json       # Latest version - 35 nodes
│   ├── prerequisite_graph_v1.1.json       # Previous version
│   ├── prerequisite_graph.json            # Original version
│   └── prerequisite_graph_visual.mermaid  # Visual representation
├── prompts/
│   ├── prompt_library_v1.1.json           # Latest - 13 prompts
│   └── prompt_library.json                # Original
├── business/
│   ├── GapSense_Conceptual_Design.docx
│   ├── GapSense_MVP_Blueprint.docx
│   ├── GapSense_Monetization_Strategy.docx
│   ├── GapSense_Negotiation_Playbook.docx
│   ├── GapSense_ViztaEdu_Partnership_Documents.docx
│   ├── GapSense_ViztaEdu_Partnership_Proposal.docx
│   ├── GapSense_ViztaEdu_Term_Sheet_DRAFT.docx
│   └── GapSense_v2_AI_Native_Redesign.docx
└── seed_data/
    ├── regions.json
    └── districts.json
```

## Usage

The platform repo references this data via environment variable:

```bash
export GAPSENSE_DATA_PATH=/path/to/gapsense-data
```

## Security

- This repo is PRIVATE
- Access restricted to core team only
- 2FA required for all contributors
- Never clone on shared/public machines
- Never share files via unencrypted channels

## Version Control

- Latest versions have highest version number (v1.2 > v1.1 > v1.0)
- Keep old versions for rollback capability
- Document changes in commit messages
EOF

# Add .gitignore for safety
cat > .gitignore << 'EOF'
# Temporary files
*.tmp
*.bak
~*

# OS files
.DS_Store
Thumbs.db

# Editor files
.vscode/
.idea/
*.swp
EOF

# Commit everything
git add -A
git commit -m "feat: organize proprietary IP

## Structure
- curriculum/ - Prerequisite graph (3 versions + visual)
- prompts/ - AI prompt library (2 versions)
- business/ - Strategy documents (8 .docx files)
- seed_data/ - Non-proprietary Ghana data

## Security
- Private repo
- Access controlled
- Never to be made public"

# Push to GitHub
git push -u origin main
```

---

## Step 4: Configure Platform Repo to Use Data Repo

```bash
cd /Users/mac/Documents/projects/gapsense

# Create .env file (from .env.example)
cp .env.example .env

# Edit .env to add data path
echo "GAPSENSE_DATA_PATH=/Users/mac/Documents/projects/gapsense-data" >> .env

# Test access
ls $GAPSENSE_DATA_PATH/curriculum/prerequisite_graph_v1.2.json

# Should show the file
```

---

## Step 5: Verify Security

```bash
cd /Users/mac/Documents/projects/gapsense

# Verify .gitignore is blocking proprietary files
git check-ignore gapsense_prerequisite_graph.json
# Should output: gapsense_prerequisite_graph.json (meaning it's blocked)

# Verify no proprietary files can be added
touch test_prerequisite_graph.json
git add test_prerequisite_graph.json
# Should fail with: The following paths are ignored by one of your .gitignore files

# Clean up test
rm test_prerequisite_graph.json

# Verify git status is clean
git status
# Should show: nothing to commit, working tree clean
```

---

## Step 6: Update IMPLEMENTATION_PLAN.md Reference

The implementation plan references these files. Update it to note:

```markdown
**Data Location:** All proprietary IP is in separate `gapsense-data` repo.

Access via: `$GAPSENSE_DATA_PATH` environment variable.

Files:
- Prerequisite graph: `$GAPSENSE_DATA_PATH/curriculum/prerequisite_graph_v1.2.json`
- Prompt library: `$GAPSENSE_DATA_PATH/prompts/prompt_library_v1.1.json`
```

---

## Final Checklist

- [ ] gapsense-data repo created and structured
- [ ] All proprietary files moved to gapsense-data
- [ ] gapsense-data repo committed and pushed to GitHub
- [ ] gapsense-data repo set to PRIVATE on GitHub
- [ ] .env configured with GAPSENSE_DATA_PATH
- [ ] Verified no gapsense_*.json or *.docx files in platform repo
- [ ] Verified .gitignore blocking works
- [ ] Platform repo git status is clean

---

## What This Achieves

### Security
✅ Proprietary IP cannot accidentally be committed to platform repo
✅ Separate access control (data repo can have different collaborators)
✅ Clear separation of code vs. IP

### Flexibility
✅ Can open-source platform code later (without exposing IP)
✅ Can version data independently from code
✅ Can share business docs separately from technical specs

### Development
✅ Local development uses real data via $GAPSENSE_DATA_PATH
✅ Production uses data from encrypted S3/Secrets Manager
✅ CI/CD can use test fixtures without real IP

---

## Next Steps

After moving files:
1. Continue with implementation (Day 1: SQLAlchemy models)
2. Scripts will load data from $GAPSENSE_DATA_PATH
3. Never commit real data to platform repo again
