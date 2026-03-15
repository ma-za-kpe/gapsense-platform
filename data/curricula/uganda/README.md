# Uganda Curriculum Data

This directory contains Uganda-specific curriculum data for the GapSense diagnostic engine, based on the NCDC (National Curriculum Development Centre) Thematic Curriculum (2007, revised).

## Structure

```
uganda/
├── country_config.json              # Education system configuration
├── primary/                         # P1-P7
│   ├── source_documents/            # NCDC curriculum PDFs
│   ├── prerequisite_graph_v1.0.json  # In development
│   └── thematic_curriculum_mapping.json  # P1-P3 themes → math concepts
├── secondary/                       # S1-S6 (not yet implemented)
└── tertiary/                        # Not applicable
```

## Education System

### Primary Education (P1-P7)

Uganda's primary education covers ages 6-13:
- **P1-P3**: Thematic curriculum approach
- **P4-P7**: Subject-based curriculum

**Curriculum Authority**: National Curriculum Development Centre (NCDC)
**Curriculum Version**: 2007 (revised)
**Source**: https://ncdc.go.ug/

### Grade Structure

| Code | Grade Name | Age | Approach |
|------|------------|-----|----------|
| P1 | Primary 1 | 6 | Thematic |
| P2 | Primary 2 | 7 | Thematic |
| P3 | Primary 3 | 8 | Thematic |
| P4 | Primary 4 | 9 | Subject-based |
| P5 | Primary 5 | 10 | Subject-based |
| P6 | Primary 6 | 11 | Subject-based |
| P7 | Primary 7 | 12-13 | Subject-based |

**High-Stakes Assessment**: PLE (Primary Leaving Examination) at end of P7

### Secondary Education (Not Yet Implemented)

| Code | Level | Age | System |
|------|-------|-----|--------|
| S1-S4 | O-Level | 13-17 | Cambridge system |
| S5-S6 | A-Level | 17-19 | Cambridge system |

## Mathematics Curriculum Structure

### Thematic Curriculum (P1-P3)

**Approach**: 12 themes, 36 sub-themes per year
- Each sub-theme = 1 week of teaching
- Math integrated into life contexts
- Cross-curricular learning areas

**Learning Areas** (not subjects):
1. Literacy
2. Mathematics
3. Life Skills
4. Creative Arts
5. Physical Education

**Example Themes**:
- "Myself and My Family"
- "Food and Nutrition"
- "Health and Hygiene"
- "Our Community"
- "Animals and Plants"

**Math Integration**: Counting, basic operations, measurement embedded in thematic contexts

### Subject-Based Curriculum (P4-P7)

**Approach**: Traditional subject teaching
- Mathematics as standalone subject
- Learning outcomes organized by strands
- Closer to Ghana's approach

**Core Subjects**:
1. English
2. Mathematics
3. Science
4. Social Studies
5. Religious Education

### Node Code Format

```
P{grade}.{subject}.{strand}.{learning_outcome}
```

**Example**: `P4.MATH.NUM.LO3`
- P4: Primary 4
- MATH: Mathematics subject
- NUM: Number strand
- LO3: Learning Outcome 3

## Prerequisite Graph Development

### Status: In Development

**Current Phase**: Curriculum analysis and source document collection

**Target Timeline**:
- Q2 2026: Complete P1-P7 prerequisite graph v1.0.0
- Q3 2026: Pilot testing with Kampala cohorts
- Q4 2026: Validate and iterate based on feedback
- Q1 2027: Production release pending validation

### Challenges Unique to Uganda

1. **Thematic Approach (P1-P3)**
   - Math concepts embedded in life contexts
   - Prerequisite relationships less explicit
   - Requires careful extraction from theme descriptions

2. **Language Complexity**
   - Official languages: English + Swahili
   - Regional languages: Luganda (Central), Luo (North), Runyankitara (West), Ateso (East)
   - Thematic curriculum encourages L1 instruction in early grades

3. **Regional Variations**
   - Post-conflict recovery in Northern Uganda
   - Urban-rural divide more pronounced than Ghana
   - Different baseline literacy levels by region

4. **Evidence Gaps**
   - No Ghana-equivalent parent engagement RCT
   - Limited published misconception studies
   - UWEZO data needs re-analysis for cascade paths

## Source Documents (NCDC)

### Downloaded/To Be Downloaded

1. **P1 Curriculum** (PDF)
   - URL: https://ncdc.go.ug/wp-content/uploads/2024/02/P1-Curriculum.pdf
   - Status: To be downloaded
   - Purpose: Thematic structure, math learning outcomes

2. **P2 Thematic Curriculum** (PDF)
   - URL: https://ncdc.go.ug/wp-content/uploads/2024/02/P2_Thematic_Curriculum_June_2011.pdf
   - Status: To be downloaded
   - Purpose: Year 2 themes and math integration

3. **P3 Thematic Curriculum** (PDF)
   - URL: https://ncdc.go.ug/wp-content/uploads/2024/02/P3_Thematic_Curr_21_November_2007_-_Edited.pdf
   - Status: To be downloaded
   - Purpose: Year 3 themes, transition to P4

4. **P3 Teachers Guide** (PDF)
   - URL: https://ncdc.go.ug/wp-content/uploads/2024/02/P.3_teachers_guide_-_Book.pdf
   - Status: To be downloaded
   - Purpose: Implementation guidance, assessment criteria

5. **P7 Materials** (PDF)
   - URL: https://ncdc.go.ug/wp-content/uploads/2024/07/PRIMARY-SEVEN-SET-ONE.pdf
   - Status: To be downloaded
   - Purpose: Exam preparation, learning outcomes

### Additional Sources Needed

- P4-P6 subject-based curriculum documents
- NCDC Mathematics syllabus guides
- PLE past papers and marking schemes
- UWEZO Uganda assessment data

## Evidence Base (To Be Collected)

### National Assessments

1. **UWEZO Uganda Reports**
   - Annual learning assessments
   - P3 and P5 literacy and numeracy data
   - Regional breakdowns available
   - **Action**: Re-analyze for cascade paths

2. **Uganda National Examinations Board (UNEB)**
   - PLE results and item analysis
   - Can identify common failure patterns
   - **Action**: Request research partnership

3. **UNESCO Uganda Education Statistics**
   - Enrollment and completion rates
   - Regional variations
   - Baseline literacy levels

### Research Studies (Gaps to Fill)

1. **Misconception Studies**
   - **Gap**: No published Uganda-specific studies found
   - **Action**: Conduct pilot study with 500+ students
   - **Priority**: High (needed for diagnostic accuracy)

2. **Parent Engagement Study**
   - **Gap**: No Uganda equivalent to Wolf & Aurino (2020)
   - **Action**: Design RCT for Kampala cohorts
   - **Priority**: High (informs messaging strategy)

3. **Regional Learning Patterns**
   - **Gap**: Limited research on North vs Central vs West vs East
   - **Action**: Analyze UWEZO regional data
   - **Priority**: Medium

4. **Cascade Path Validation**
   - **Gap**: No research on prerequisite failure patterns
   - **Action**: Correlational analysis of UWEZO item-level data
   - **Priority**: High (core to diagnostic engine)

## Cascade Paths (To Be Identified)

Pending UWEZO data analysis. Expected patterns based on regional teacher interviews:

### Hypothesized Cascade Paths

1. **Counting → Place Value → Operations** (likely similar to Ghana)
2. **Fractions Concept → Fraction Operations** (universal pattern)
3. **Local Measurement Units → Standard Units** (unique to Uganda/East Africa context)
4. **L1 Math Vocabulary → English Math Vocabulary** (language transition at P4)

**Validation Required**: Cannot confirm without empirical data

## Regional Context

### Central Uganda (Buganda) - Luganda-speaking
- **Urban Centers**: Kampala, Entebbe, Wakiso
- **Literacy**: Highest in country
- **Languages**: Luganda + English, some Swahili
- **Materials**: Wide availability (urban infrastructure)
- **Priority**: Pilot launch region

### Northern Uganda (Acholi) - Luo-speaking
- **Context**: Post-conflict recovery (LRA insurgency impact)
- **Literacy**: Lower than national average (UWEZO data)
- **Languages**: Luo + some English/Swahili
- **Materials**: Limited (rural, electricity not guaranteed)
- **Priority**: High need, requires careful cultural adaptation
- **Cultural**: Different norms from Central Uganda

### Western Uganda - Runyankitara-speaking
- **Context**: Farming communities (Banyankole, Banyoro, Batoro)
- **Languages**: Runyankitara cluster (inter-intelligible)
- **Literacy**: Moderate
- **Priority**: Medium (after Central/Northern validation)

### Eastern Uganda (Teso) - Ateso-speaking
- **Context**: Mixed farming and trading
- **Languages**: Ateso (Nilo-Saharan, different from Bantu languages)
- **Literacy**: Moderate
- **Priority**: Medium

## Thematic Curriculum Mapping (P1-P3)

### Challenge

Math learning outcomes are embedded in weekly themes, not explicitly sequenced as prerequisites.

**Example** (P2 Theme: "Food and Nutrition"):
- Sub-theme: "Preparing meals"
- Math integration: "Counting ingredients, measuring quantities"
- Learning outcomes: Counting to 50, simple addition, measurement concepts

**Approach**:
1. Extract all math-related learning outcomes from themes
2. Map to explicit math concepts (e.g., "counting ingredients" → "counting fluency 1-50")
3. Identify prerequisite relationships across themes
4. Create separate prerequisite graph for P1-P3 vs P4-P7
5. Map transition from thematic to subject-based

### Thematic Mapping File

`thematic_curriculum_mapping.json` (to be created):
```json
{
  "P1": {
    "themes": [...],
    "math_outcomes_extracted": [...],
    "mapped_concepts": [...]
  },
  "P2": {...},
  "P3": {...}
}
```

## Comparison: Uganda vs Ghana

| Aspect | Uganda | Ghana |
|--------|--------|-------|
| **Grades** | P1-P7 (Primary) | B1-B9 (includes JHS) |
| **Approach** | Thematic (P1-P3), Subject (P4-P7) | Subject-based throughout |
| **Curriculum Authority** | NCDC | NaCCA |
| **Curriculum Year** | 2007 (revised) | 2019 (Standards-Based) |
| **Languages** | English + Swahili official; Luganda, Luo, etc. regional | English official; Twi, Ewe, Ga, etc. common |
| **Evidence Base** | Limited (UWEZO) | Strong (NEA, EGMA, research) |
| **Status** | In development | Production (v1.2.0) |
| **Cascade Paths** | To be identified | 6 identified |
| **Misconceptions** | To be researched | Documented (Abugri & Mereku 2024) |

## Development Roadmap

### Phase 1: Curriculum Analysis (Q2 2026)
- ✅ Country configuration created
- ⏳ Download NCDC source documents
- ⏳ Extract P1-P3 thematic math outcomes
- ⏳ Analyze P4-P7 subject-based curriculum
- ⏳ Create initial node list (target: 40-45 nodes)

### Phase 2: Prerequisite Graph Construction (Q2 2026)
- ⏳ Define prerequisite relationships
- ⏳ Map to NCDC learning outcomes
- ⏳ Estimate initial difficulty (from UWEZO data)
- ⏳ Create prerequisite_graph_v1.0.json
- ⏳ Validate with Ugandan teachers

### Phase 3: Evidence Collection (Q3 2026)
- ⏳ Re-analyze UWEZO data for cascade paths
- ⏳ Conduct misconception pilot study (500 students)
- ⏳ Teacher interviews for prerequisite validation
- ⏳ Create cascade_paths.json
- ⏳ Create misconceptions.json

### Phase 4: Pilot Testing (Q3-Q4 2026)
- ⏳ Launch with 200 parent-child pairs (Kampala)
- ⏳ Test Luganda + Swahili language plugins
- ⏳ Measure diagnostic accuracy
- ⏳ Gather parent feedback
- ⏳ Iterate on prerequisite graph

### Phase 5: Production Release (Q1 2027)
- ⏳ Validate cascade paths with pilot data
- ⏳ Update difficulty estimates
- ⏳ Get NCDC official endorsement (if possible)
- ⏳ Release v1.0.0 for production use
- ⏳ Plan regional expansion (Northern Uganda)

## Research Partnerships Needed

1. **NCDC** - Official curriculum authority
   - Access to internal curriculum documents
   - Validation of prerequisite relationships
   - Potential endorsement

2. **UWEZO Uganda** - Assessment organization
   - Access to item-level data
   - Collaboration on cascade path identification
   - Regional breakdown analysis

3. **Universities** (Makerere University, etc.)
   - Misconception research studies
   - Parent engagement validation
   - Graduate student thesis opportunities

4. **District Education Offices**
   - Pilot testing in schools
   - Teacher recruitment for validation
   - Cultural appropriateness review

## Integration with Other Data

### Language Plugins (`/languages/uganda/`)
- English (en)
- Swahili (sw) - 25% speakers, official language
- Luganda (lg) - 16% speakers, Central region
- *Planned*: Runyankitara, Luo, Ateso

### Cultural Context (`/cultural_context/uganda.json`)
- Common names (twin names, clan names)
- Household materials (boda-boda, matoke, posho)
- Regional differences (Baganda, Acholi, Banyankole, Iteso)
- Time references (evening 5-8pm best for activities)

### Platform Code (`/gapsense-platform/`)
- Will need to handle thematic curriculum mapping
- Language switching at P4 transition (L1 → English)
- Regional adaptation logic

## Questions and Uncertainties

1. **Thematic Curriculum**
   - How to best extract prerequisite relationships from integrated themes?
   - Should P1-P3 have separate graph from P4-P7?

2. **Language Transition**
   - Many students taught in L1 (P1-P3) then switch to English (P4+)
   - How to handle diagnostic questions across this transition?

3. **Regional Validity**
   - Will prerequisite relationships hold across North vs Central vs West vs East?
   - Need regional pilot data to confirm

4. **Cascade Paths**
   - Can we assume similar patterns to Ghana, or are there Uganda-specific patterns?
   - UWEZO data analysis critical

## Contributing

This is preliminary work. Contributions needed:

- **NCDC Curriculum Experts**: Validate prerequisite relationships
- **Ugandan Teachers**: Review node definitions, suggest additions
- **Researchers**: Misconception studies, cascade path validation
- **Native Speakers**: Language plugin validation (Luganda, Swahili)

Contact: uganda@gapsense.app

## Related Files

- `/languages/uganda/` - Language-specific messaging
- `/cultural_context/uganda.json` - Cultural grounding
- `/docs/thematic_curriculum_guide.md` - Guidance on P1-P3 mapping
- `/docs/prerequisite_graph_spec.md` - Technical graph specification

## Status

- **Version**: Pre-v1.0.0 (in development)
- **Last Updated**: March 2026
- **Status**: Development (not ready for pilot)
- **Next Milestone**: Complete curriculum analysis and prerequisite graph v1.0.0 (Q2 2026)
- **Coverage**: P1-P7 mathematics (to be developed)
