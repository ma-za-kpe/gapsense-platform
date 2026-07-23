-- ============================================================================
-- GAPSENSE DATA MODEL v1.0
-- PostgreSQL Schema for AI-Powered Foundational Learning Diagnostic Platform
-- 
-- Author: Maku Mazakpe
-- Date: 2026-02-13
-- License: Proprietary IP — Licensed to ViztaEdu under GapSense Partnership
--
-- This schema supports:
--   1. NaCCA Curriculum Prerequisite Graph (nodes, edges, misconceptions)
--   2. Student diagnostic sessions and gap profiles
--   3. Parent engagement via WhatsApp (Wolf/Aurino dignity-first model)
--   4. Teacher/school administration
--   5. AI prompt versioning and quality tracking
--   6. Analytics and reporting
--
-- Designed for: AWS RDS PostgreSQL 16+
-- ORM Target: SQLAlchemy 2.0+ (FastAPI backend)
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search on curriculum


-- ============================================================================
-- SECTION 1: CURRICULUM GRAPH
-- The NaCCA prerequisite mapping — GapSense's core IP
-- ============================================================================

CREATE TABLE curriculum_strands (
    id              SERIAL PRIMARY KEY,
    strand_number   SMALLINT NOT NULL UNIQUE,  -- 1=Number, 2=Algebra, 3=Geometry, 4=Data
    name            VARCHAR(100) NOT NULL,
    color_hex       CHAR(7),                    -- For UI rendering
    description     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE curriculum_sub_strands (
    id              SERIAL PRIMARY KEY,
    strand_id       INT NOT NULL REFERENCES curriculum_strands(id),
    sub_strand_number SMALLINT NOT NULL,        -- e.g., 1, 2, 3 within strand
    phase           VARCHAR(10) NOT NULL,        -- 'B1_B3', 'B4_B6', 'B7_B9'
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (strand_id, sub_strand_number, phase)
);

CREATE TABLE curriculum_nodes (
    -- The core of the prerequisite graph
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    code            VARCHAR(20) NOT NULL UNIQUE, -- e.g., 'B2.1.1.1'
    grade           VARCHAR(5) NOT NULL,          -- 'B1' through 'B9'
    strand_id       INT NOT NULL REFERENCES curriculum_strands(id),
    sub_strand_id   INT NOT NULL REFERENCES curriculum_sub_strands(id),
    content_standard_number SMALLINT NOT NULL,
    
    title           VARCHAR(300) NOT NULL,        -- Human-readable title
    description     TEXT NOT NULL,                 -- Full description of what mastery looks like
    
    severity        SMALLINT NOT NULL CHECK (severity BETWEEN 1 AND 5),
    severity_rationale TEXT,                       -- Why this severity rating
    
    -- Diagnostic configuration
    questions_required SMALLINT DEFAULT 2,         -- Min questions to confirm mastery/gap
    confidence_threshold DECIMAL(3,2) DEFAULT 0.80,
    
    -- Ghana-specific evidence
    ghana_evidence  TEXT,                          -- EGMA/NEA data, research citations
    
    -- Status tracking
    population_status VARCHAR(20) DEFAULT 'skeleton' 
        CHECK (population_status IN ('skeleton', 'partial', 'full', 'validated')),
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_curriculum_nodes_grade ON curriculum_nodes(grade);
CREATE INDEX idx_curriculum_nodes_severity ON curriculum_nodes(severity DESC);
CREATE INDEX idx_curriculum_nodes_code ON curriculum_nodes(code);

CREATE TABLE curriculum_prerequisites (
    -- Directed edges in the prerequisite graph
    id              SERIAL PRIMARY KEY,
    source_node_id  UUID NOT NULL REFERENCES curriculum_nodes(id) ON DELETE CASCADE,
    target_node_id  UUID NOT NULL REFERENCES curriculum_nodes(id) ON DELETE CASCADE,
    relationship    VARCHAR(20) DEFAULT 'requires'  -- 'requires', 'strengthens', 'enables'
        CHECK (relationship IN ('requires', 'strengthens', 'enables')),
    weight          DECIMAL(3,2) DEFAULT 1.0,       -- Edge weight for path analysis
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source_node_id, target_node_id),
    CHECK (source_node_id != target_node_id)        -- No self-loops
);

CREATE INDEX idx_prerequisites_source ON curriculum_prerequisites(source_node_id);
CREATE INDEX idx_prerequisites_target ON curriculum_prerequisites(target_node_id);

CREATE TABLE curriculum_indicators (
    -- Learning indicators within each content standard
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    node_id         UUID NOT NULL REFERENCES curriculum_nodes(id) ON DELETE CASCADE,
    indicator_code  VARCHAR(25) NOT NULL UNIQUE,   -- e.g., 'B1.1.1.1.1'
    title           VARCHAR(300) NOT NULL,
    
    -- Diagnostic integration
    diagnostic_question_type VARCHAR(30),           -- 'oral_counting', 'computation', 'word_problem', etc.
    diagnostic_prompt_example TEXT,                  -- Example diagnostic question
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE indicator_error_patterns (
    -- What specific errors reveal about gaps at each indicator
    id              SERIAL PRIMARY KEY,
    indicator_id    UUID NOT NULL REFERENCES curriculum_indicators(id) ON DELETE CASCADE,
    error_description TEXT NOT NULL,
    severity        VARCHAR(10) DEFAULT 'standard'  -- 'critical', 'standard', 'minor'
        CHECK (severity IN ('critical', 'standard', 'minor')),
    indicates_gap_at UUID REFERENCES curriculum_nodes(id), -- Which node this error points to
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE curriculum_misconceptions (
    -- Common misconceptions at each curriculum node
    id              VARCHAR(30) PRIMARY KEY,         -- e.g., 'MC-B2.1.1.1-01'
    node_id         UUID NOT NULL REFERENCES curriculum_nodes(id) ON DELETE CASCADE,
    description     TEXT NOT NULL,                    -- What the misconception IS
    evidence        TEXT NOT NULL,                    -- How it manifests (observable behavior)
    root_cause      TEXT NOT NULL,                    -- WHY this misconception forms
    remediation_approach TEXT NOT NULL,               -- How to fix it
    frequency_estimate VARCHAR(50),                   -- e.g., '55% of students' if known
    source_citation TEXT,                              -- Research source
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE cascade_paths (
    -- Pre-computed critical failure cascades
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,            -- e.g., 'The Place Value Collapse'
    description     TEXT NOT NULL,
    frequency       VARCHAR(100),                     -- e.g., 'Affects ~55% of students'
    diagnostic_entry_point UUID REFERENCES curriculum_nodes(id),
    diagnostic_entry_question TEXT,
    remediation_priority VARCHAR(20),                 -- 'HIGHEST', 'HIGH', 'MEDIUM-HIGH', 'MEDIUM'
    node_sequence   UUID[] NOT NULL,                  -- Ordered array of node IDs in the cascade
    created_at      TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================================
-- SECTION 2: SCHOOLS, TEACHERS, STUDENTS, PARENTS
-- ============================================================================

CREATE TABLE regions (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,     -- Ghana's 16 regions
    code            VARCHAR(5) NOT NULL UNIQUE
);

CREATE TABLE districts (
    id              SERIAL PRIMARY KEY,
    region_id       INT NOT NULL REFERENCES regions(id),
    name            VARCHAR(200) NOT NULL,
    ges_district_code VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (region_id, name)
);

CREATE TABLE schools (
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name            VARCHAR(300) NOT NULL,
    district_id     INT NOT NULL REFERENCES districts(id),
    school_type     VARCHAR(20) DEFAULT 'primary'
        CHECK (school_type IN ('primary', 'jhs', 'combined', 'private')),
    ges_school_code VARCHAR(30),
    
    -- Contact
    phone           VARCHAR(20),
    location_lat    DECIMAL(10,7),
    location_lng    DECIMAL(10,7),
    
    -- Metadata
    total_enrollment INT,
    language_of_instruction VARCHAR(30) DEFAULT 'English',  -- Primary LOI
    dominant_l1     VARCHAR(30),                              -- Most common mother tongue
    
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE teachers (
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    school_id       UUID NOT NULL REFERENCES schools(id),
    
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    phone           VARCHAR(20) NOT NULL,              -- WhatsApp number
    phone_verified  BOOLEAN DEFAULT FALSE,
    
    grade_taught    VARCHAR(5),                         -- Current grade (B1-B9)
    subjects        VARCHAR(100)[],                     -- Array of subjects
    
    -- GapSense engagement
    onboarded_at    TIMESTAMPTZ,
    last_active_at  TIMESTAMPTZ,
    total_students_diagnosed INT DEFAULT 0,
    
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE parents (
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- Minimal required info (dignity-first: don't ask for more than needed)
    phone           VARCHAR(20) NOT NULL UNIQUE,       -- WhatsApp number (primary identifier)
    phone_verified  BOOLEAN DEFAULT FALSE,
    preferred_name  VARCHAR(100),                       -- How they want to be addressed
    
    -- Language (critical for engagement)
    preferred_language VARCHAR(30) DEFAULT 'en',        -- ISO code or 'tw', 'ee', 'ga', 'dag'
    literacy_level  VARCHAR(20),                         -- 'literate', 'semi_literate', 'non_literate'
        -- Determines message complexity; NEVER shared externally
    
    -- Location
    district_id     INT REFERENCES districts(id),
    community       VARCHAR(200),
    
    -- Engagement tracking
    onboarded_at    TIMESTAMPTZ,
    last_interaction_at TIMESTAMPTZ,
    total_interactions INT DEFAULT 0,
    engagement_score DECIMAL(4,2),                       -- Rolling engagement metric
    
    -- Wolf/Aurino compliance
    opted_in        BOOLEAN DEFAULT FALSE,              -- Explicit WhatsApp opt-in
    opted_in_at     TIMESTAMPTZ,
    opted_out       BOOLEAN DEFAULT FALSE,
    opted_out_at    TIMESTAMPTZ,
    
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_parents_phone ON parents(phone);

CREATE TABLE students (
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- Identity (minimal, dignity-first)
    first_name      VARCHAR(100) NOT NULL,
    -- No last name required (some parents may not want to share)
    age             SMALLINT,                            -- Approximate age
    gender          VARCHAR(10) CHECK (gender IN ('male', 'female', 'other', NULL)),
    
    -- Academic context
    school_id       UUID REFERENCES schools(id),
    current_grade   VARCHAR(5) NOT NULL,                 -- B1-B9
    grade_as_of     DATE DEFAULT CURRENT_DATE,           -- When this grade was recorded
    teacher_id      UUID REFERENCES teachers(id),
    
    -- Parent linkage
    primary_parent_id UUID NOT NULL REFERENCES parents(id),
    secondary_parent_id UUID REFERENCES parents(id),
    
    -- Language context (critical for diagnosis)
    home_language   VARCHAR(30),                          -- L1 spoken at home
    school_language VARCHAR(30) DEFAULT 'English',        -- LOI at school
    
    -- Diagnostic state
    latest_gap_profile_id UUID,                          -- FK added after gap_profiles table
    diagnosis_count INT DEFAULT 0,
    first_diagnosed_at TIMESTAMPTZ,
    last_diagnosed_at TIMESTAMPTZ,
    
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_students_parent ON students(primary_parent_id);
CREATE INDEX idx_students_school ON students(school_id);
CREATE INDEX idx_students_grade ON students(current_grade);


-- ============================================================================
-- SECTION 3: DIAGNOSTIC ENGINE
-- ============================================================================

CREATE TABLE diagnostic_sessions (
    -- Each time a student is assessed
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    student_id      UUID NOT NULL REFERENCES students(id),
    
    -- Session context
    initiated_by    VARCHAR(20) NOT NULL                  -- 'parent', 'teacher', 'system'
        CHECK (initiated_by IN ('parent', 'teacher', 'system', 'self')),
    channel         VARCHAR(20) DEFAULT 'whatsapp'
        CHECK (channel IN ('whatsapp', 'web', 'app', 'sms', 'paper')),
    
    -- Session state
    status          VARCHAR(20) DEFAULT 'in_progress'
        CHECK (status IN ('in_progress', 'completed', 'abandoned', 'timed_out')),
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    
    -- Entry point
    entry_grade     VARCHAR(5) NOT NULL,                  -- Grade level started at
    entry_node_id   UUID REFERENCES curriculum_nodes(id), -- First node tested
    
    -- Results
    total_questions INT DEFAULT 0,
    correct_answers INT DEFAULT 0,
    nodes_tested    UUID[] DEFAULT '{}',                   -- Array of tested node IDs
    nodes_mastered  UUID[] DEFAULT '{}',
    nodes_gap       UUID[] DEFAULT '{}',
    
    -- Root cause identified
    root_gap_node_id UUID REFERENCES curriculum_nodes(id),
    root_gap_confidence DECIMAL(3,2),                     -- 0.0-1.0
    cascade_path_id INT REFERENCES cascade_paths(id),     -- Which cascade pattern matched
    
    -- AI metadata
    prompt_version_id UUID,                                -- FK to prompt_versions
    model_used      VARCHAR(50),                           -- e.g., 'claude-sonnet-4-5'
    total_tokens    INT,
    ai_reasoning_log JSONB,                                -- Full chain-of-thought (encrypted at rest)
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_student ON diagnostic_sessions(student_id);
CREATE INDEX idx_sessions_status ON diagnostic_sessions(status);
CREATE INDEX idx_sessions_root_gap ON diagnostic_sessions(root_gap_node_id);

CREATE TABLE diagnostic_questions (
    -- Individual questions within a session
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id      UUID NOT NULL REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
    
    -- Question context
    question_order  SMALLINT NOT NULL,                    -- Order within session
    node_id         UUID NOT NULL REFERENCES curriculum_nodes(id),
    indicator_id    UUID REFERENCES curriculum_indicators(id),
    
    -- Question content
    question_text   TEXT NOT NULL,                         -- The actual question asked
    question_type   VARCHAR(30) NOT NULL,                  -- 'multiple_choice', 'free_response', 'image', 'voice'
    question_media_url TEXT,                               -- Image/audio if applicable
    expected_answer TEXT,
    
    -- Response
    student_response TEXT,
    response_media_url TEXT,                               -- Photo of exercise book, voice note
    is_correct      BOOLEAN,
    response_time_seconds INT,                             -- How long student took
    
    -- AI analysis
    error_pattern_detected VARCHAR(100),                   -- Which error pattern matched
    misconception_id VARCHAR(30) REFERENCES curriculum_misconceptions(id),
    ai_analysis     JSONB,                                 -- Detailed AI reasoning about the response
    
    asked_at        TIMESTAMPTZ DEFAULT NOW(),
    answered_at     TIMESTAMPTZ
);

CREATE INDEX idx_questions_session ON diagnostic_questions(session_id);
CREATE INDEX idx_questions_node ON diagnostic_questions(node_id);

CREATE TABLE gap_profiles (
    -- A student's current learning gap profile (updated after each session)
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    student_id      UUID NOT NULL REFERENCES students(id),
    session_id      UUID NOT NULL REFERENCES diagnostic_sessions(id),
    
    -- Gap summary
    mastered_nodes  UUID[] NOT NULL DEFAULT '{}',         -- Nodes confirmed mastered
    gap_nodes       UUID[] NOT NULL DEFAULT '{}',         -- Nodes with confirmed gaps
    uncertain_nodes UUID[] NOT NULL DEFAULT '{}',         -- Need more data
    
    -- Root cause analysis
    primary_gap_node UUID REFERENCES curriculum_nodes(id),  -- The deepest root gap
    primary_cascade VARCHAR(100),                            -- Which cascade path
    secondary_gaps  UUID[] DEFAULT '{}',                     -- Additional gap roots
    
    -- Actionable output
    recommended_focus_node UUID REFERENCES curriculum_nodes(id), -- What to work on FIRST
    recommended_activity TEXT,                                    -- Specific activity for parent
    estimated_grade_level VARCHAR(5),                             -- Functional grade level
    grade_gap       SMALLINT,                                    -- Difference from enrolled grade
    
    -- Confidence
    overall_confidence DECIMAL(3,2),                       -- How confident we are in this profile
    
    is_current      BOOLEAN DEFAULT TRUE,                  -- Only one current profile per student
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gap_profiles_student ON gap_profiles(student_id);
CREATE INDEX idx_gap_profiles_current ON gap_profiles(student_id) WHERE is_current = TRUE;

-- Add FK from students to gap_profiles
ALTER TABLE students ADD CONSTRAINT fk_latest_gap_profile 
    FOREIGN KEY (latest_gap_profile_id) REFERENCES gap_profiles(id);


-- ============================================================================
-- SECTION 4: PARENT ENGAGEMENT (WhatsApp)
-- Wolf/Aurino evidence-based design
-- ============================================================================

CREATE TABLE parent_interactions (
    -- Every WhatsApp message exchange
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    parent_id       UUID NOT NULL REFERENCES parents(id),
    student_id      UUID REFERENCES students(id),
    
    -- Message metadata
    direction       VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    channel         VARCHAR(20) DEFAULT 'whatsapp',
    wa_message_id   VARCHAR(100),                          -- WhatsApp message ID for tracking
    
    -- Content
    message_type    VARCHAR(20) NOT NULL,                   -- 'text', 'image', 'voice', 'button', 'list', 'template'
    interaction_purpose VARCHAR(30) NOT NULL,               -- 'diagnostic', 'activity', 'check_in', 'onboarding', 'feedback', 'reminder'
    
    message_content TEXT,                                   -- Actual message text (encrypted at rest)
    media_url       TEXT,                                   -- Media attachment URL
    template_name   VARCHAR(100),                           -- WhatsApp template name if applicable
    
    -- Language
    language_used   VARCHAR(30),                            -- Language this message was in
    
    -- AI processing
    ai_generated    BOOLEAN DEFAULT FALSE,
    prompt_version_id UUID,
    sentiment_score DECIMAL(3,2),                           -- -1.0 to 1.0
    
    -- Status
    delivery_status VARCHAR(20) DEFAULT 'sent'
        CHECK (delivery_status IN ('queued', 'sent', 'delivered', 'read', 'failed')),
    
    sent_at         TIMESTAMPTZ DEFAULT NOW(),
    delivered_at    TIMESTAMPTZ,
    read_at         TIMESTAMPTZ
);

CREATE INDEX idx_interactions_parent ON parent_interactions(parent_id);
CREATE INDEX idx_interactions_student ON parent_interactions(student_id);
CREATE INDEX idx_interactions_purpose ON parent_interactions(interaction_purpose);

CREATE TABLE parent_activities (
    -- Specific learning activities sent to parents
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    parent_id       UUID NOT NULL REFERENCES parents(id),
    student_id      UUID NOT NULL REFERENCES students(id),
    gap_profile_id  UUID REFERENCES gap_profiles(id),
    
    -- Activity details
    focus_node_id   UUID NOT NULL REFERENCES curriculum_nodes(id),
    activity_title  VARCHAR(200) NOT NULL,
    activity_description TEXT NOT NULL,                      -- The 3-minute activity
    materials_needed TEXT,                                   -- What parent needs (bottle caps, paper, etc.)
    estimated_minutes SMALLINT DEFAULT 3,
    
    -- Language
    language        VARCHAR(30) NOT NULL,
    
    -- Tracking
    sent_at         TIMESTAMPTZ DEFAULT NOW(),
    started_at      TIMESTAMPTZ,                            -- Parent confirmed they started
    completed_at    TIMESTAMPTZ,                            -- Parent confirmed completion
    parent_feedback TEXT,                                    -- Optional feedback from parent
    
    -- Effectiveness
    follow_up_session_id UUID REFERENCES diagnostic_sessions(id),
    skill_improved  BOOLEAN                                 -- Did follow-up show improvement?
);

CREATE INDEX idx_activities_parent ON parent_activities(parent_id);
CREATE INDEX idx_activities_node ON parent_activities(focus_node_id);


-- ============================================================================
-- SECTION 5: AI PROMPT VERSIONING
-- Proprietary IP — prompt engineering is GapSense's defensible moat
-- ============================================================================

CREATE TABLE prompt_categories (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(50) NOT NULL UNIQUE,           -- 'diagnostic', 'parent_engagement', 'teacher', 'analysis'
    description     TEXT
);

CREATE TABLE prompt_versions (
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    category_id     INT NOT NULL REFERENCES prompt_categories(id),
    
    -- Version tracking
    version         VARCHAR(20) NOT NULL,                   -- Semantic versioning: '1.0.0'
    name            VARCHAR(200) NOT NULL,                  -- e.g., 'Diagnostic Reasoning Prompt v2'
    
    -- Prompt content
    system_prompt   TEXT NOT NULL,                           -- The actual system prompt
    user_template   TEXT,                                    -- Template for user messages (with {{placeholders}})
    output_schema   JSONB,                                   -- Expected output format
    
    -- Configuration
    model_target    VARCHAR(50) DEFAULT 'claude-sonnet-4-5', -- Which model this is optimized for
    temperature     DECIMAL(3,2) DEFAULT 0.3,
    max_tokens      INT DEFAULT 2048,
    
    -- Quality tracking
    test_cases_passed INT DEFAULT 0,
    test_cases_total INT DEFAULT 0,
    accuracy_score  DECIMAL(4,2),                            -- % accuracy on test cases
    
    -- Lifecycle
    status          VARCHAR(20) DEFAULT 'draft'
        CHECK (status IN ('draft', 'testing', 'active', 'deprecated')),
    activated_at    TIMESTAMPTZ,
    deprecated_at   TIMESTAMPTZ,
    deprecated_reason TEXT,
    
    -- Metadata
    created_by      VARCHAR(100),
    changelog       TEXT,
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (category_id, version)
);

CREATE INDEX idx_prompt_versions_active ON prompt_versions(category_id) WHERE status = 'active';

CREATE TABLE prompt_test_cases (
    -- Test scenarios for validating prompts
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    prompt_version_id UUID NOT NULL REFERENCES prompt_versions(id) ON DELETE CASCADE,
    
    -- Test input
    test_name       VARCHAR(200) NOT NULL,
    test_input      JSONB NOT NULL,                          -- Simulated input data
    expected_output JSONB NOT NULL,                           -- What the prompt should produce
    
    -- Test results
    actual_output   JSONB,
    passed          BOOLEAN,
    notes           TEXT,
    
    last_run_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================================
-- SECTION 6: ANALYTICS & REPORTING
-- ============================================================================

CREATE TABLE school_analytics (
    -- Aggregated analytics per school (updated periodically)
    id              SERIAL PRIMARY KEY,
    school_id       UUID NOT NULL REFERENCES schools(id),
    period          DATE NOT NULL,                           -- Month start date
    
    total_students_diagnosed INT DEFAULT 0,
    total_sessions  INT DEFAULT 0,
    
    -- Gap distribution
    top_gap_node_1  UUID REFERENCES curriculum_nodes(id),
    top_gap_node_1_count INT,
    top_gap_node_2  UUID REFERENCES curriculum_nodes(id),
    top_gap_node_2_count INT,
    top_gap_node_3  UUID REFERENCES curriculum_nodes(id),
    top_gap_node_3_count INT,
    
    -- Cascade distribution
    pct_place_value_cascade DECIMAL(5,2),
    pct_fraction_cascade DECIMAL(5,2),
    pct_subtraction_cascade DECIMAL(5,2),
    pct_multiplicative_cascade DECIMAL(5,2),
    
    -- Engagement
    avg_parent_engagement_score DECIMAL(4,2),
    pct_activities_completed DECIMAL(5,2),
    pct_skills_improved DECIMAL(5,2),
    
    -- Grade level
    avg_grade_gap   DECIMAL(3,1),                            -- Average gap between enrolled and functional grade
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (school_id, period)
);

CREATE TABLE district_analytics (
    id              SERIAL PRIMARY KEY,
    district_id     INT NOT NULL REFERENCES districts(id),
    period          DATE NOT NULL,
    
    total_schools_active INT DEFAULT 0,
    total_students_diagnosed INT DEFAULT 0,
    avg_grade_gap   DECIMAL(3,1),
    
    top_gap_nodes   UUID[],                                  -- Most common gaps across district
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (district_id, period)
);


-- ============================================================================
-- SECTION 7: SYSTEM & AUDIT
-- ============================================================================

CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    entity_type     VARCHAR(50) NOT NULL,                    -- Table name
    entity_id       VARCHAR(100) NOT NULL,                   -- Record ID
    action          VARCHAR(20) NOT NULL,                    -- 'create', 'update', 'delete'
    changed_by      VARCHAR(100),                            -- User or system
    old_values      JSONB,
    new_values      JSONB,
    ip_address      INET,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_created ON audit_log(created_at);

CREATE TABLE system_config (
    key             VARCHAR(100) PRIMARY KEY,
    value           JSONB NOT NULL,
    description     TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_by      VARCHAR(100)
);

-- Insert default system config
INSERT INTO system_config (key, value, description) VALUES
('diagnostic.max_trace_depth', '4', 'Maximum grade levels to trace backward during diagnosis'),
('diagnostic.min_confidence', '0.80', 'Minimum confidence threshold to confirm a gap'),
('diagnostic.questions_per_node', '2', 'Default questions per node (min 2 to confirm)'),
('engagement.reminder_interval_days', '3', 'Days between parent check-in reminders'),
('engagement.max_messages_per_day', '3', 'Maximum outbound messages per parent per day'),
('engagement.cool_off_after_opt_out_days', '30', 'Wait period before re-engagement attempt'),
('wolf_aurino.never_generic_messages', 'true', 'NEVER send generic "your child is behind" messages'),
('wolf_aurino.strength_first_framing', 'true', 'Always lead with what the child CAN do'),
('wolf_aurino.single_focus_activity', 'true', 'Only recommend ONE activity per interaction');


-- ============================================================================
-- SEED DATA: Curriculum strands
-- ============================================================================

INSERT INTO curriculum_strands (strand_number, name, color_hex, description) VALUES
(1, 'Number', '#2563EB', 'Counting, representation, cardinality, operations, fractions, decimals, percentages'),
(2, 'Algebra', '#7C3AED', 'Patterns, relationships, functions, expressions, equations, inequalities'),
(3, 'Geometry and Measurement', '#059669', 'Lines, shapes, position, transformation, measurements, geometrical reasoning'),
(4, 'Data', '#D97706', 'Collection, presentation, analysis, interpretation, probability');


-- ============================================================================
-- SEED DATA: Priority screening nodes (the 6 root-cause nodes)
-- ============================================================================

INSERT INTO system_config (key, value, description) VALUES
('diagnostic.priority_screening_nodes', 
 '["B2.1.1.1", "B1.1.2.2", "B2.1.2.2", "B2.1.3.1", "B3.1.3.1", "B4.1.3.1"]',
 'These 6 nodes sit at the roots of the 4 critical cascade paths. Test FIRST for any child regardless of grade.');


-- ============================================================================
-- VIEWS for common queries
-- ============================================================================

-- View: Student's current gap profile with human-readable info
CREATE VIEW v_student_gap_summary AS
SELECT 
    s.id AS student_id,
    s.first_name,
    s.current_grade,
    s.home_language,
    p.phone AS parent_phone,
    p.preferred_language,
    gp.estimated_grade_level,
    gp.grade_gap,
    gp.overall_confidence,
    cn.code AS primary_gap_code,
    cn.title AS primary_gap_title,
    cn.severity AS primary_gap_severity,
    rfn.code AS recommended_focus_code,
    rfn.title AS recommended_focus_title,
    gp.recommended_activity,
    gp.created_at AS last_diagnosed_at
FROM students s
JOIN parents p ON s.primary_parent_id = p.id
LEFT JOIN gap_profiles gp ON s.latest_gap_profile_id = gp.id
LEFT JOIN curriculum_nodes cn ON gp.primary_gap_node = cn.id
LEFT JOIN curriculum_nodes rfn ON gp.recommended_focus_node = rfn.id
WHERE s.is_active = TRUE;

-- View: School-level gap distribution
CREATE VIEW v_school_gap_distribution AS
SELECT 
    sc.id AS school_id,
    sc.name AS school_name,
    s.current_grade,
    cn.code AS gap_code,
    cn.title AS gap_title,
    cn.severity,
    COUNT(*) AS student_count
FROM students s
JOIN schools sc ON s.school_id = sc.id
JOIN gap_profiles gp ON s.latest_gap_profile_id = gp.id
JOIN curriculum_nodes cn ON gp.primary_gap_node = cn.id
WHERE s.is_active = TRUE AND gp.is_current = TRUE
GROUP BY sc.id, sc.name, s.current_grade, cn.code, cn.title, cn.severity
ORDER BY sc.name, s.current_grade, student_count DESC;


-- ============================================================================
-- COMMENTS for Claude Code / documentation
-- ============================================================================

COMMENT ON TABLE curriculum_nodes IS 'Core of the GapSense prerequisite graph. Each node represents a NaCCA content standard with diagnostic metadata. PROPRIETARY IP.';
COMMENT ON TABLE curriculum_prerequisites IS 'Directed edges in the prerequisite graph. source_node_id REQUIRES target_node_id to be mastered first.';
COMMENT ON TABLE curriculum_misconceptions IS 'Research-backed misconceptions at each curriculum node. Links error patterns to root causes and remediation. PROPRIETARY IP.';
COMMENT ON TABLE diagnostic_sessions IS 'Each assessment session. Tracks the adaptive diagnostic journey from entry point to root cause identification.';
COMMENT ON TABLE gap_profiles IS 'A student learning gap profile generated after diagnosis. Only one is_current=TRUE per student at any time.';
COMMENT ON TABLE parent_interactions IS 'All WhatsApp message exchanges. Wolf/Aurino compliant: never generic, always specific, always dignity-preserving.';
COMMENT ON TABLE prompt_versions IS 'AI prompt engineering version control. PROPRIETARY IP. Each prompt is tested against test_cases before activation.';
COMMENT ON COLUMN parents.literacy_level IS 'SENSITIVE: Used only to calibrate message complexity. NEVER shared with schools, teachers, or reports.';
COMMENT ON COLUMN diagnostic_sessions.ai_reasoning_log IS 'Full AI chain-of-thought for the diagnostic session. Encrypted at rest. Used for quality assurance and prompt improvement.';
