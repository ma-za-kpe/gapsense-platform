# Uganda Primary Mathematics (P1-P7)

This directory contains the mathematics curriculum data for Uganda's primary education (P1-P7, ages 6-13).

## Curriculum Information

**Grades**: P1-P7 (Primary 1-7)
**Age Range**: 6-13 years
**Curriculum Authority**: National Curriculum Development Centre (NCDC)
**Curriculum Version**: Thematic Curriculum (2007, revised)
**Assessment**: PLE (Primary Leaving Examination) at end of P7

## Unique Curriculum Structure

Uganda's primary curriculum differs significantly from Ghana's due to its **thematic approach** for early grades:

### P1-P3: Thematic Curriculum
- **Structure**: 12 themes, 36 sub-themes per year
- **Duration**: Each sub-theme = 1 week of teaching
- **Approach**: Mathematics integrated into life contexts, not taught as standalone subject
- **Learning Areas**: Literacy, Mathematics, Life Skills, Creative Arts, Physical Education

**Example Theme Structure**:
- Theme: "Food and Nutrition"
- Sub-theme: "Preparing meals"
- Math integration: Counting ingredients, measuring quantities, sharing portions
- Learning outcomes: Counting to 50, simple addition, measurement concepts

### P4-P7: Subject-Based Curriculum
- **Approach**: Traditional subject teaching (similar to Ghana B4-B6)
- **Mathematics**: Standalone subject with explicit learning outcomes
- **Core Subjects**: English, Mathematics, Science, Social Studies, Religious Education

## Node Code Format

```
P{grade}.MATH.{strand}.{learning_outcome}
```

Example: `P4.MATH.NUM.LO3` = Primary 4, Mathematics, Number strand, Learning Outcome 3

Note: P1-P3 nodes may require different coding to reflect thematic integration.

## Current Status

**Version**: v0.1.0 (In Development)
**Phase**: Curriculum analysis and extraction
**Target**: Q3 2026 for prerequisite graph v1.0.0

### Development Challenges

1. **Thematic Curriculum Extraction (P1-P3)**
   - Math concepts embedded in weekly themes
   - Prerequisites not explicitly sequenced
   - Requires manual extraction from theme descriptions
   - May need separate prerequisite graph for P1-P3 vs P4-P7

2. **Language Transition**
   - P1-P3: Often taught in L1 (Luganda, Luo, Runyankitara, etc.)
   - P4+: Shift to English medium instruction
   - Diagnostic questions must account for this transition

3. **Evidence Gaps**
   - No Uganda-equivalent parent engagement RCT (like Wolf & Aurino for Ghana)
   - Limited published misconception studies for Uganda
   - UWEZO data exists but needs re-analysis for cascade paths

4. **Regional Variations**
   - Central (Buganda): Higher literacy, more resources
   - Northern (Acholi): Post-conflict recovery, different norms
   - Western/Eastern: Different languages, cultural contexts

## Development Roadmap

### Phase 1: Source Document Collection (Q2 2026) ⏳
- [x] Identify NCDC curriculum PDFs
- [ ] Download P1-P3 Thematic Curriculum documents
- [ ] Download P3 Teachers Guide
- [ ] Download P4-P7 subject-based curriculum documents
- [ ] Download P7 PLE materials

### Phase 2: Thematic Curriculum Mapping (Q2 2026)
- [ ] Extract all math-related learning outcomes from P1-P3 themes
- [ ] Map to explicit math concepts (e.g., "counting ingredients" → "counting fluency 1-50")
- [ ] Identify prerequisite relationships across themes
- [ ] Create thematic_curriculum_mapping.json
- [ ] Determine if P1-P3 needs separate graph from P4-P7

### Phase 3: Subject Curriculum Extraction (P4-P7) (Q2-Q3 2026)
- [ ] Extract learning outcomes from P4-P7 curriculum documents
- [ ] Identify strand structure
- [ ] Map prerequisite relationships
- [ ] Create initial node list (target: 40-50 nodes)

### Phase 4: Prerequisite Graph Construction (Q3 2026)
- [ ] Build unified or separate graphs for P1-P3 and P4-P7
- [ ] Define prerequisite relationships
- [ ] Estimate initial difficulty from UWEZO data
- [ ] Validate with Ugandan teachers
- [ ] Create prerequisite_graph_v1.0.json

### Phase 5: Evidence Collection (Q3-Q4 2026)
- [ ] Re-analyze UWEZO Uganda data for cascade paths
- [ ] Conduct misconception pilot study (500+ students, Kampala)
- [ ] Teacher interviews for prerequisite validation
- [ ] Create cascade_paths.json
- [ ] Create evidence_base.json

### Phase 6: Pilot Testing (Q4 2026 - Q1 2027)
- [ ] Launch with 200 parent-child pairs (Central Uganda)
- [ ] Test Luganda + Swahili language plugins
- [ ] Measure diagnostic accuracy
- [ ] Validate cascade paths
- [ ] Iterate on prerequisite graph

## NCDC Source Documents

All source documents are publicly available via NCDC website:

### P1-P3 Thematic Curriculum
1. **P1 Curriculum**: https://ncdc.go.ug/wp-content/uploads/2024/02/P1-Curriculum.pdf
2. **P2 Thematic Curriculum**: https://ncdc.go.ug/wp-content/uploads/2024/02/P2_Thematic_Curriculum_June_2011.pdf
3. **P3 Thematic Curriculum**: https://ncdc.go.ug/wp-content/uploads/2024/02/P3_Thematic_Curr_21_November_2007_-_Edited.pdf
4. **P3 Teachers Guide**: https://ncdc.go.ug/wp-content/uploads/2024/02/P.3_teachers_guide_-_Book.pdf

### P7 Materials
5. **P7 Set One**: https://ncdc.go.ug/wp-content/uploads/2024/07/PRIMARY-SEVEN-SET-ONE.pdf

### Additional Documents Needed
- P4, P5, P6 Mathematics Syllabus/Curriculum (to be located on NCDC website)
- PLE past papers and marking schemes (for difficulty estimates)
- Teachers' guides for P4-P7

## Comparison: Uganda vs Ghana

| Aspect | Uganda (P1-P7) | Ghana (B1-B9) |
|--------|----------------|---------------|
| **Curriculum Approach** | Thematic (P1-P3), Subject (P4-P7) | Subject-based throughout |
| **Grade Span** | Primary only (7 grades) | Primary + JHS (9 grades) |
| **Curriculum Year** | 2007 (revised) | 2019 (Standards-Based), 2021 (CCP) |
| **Math Integration** | Embedded in themes (P1-P3) | Standalone subject all levels |
| **Language Transition** | L1 (P1-P3) → English (P4+) | More English throughout |
| **Evidence Base** | Limited (UWEZO only) | Strong (NEA, EGMA, research) |
| **Status** | In development | Production (primary v1.2.0) |

## Expected Strands (P4-P7)

Based on typical East African curricula, expected strands:
1. **Number** - Counting, operations, fractions, decimals
2. **Algebra** - Patterns, relationships (basic level)
3. **Geometry** - Shapes, spatial reasoning
4. **Measurement** - Length, mass, capacity, time
5. **Data Handling** - Collecting, presenting, interpreting data

*To be confirmed from NCDC curriculum documents.*

## Cascade Paths (Hypothesized)

Based on UWEZO data patterns and teacher interviews, we hypothesize similar cascade paths to Ghana:

1. **Place Value Cascade** (likely similar to Ghana CP-001)
2. **Fraction Concept Collapse** (universal pattern)
3. **Local → Standard Measurement Units** (unique to Uganda context)
4. **L1 → English Math Vocabulary Transition** (P4 transition challenge)

*To be validated with empirical data from pilot testing.*

## Regional Considerations

### Central Uganda (Buganda) - Luganda-speaking
- Urban: Kampala, Entebbe, Wakiso
- Higher literacy levels
- Pilot launch region
- Better resource availability

### Northern Uganda (Acholi) - Luo-speaking
- Post-conflict context
- Lower baseline literacy (UWEZO)
- Different cultural norms
- High-need priority region

### Western Uganda - Runyankitara-speaking
- Farming communities
- Moderate literacy
- Language cluster (inter-intelligible dialects)

### Eastern Uganda (Teso) - Ateso-speaking
- Trading communities
- Different language family (Nilo-Saharan vs Bantu)
- Moderate literacy

## Integration with GapSense Platform

### Platform Adaptations Needed

1. **Thematic Curriculum Support**
   - Handle P1-P3 nodes that map to themes, not explicit standards
   - Diagnostic questions must be context-aware (theme-based scenarios)

2. **Language Transition Support**
   - P1-P3 diagnostics in L1 (Luganda, Luo, etc.)
   - P4+ diagnostics in English with L1 support
   - Parent messaging follows language preference

3. **Cultural Context**
   - Use Uganda-specific materials (boda-boda, matoke, posho)
   - Avoid Ghana references (tro-tro, kenkey, cedis)
   - Timing: Evening 5-8pm (similar to Ghana)

## Evidence Sources (To Be Collected)

### Assessment Data
- **UWEZO Uganda**: Annual P3/P5 assessments (to be re-analyzed)
- **PLE Results**: P7 exit exam data (from UNEB)
- **School Data**: Diagnostic assessments from pilot schools

### Research Studies Needed
- Misconception study for Uganda students (P4-P7)
- Prerequisite validation study
- Parent engagement validation (Uganda-specific)
- Regional variation analysis (North vs Central vs West vs East)

### Partnerships Needed
- **NCDC**: Curriculum authority, validation
- **UWEZO Uganda**: Assessment data access
- **UNEB**: PLE item-level data
- **Universities**: Research partnerships (Makerere University)

## Related Files

- `/languages/uganda/` - Luganda, Swahili language plugins
- `/cultural_context/uganda.json` - Cultural grounding for Uganda
- `/curricula/uganda/country_config.json` - Education system configuration

## Next Immediate Steps

1. ✅ Create directory structure
2. ⏳ Download NCDC source documents (P1-P7 curricula)
3. ⏳ Extract math learning outcomes from thematic curriculum
4. ⏳ Map prerequisite relationships
5. ⏳ Create thematic_curriculum_mapping.json

## Questions to Resolve

1. **Graph Structure**: Single graph for P1-P7, or separate graphs for P1-P3 (thematic) vs P4-P7 (subject-based)?
2. **Language**: How to handle L1 instruction in P1-P3 for diagnostic questions?
3. **Thematic Mapping**: How granular should math extraction from themes be?
4. **Validation**: Who validates prerequisite relationships (teachers, NCDC, researchers)?

## Contact

For Uganda primary mathematics curriculum questions: uganda@gapsense.app

## Sources

- [NCDC Uganda Official Website](https://ncdc.go.ug/)
- UWEZO Uganda Assessment Reports
- UNESCO Uganda Education Statistics
