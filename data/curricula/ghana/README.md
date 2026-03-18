# Ghana Curriculum Data

This directory contains Ghana-specific curriculum data for the GapSense diagnostic engine, based on the NaCCA (National Council for Curriculum and Assessment) Standards-Based Curriculum (2019).

## Structure

```
ghana/
├── country_config.json              # Education system configuration
├── primary/                         # Basic 1-9 (includes JHS)
│   ├── prerequisite_graph_v1.0.json   # Initial version (2024)
│   ├── prerequisite_graph_v1.1.json   # Added cascade paths (2025)
│   └── prerequisite_graph_v1.2.json   # Current version (March 2026)
├── secondary/                       # SHS 1-3 (not yet implemented)
└── tertiary/                        # Not applicable
```

## Education System

### Basic Education (B1-B9)

Ghana's basic education covers ages 6-15:
- **Basic 1-6**: Primary level (formerly Primary 1-6)
- **Basic 7-9**: Junior High School (formerly JHS 1-3)

**Curriculum Authority**: National Council for Curriculum and Assessment (NaCCA)
**Curriculum Version**: Standards-Based Curriculum, 2019
**Source**: https://nacca.gov.gh/

### Grade Structure

| Code | Grade Name | Age | Level |
|------|------------|-----|-------|
| B1 | Basic 1 | 6 | Primary |
| B2 | Basic 2 | 7 | Primary |
| B3 | Basic 3 | 8 | Primary |
| B4 | Basic 4 | 9 | Primary |
| B5 | Basic 5 | 10 | Primary |
| B6 | Basic 6 | 11 | Primary |
| B7 | Basic 7 (JHS 1) | 12 | Junior High |
| B8 | Basic 8 (JHS 2) | 13 | Junior High |
| B9 | Basic 9 (JHS 3) | 14-15 | Junior High |

**High-Stakes Assessment**: BECE (Basic Education Certificate Examination) at end of B9

## Mathematics Curriculum Structure

### Strands (NaCCA Standards-Based Curriculum)

1. **Number** - Counting, operations, fractions, decimals
2. **Algebra** - Patterns, expressions, equations
3. **Geometry & Measurement** - Shapes, spatial reasoning, measurement
4. **Data & Probability** - Data handling, statistics, probability concepts

### Node Code Format

```
B{grade}.{strand}.{sub_strand}.{content_standard}.{indicator}
```

**Example**: `B3.N.PV.CS1.I2`
- B3: Basic 3 (Grade 3)
- N: Number strand
- PV: Place Value sub-strand
- CS1: Content Standard 1
- I2: Indicator 2

## Prerequisite Graph Versions

### v1.0.0 (2024)
- **Initial release**
- 38 core nodes
- Basic prerequisite relationships
- NaCCA B1-B6 mapping
- Source: NEA 2016 data

### v1.1.0 (2025)
- **Added**: 6 cascade paths from EGMA analysis
- **Added**: JHS nodes (B7-B9)
- **Updated**: Prerequisite relationships based on pilot data
- 41 nodes total

### v1.2.0 (March 2026) - CURRENT
- **Added**: Misconception metadata from Abugri & Mereku (2024)
- **Added**: 2 additional nodes (fraction comparison, multi-step word problems)
- **Updated**: Difficulty estimates from Ghana pilot cohorts
- 43 nodes total
- **Status**: Production

## Evidence Base

### National Assessments

1. **Ghana National Education Assessment (NEA) 2016**
   - P3 and P6 math performance data
   - Identified weak areas: place value, fractions, word problems
   - Used for initial difficulty estimates

2. **Early Grade Mathematics Assessment (EGMA) Ghana P2**
   - P2 diagnostic data
   - Item-level analysis for early numeracy nodes
   - Informed cascade path identification

### Research Studies

1. **Abugri & Mereku (2024)** - Place value and fraction misconceptions in Ghana
   - Systematic study of common errors
   - Diagnostic questions validated with 1,200+ students
   - Directly integrated into misconceptions database

2. **Wolf & Aurino (2020)** - Parent engagement RCT in Ghana
   - 2,100+ parent-child pairs
   - Found L1 messaging 2.3x more effective than English
   - Informed language plugin design and messaging strategy

3. **UNESCO MICS Ghana** - Multiple Indicator Cluster Survey
   - Household literacy and education data
   - Regional variations in educational access

4. **World Bank GALOP** - Ghana Accountability for Learning Outcomes Project
   - Teacher training impact data
   - School-level performance patterns

## Cascade Paths

Six research-identified failure patterns:

### 1. Counting → Place Value → Addition/Subtraction
**Root**: Weak counting fluency
**Impact**: Cannot understand place value, struggles with carrying/borrowing
**Prevalence**: 34% of weak performers (EGMA data)

### 2. Place Value → Multiplication → Division
**Root**: Place value misconceptions (treating 24 as "2 and 4" not "twenty-four")
**Impact**: Cannot understand multiplication as repeated addition, division fails
**Prevalence**: 28% of weak performers

### 3. Fractions Concept → Fraction Operations
**Root**: Fractions as separate numerals vs. single number
**Impact**: Incorrectly adds numerators and denominators (1/2 + 1/3 = 2/5)
**Prevalence**: 42% of B5-B6 students (Abugri & Mereku 2024)

### 4. Measurement → Geometry
**Root**: Unit confusion (cm vs m), estimation weakness
**Impact**: Cannot calculate perimeter/area, spatial reasoning fails
**Prevalence**: 19% of weak performers

### 5. Number Sense → Word Problems
**Root**: Cannot translate context to math operation
**Impact**: All word problems become guessing
**Prevalence**: 38% of weak performers

### 6. Basic Operations → Multi-step Problems
**Root**: Fluency gaps in addition/subtraction/multiplication
**Impact**: Cannot sequence multiple operations, cognitive overload
**Prevalence**: 31% of B7-B9 students

## Regional Variations

### Akan Regions (Ashanti, Central, Eastern) - Twi-speaking
- Highest engagement with Twi language plugin
- Urban-rural divide in material access
- Strong cultural grounding with day-name personalization

### Volta Region - Ewe-speaking
- Distinct linguistic/cultural context from Akan
- Requires Ewe language plugin
- Regional variation in EGMA performance

### Greater Accra - Ga-speaking, multilingual
- Urban, high English exposure
- Code-switching common
- More access to materials

### Northern Regions - Dagbani-speaking
- Lower baseline literacy
- Different household materials available
- Stronger preference for L1 messaging

## Usage in GapSense Platform

### 1. Student Onboarding
- Grade selection (B1-B9)
- Language preference (en, tw, ee, ga, dag)
- Initial diagnostic assessment (6-8 questions)

### 2. Diagnostic Engine
- Loads prerequisite graph v1.2.0
- Bayesian inference on node mastery
- Identifies root cause failures via cascade paths

### 3. Intervention Targeting
- Recommends 3-minute parent-child activities
- Targets root nodes (not symptoms)
- Uses language plugin + cultural context for messaging

### 4. Progress Tracking
- Follow-up diagnostic after 3 days
- Measures movement along prerequisite graph
- Adjusts recommendations based on progress

## Data Files

### Primary Directory

**Prerequisite Graphs**:
- `prerequisite_graph_v1.0.json` - 38 nodes (archived)
- `prerequisite_graph_v1.1.json` - 41 nodes (archived)
- `prerequisite_graph_v1.2.json` - 43 nodes (CURRENT)

**Supporting Data** (to be extracted):
- `cascade_paths.json` - 6 cascade path definitions
- `misconceptions.json` - Research-backed misconceptions database
- `evidence_base.json` - Citations and research sources

### Secondary Directory
- **Status**: Not yet implemented
- **Priority**: Low (focus on primary level first)
- **Requirements**: SHS curriculum analysis, WASSCE data integration

## Maintenance Schedule

### Annual Review (March)
- Update difficulty estimates with year's pilot data
- Review for NaCCA curriculum changes
- Increment patch version (e.g., v1.2.0 → v1.2.1)

### Major Updates (As needed)
- When NaCCA releases new curriculum version
- When new national assessment data available (NEA)
- When significant research findings published
- Increment minor or major version

### Validation Metrics
- **Diagnostic accuracy**: % of predicted failures matching actual assessment
- **Intervention effectiveness**: Improvement rate after targeted activities
- **Parent engagement**: Completion rates for recommended activities
- **Cultural relevance**: Parent feedback on messaging appropriateness

## Integration with Other Data

### Language Plugins (`/languages/ghana/`)
- English (en)
- Twi (tw) - 44% speakers
- Ewe (ee) - 13% speakers
- Ga (gaa) - 8% speakers
- Dagbani (dag) - 4% speakers

### Cultural Context (`/cultural_context/ghana.json`)
- Common names (Akan day-names)
- Household materials (toa atifi, aboɔ, dua)
- Local foods and contexts
- Time references (best activity times)

### Platform Code (`/gapsense-platform/`)
- Diagnostic engine loads prerequisite graph
- Prompt generator uses language + cultural context
- WhatsApp integration sends messages via Turn.io

## Research Questions

Ongoing investigation areas:

1. **Cascade Path Validation**
   - Do interventions at root nodes improve downstream performance?
   - Can we predict cascade path membership from initial diagnostic?

2. **Regional Variations**
   - Are prerequisite relationships consistent across regions?
   - Do Akan vs Ewe vs Ga regions show different patterns?

3. **Grade Progression**
   - How do students move through the prerequisite graph over time?
   - What's the typical mastery trajectory?

4. **Parent Engagement Moderators**
   - Which factors predict completion (language, literacy, region)?
   - Optimal messaging frequency and timing?

## Contributing

### Adding New Nodes
1. Identify curriculum gap
2. Define prerequisite relationships
3. Create diagnostic questions
4. Estimate difficulty from pilot data
5. Update prerequisite graph
6. Increment minor version

### Updating Cascade Paths
1. Analyze cohort data for co-failure patterns
2. Validate with teacher interviews
3. Test interventions at root nodes
4. Update cascade_paths.json
5. Document in evidence_base.json

### Reporting Issues
- Incorrect prerequisite relationships
- Outdated difficulty estimates
- Missing NaCCA standards
- Cultural appropriateness concerns

Contact: ghana@gapsense.app

## Related Files

- `/languages/ghana/` - Language-specific messaging
- `/cultural_context/ghana.json` - Cultural grounding
- `/docs/prerequisite_graph_spec.md` - Technical graph specification
- `/docs/noacca_standards_mapping.md` - Full NaCCA curriculum mapping

## Status

- **Version**: v1.2.0
- **Last Updated**: March 2026
- **Status**: Production (active pilot cohorts)
- **Next Review**: March 2027
- **Coverage**: B1-B9 mathematics (primary focus: B1-B6)
