# Requirements Document

## Introduction

The GapSense platform must be upgraded to consume the massively expanded gapsense-data layer (v2.0 multi-country prompt library, multi-country curricula, cultural context files, L1 language files). The current platform code has hardcoded paths to v1.1 data structures, a synchronous AI client, a single-country database schema, and only 2 of 13 prompts wired into code. This spec covers the foundational service upgrades needed to unblock all five MVP features: Exercise Book Scanner, Teacher Conversation Partner, Parent Voice Notes, Voice Micro-Coaching, and GUARD-001 Compliance Gate.

## Glossary

- **AI_Client**: The async service that sends requests to Anthropic Claude (primary) and xAI Grok (fallback) APIs with retry, timeout, JSON mode, and multimodal support
- **Prompt_Service**: The service that loads v2.0 multi-country prompts, resolves country_config parameters, injects cultural context, and renders prompt templates
- **Curriculum_Loader**: The service that ingests multi-country, multi-subject, multi-level curriculum JSON files from the `curricula/{country}/{level}/{subject}/` directory structure into the database
- **Country_Config**: The JSON configuration for a supported country containing curriculum authority, grade structure, currency, languages, and cultural context
- **Cultural_Context**: The JSON file containing country-specific names, foods, household materials, time references, and cultural norms used to parameterize prompts
- **L1_Language_File**: The JSON file containing greetings, encouragement phrases, math vocabulary, materials, and action verbs in a local language (e.g., Twi, Ewe, Luganda)
- **Guard_Service**: The compliance gate that validates all outbound parent-facing messages against Wolf/Aurino dignity-first principles using the GUARD-001 prompt
- **Media_Service**: The service that handles S3 upload/download of images (exercise book photos) and audio (voice notes) with presigned URLs
- **Worker_Service**: The background SQS consumer that processes async tasks such as TTS generation, image analysis, and scheduled message delivery
- **Flow_Executor**: The core WhatsApp conversation orchestrator that routes inbound messages through onboarding, diagnostics, and engagement flows
- **CurriculumNode**: The database model representing a single learning objective in the prerequisite graph
- **GapProfile**: The database model representing a student's diagnosed learning gaps, linked to diagnostic sessions or other gap sources
- **TTS_Service**: The text-to-speech service that converts activity messages into voice notes in L1 languages
- **STT_Service**: The speech-to-text service that transcribes parent voice replies using Whisper
- **Prompt_Template**: A v2.0 prompt containing `{{country}}`, `{{curriculum_authority}}`, `{{common_foods}}`, and other parameterized placeholders

## Requirements

### Requirement 1: Async AI Client with Retry and Multimodal Support

**User Story:** As a platform developer, I want an async AI client with connection pooling, retry logic, JSON mode, and multimodal (image) support, so that all downstream services can make reliable, non-blocking AI calls.

#### Acceptance Criteria

1. THE AI_Client SHALL use a single shared AsyncAnthropic client instance with connection pooling instead of creating a new client on every call
2. WHEN the AI_Client sends a request to Anthropic, THE AI_Client SHALL use async/await for all API calls
3. WHEN an Anthropic API call fails with a transient error (429, 500, 502, 503, 529), THE AI_Client SHALL retry the request up to 3 times with exponential backoff starting at 1 second
4. WHEN an Anthropic API call does not respond within 30 seconds, THE AI_Client SHALL cancel the request and return a timeout error
5. WHEN the caller requests JSON mode, THE AI_Client SHALL pass the appropriate response_format parameter to the Anthropic API so that the response is valid JSON
6. WHEN the caller provides image content (base64 or URL), THE AI_Client SHALL include the image in the message content array as an image content block for Claude Vision multimodal analysis
7. WHEN the primary Anthropic provider fails after all retries, THE AI_Client SHALL fall back to the Grok provider using the same async pattern
8. WHEN all providers fail, THE AI_Client SHALL return None to signal that rule-based fallback logic should be used
9. THE AI_Client SHALL enforce a configurable concurrency limit (default 10) on simultaneous API requests using an asyncio semaphore
10. THE AI_Client SHALL log the provider used, prompt_id, latency in milliseconds, token usage, and success/failure status for every API call

### Requirement 2: Multi-Country Prompt Service with Template Resolution

**User Story:** As a platform developer, I want a prompt service that loads v2.0 multi-country prompts and resolves country-specific parameters, so that all 13 prompts can generate culturally appropriate output for Ghana, Uganda, Kenya, and Nigeria.

#### Acceptance Criteria

1. THE Prompt_Service SHALL load prompts from the v2.0 multi-country prompt library file at `prompts/gapsense_prompt_library_v2.0_multicountry.json`
2. THE Prompt_Service SHALL load Country_Config from `country_config` section of the prompt library and from `curricula/{country}/country_config.json`
3. THE Prompt_Service SHALL load Cultural_Context from `cultural_context/{country}.json` for each supported country
4. THE Prompt_Service SHALL load L1_Language_File from `languages/{country}/{language}.json` for each supported language
5. WHEN a prompt is requested with a country parameter, THE Prompt_Service SHALL substitute all `{{country}}`, `{{curriculum_authority}}`, `{{common_foods}}`, `{{common_names}}`, `{{household_materials}}`, `{{currency}}`, and `{{geographic_contexts}}` placeholders with values from the corresponding Country_Config
6. WHEN a prompt is requested with a language parameter, THE Prompt_Service SHALL inject L1 greetings, encouragement phrases, math vocabulary, and material names from the corresponding L1_Language_File into the prompt context
7. IF a requested country is not found in the supported countries list, THEN THE Prompt_Service SHALL raise a ValueError with the list of supported countries
8. IF a requested language is not supported for the given country, THEN THE Prompt_Service SHALL raise a ValueError with the list of supported languages for that country
9. THE Prompt_Service SHALL provide access to all 13 prompts: DIAG-001, DIAG-002, DIAG-003, PARENT-001, PARENT-002, PARENT-003, ACT-001, TEACHER-001, TEACHER-002, TEACHER-003, ANALYSIS-001, ANALYSIS-002, GUARD-001
10. FOR ALL valid Prompt_Template objects, rendering a template with a Country_Config and then extracting the placeholders SHALL produce a string with zero unresolved `{{...}}` placeholders (round-trip property)

### Requirement 3: Configuration Update for Multi-Country Data Paths

**User Story:** As a platform developer, I want the application configuration to reference the new v2.0 data structures, so that the platform loads curricula from `curricula/` (plural) and prompts from the v2.0 library.

#### Acceptance Criteria

1. THE Settings SHALL provide a `prompt_library_path` property that resolves to `{GAPSENSE_DATA_PATH}/prompts/gapsense_prompt_library_v2.0_multicountry.json`
2. THE Settings SHALL provide a `curricula_base_path` property that resolves to `{GAPSENSE_DATA_PATH}/curricula/`
3. THE Settings SHALL provide a `cultural_context_path` property that resolves to `{GAPSENSE_DATA_PATH}/cultural_context/`
4. THE Settings SHALL provide a `languages_base_path` property that resolves to `{GAPSENSE_DATA_PATH}/languages/`
5. THE Settings validator SHALL check for the existence of `curricula/` (plural) directory instead of `curriculum/` (singular)
6. THE Settings SHALL retain backward compatibility by keeping the `prerequisite_graph_path` property pointing to `curriculum/gapsense_prerequisite_graph_v1.2.json` for existing code that still references it
7. WHEN the `curricula/` directory does not exist at the configured GAPSENSE_DATA_PATH, THE Settings validator SHALL raise a ValueError with a descriptive message

### Requirement 4: Database Schema Migration for Multi-Country Support

**User Story:** As a platform developer, I want the database schema to support multi-country, multi-subject, multi-level curriculum data and multi-source gap profiles, so that the platform can store data from Ghana, Uganda, Kenya, and Nigeria.

#### Acceptance Criteria

1. THE CurriculumNode model SHALL include a `country` column of type String(5) that stores the ISO-style country code (e.g., "GH", "UG", "KE", "NG")
2. THE CurriculumNode model SHALL include a `subject` column of type String(50) that stores the subject name (e.g., "mathematics", "english")
3. THE CurriculumNode model SHALL include a `level` column of type String(20) that stores the education level (e.g., "primary", "secondary")
4. THE CurriculumNode model SHALL have a composite index on (country, subject, level, grade) for efficient multi-country queries
5. THE GapProfile model SHALL make the `session_id` column nullable to allow gap profiles created from sources other than diagnostic sessions
6. THE GapProfile model SHALL include a `source` column of type String(30) that indicates the origin of the gap profile (e.g., "diagnostic", "exercise_book", "teacher_report", "voice_coaching")
7. THE GapProfile model SHALL default the `source` column to "diagnostic" for backward compatibility with existing gap profiles
8. WHEN a GapProfile is created without a session_id, THE GapProfile model SHALL require the `source` column to contain a non-empty value
9. THE database migration SHALL be created as an Alembic migration script that can be applied to existing databases without data loss

### Requirement 5: Multi-Country Curriculum Loader

**User Story:** As a platform developer, I want a curriculum loader that ingests the new multi-country directory structure, so that all 292 nodes across 7 subjects and multiple countries are loaded into the database.

#### Acceptance Criteria

1. THE Curriculum_Loader SHALL discover curriculum files by walking the `curricula/{country}/{level}/{subject}/` directory tree
2. THE Curriculum_Loader SHALL parse object-based JSON files where nodes are keyed by node code (e.g., `{"B2.1.1.1": {...}}`) instead of array-based JSON
3. THE Curriculum_Loader SHALL populate the `country`, `subject`, and `level` columns on each CurriculumNode based on the directory path
4. THE Curriculum_Loader SHALL read the `country_config.json` for each country to determine active levels and active subjects
5. WHEN a curriculum file contains a node code that already exists in the database for the same country, THE Curriculum_Loader SHALL update the existing node instead of creating a duplicate
6. WHEN a curriculum file contains invalid JSON, THE Curriculum_Loader SHALL log the file path and error message and continue loading remaining files
7. THE Curriculum_Loader SHALL report a summary after loading: total files processed, total nodes created, total nodes updated, total errors, broken down by country and subject
8. THE Curriculum_Loader SHALL load prerequisite relationships, misconceptions, indicators, and cascade paths from the curriculum files when present

### Requirement 6: GUARD-001 Compliance Gate

**User Story:** As a platform developer, I want a compliance gate that validates all outbound parent-facing messages against Wolf/Aurino dignity-first principles, so that no message reaches a parent without passing the GUARD-001 check.

#### Acceptance Criteria

1. WHEN an outbound parent-facing message is generated, THE Guard_Service SHALL send the message text, the student context, and the parent language preference to the AI_Client using the GUARD-001 prompt
2. THE Guard_Service SHALL receive a structured response indicating pass/fail and, on failure, a list of specific violations
3. WHEN the GUARD-001 check returns a pass result, THE Guard_Service SHALL return the original message unchanged
4. WHEN the GUARD-001 check returns a fail result, THE Guard_Service SHALL return the violation details and block the message from being sent
5. IF the AI_Client returns None (all providers failed), THEN THE Guard_Service SHALL block the message and log a compliance-check-unavailable event rather than sending an unvalidated message
6. THE Guard_Service SHALL complete the compliance check within 5 seconds for text messages
7. THE Guard_Service SHALL log the prompt_id, pass/fail result, latency, and any violation categories for every compliance check

### Requirement 7: S3 Media Service for Images and Audio

**User Story:** As a platform developer, I want a media service that uploads and downloads images and audio files to/from S3, so that exercise book photos and voice notes can be stored and retrieved.

#### Acceptance Criteria

1. THE Media_Service SHALL upload binary content (images, audio) to the configured S3 bucket with a structured key format: `{country}/{student_id}/{media_type}/{timestamp}_{filename}`
2. THE Media_Service SHALL generate presigned download URLs with a configurable expiry (default 1 hour)
3. THE Media_Service SHALL generate presigned upload URLs for direct client uploads with a configurable expiry (default 15 minutes)
4. WHEN uploading an image, THE Media_Service SHALL validate that the content type is one of: image/jpeg, image/png, image/webp
5. WHEN uploading audio, THE Media_Service SHALL validate that the content type is one of: audio/ogg, audio/mpeg, audio/wav, audio/mp4
6. IF the S3 upload fails, THEN THE Media_Service SHALL retry up to 2 times with exponential backoff and return a descriptive error on final failure
7. THE Media_Service SHALL use the LocalStack S3 endpoint in local/development environments and the real AWS S3 endpoint in staging/production
8. THE Media_Service SHALL enforce a maximum file size of 10 MB for images and 25 MB for audio files

### Requirement 8: Worker Service for Background Processing

**User Story:** As a platform developer, I want a background worker service that consumes SQS messages and processes async tasks, so that TTS generation, image analysis, and scheduled deliveries do not block the web API.

#### Acceptance Criteria

1. THE Worker_Service SHALL implement a long-polling SQS consumer that reads messages from the configured queue URL
2. THE Worker_Service SHALL support task types: `tts_generate`, `image_analyze`, `scheduled_message`, and `voice_transcribe`
3. WHEN a `tts_generate` task is received, THE Worker_Service SHALL invoke the TTS_Service to convert text to speech and upload the result to S3 via the Media_Service
4. WHEN an `image_analyze` task is received, THE Worker_Service SHALL download the image from S3, send it to the AI_Client with the ANALYSIS-001 prompt for multimodal analysis, and store the results
5. WHEN a `scheduled_message` task is received, THE Worker_Service SHALL send the message through the Guard_Service before delivering it via WhatsApp
6. WHEN a `voice_transcribe` task is received, THE Worker_Service SHALL download the audio from S3, transcribe it using the STT_Service, and store the transcript
7. IF a task fails after processing, THEN THE Worker_Service SHALL return the message to the queue with an incremented retry count and exponential backoff visibility timeout
8. WHEN a task has exceeded 3 retry attempts, THE Worker_Service SHALL move the message to a dead-letter queue and log the failure details
9. THE Worker_Service SHALL process tasks concurrently up to a configurable limit (default 5) using asyncio

### Requirement 9: Exercise Book Scanner Integration

**User Story:** As a teacher, I want to photograph student exercise books and receive AI analysis of error patterns traced to foundational gaps, so that I can understand where each student's understanding breaks down.

#### Acceptance Criteria

1. WHEN a teacher sends an image via WhatsApp, THE Flow_Executor SHALL identify the message as an exercise book scan and enqueue an `image_analyze` task to the Worker_Service
2. THE Worker_Service SHALL send the exercise book image to the AI_Client using the ANALYSIS-001 prompt with multimodal (image + text) content
3. THE AI_Client SHALL return a structured JSON response containing: identified errors, error patterns, traced foundational gaps (as CurriculumNode codes), and recommended focus areas
4. WHEN the analysis is complete, THE Flow_Executor SHALL create or update a GapProfile for the student with source "exercise_book"
5. WHEN the analysis is complete, THE Flow_Executor SHALL send the teacher a summary of findings via WhatsApp including the identified gaps and recommended next steps
6. IF the image is too blurry or unreadable, THEN THE AI_Client SHALL return a response indicating the image quality issue, and THE Flow_Executor SHALL ask the teacher to retake the photo

### Requirement 10: Parent Activity Delivery with TTS Voice Notes

**User Story:** As a parent, I want to receive daily voice messages in my preferred language with 3-minute learning activities for my child, so that I can support my child's learning at home using household materials.

#### Acceptance Criteria

1. THE Flow_Executor SHALL use the PARENT-001 prompt to generate a personalized daily activity based on the student's current GapProfile and the parent's preferred language
2. THE Flow_Executor SHALL use the ACT-001 prompt to generate the specific 3-minute activity using household materials from the Cultural_Context for the parent's country
3. WHEN an activity is generated, THE Flow_Executor SHALL pass the activity text through the Guard_Service (GUARD-001) before delivery
4. WHEN the activity passes the GUARD-001 check, THE Flow_Executor SHALL enqueue a `tts_generate` task to convert the activity text to a voice note in the parent's L1 language
5. WHEN the TTS voice note is ready, THE Worker_Service SHALL send the voice note to the parent via WhatsApp as an audio message
6. THE Flow_Executor SHALL also send a text version of the activity in the parent's preferred language alongside the voice note
7. THE Flow_Executor SHALL schedule activity delivery at the configured optimal time (default 6:30 PM local time) based on the country's timezone

### Requirement 11: Teacher Conversation Partner

**User Story:** As a teacher, I want to have a persistent WhatsApp conversation where I can ask questions about my class and receive AI-powered pedagogical guidance, so that I can better support students with learning gaps.

#### Acceptance Criteria

1. WHEN a teacher sends a text message via WhatsApp, THE Flow_Executor SHALL route the message to the teacher conversation flow
2. THE Flow_Executor SHALL use the TEACHER-001 prompt to analyze the teacher's question in the context of their class's aggregate gap data
3. THE Flow_Executor SHALL use the TEACHER-002 prompt to generate a pedagogical response with specific, actionable classroom strategies
4. THE Flow_Executor SHALL use the TEACHER-003 prompt to format the response for WhatsApp delivery with appropriate length and structure
5. WHEN the teacher asks about a specific student, THE Flow_Executor SHALL retrieve that student's current GapProfile and include the gap details in the AI context
6. WHEN the teacher asks about class-wide patterns, THE Flow_Executor SHALL aggregate GapProfile data across all students in the teacher's class and include the aggregate in the AI context
7. THE Flow_Executor SHALL maintain conversation history for the teacher session to enable multi-turn dialogue

### Requirement 12: Voice Micro-Coaching for Parents

**User Story:** As a parent, I want to send voice replies about how the activity went and receive AI coaching feedback, so that I can improve how I support my child's learning.

#### Acceptance Criteria

1. WHEN a parent sends a voice message via WhatsApp, THE Flow_Executor SHALL enqueue a `voice_transcribe` task to the Worker_Service
2. WHEN the transcription is complete, THE Worker_Service SHALL send the transcript to the AI_Client using the ANALYSIS-002 prompt for pedagogical coaching analysis
3. THE AI_Client SHALL return a structured response containing: parent engagement assessment, coaching feedback, and a suggested follow-up activity
4. WHEN the coaching response is generated, THE Flow_Executor SHALL pass the response through the Guard_Service (GUARD-001) before delivery
5. WHEN the coaching response passes the GUARD-001 check, THE Flow_Executor SHALL send the coaching feedback to the parent via WhatsApp in the parent's preferred language
6. THE Flow_Executor SHALL update the ParentInteraction record with the transcript, sentiment score, and coaching response

### Requirement 13: Application Startup and Service Initialization

**User Story:** As a platform developer, I want all new services to be initialized during application startup with proper health checks, so that the platform is fully operational when it begins serving traffic.

#### Acceptance Criteria

1. WHEN the FastAPI application starts, THE lifespan handler SHALL initialize the AI_Client as a shared singleton with connection pooling
2. WHEN the FastAPI application starts, THE lifespan handler SHALL initialize the Prompt_Service and load all v2.0 prompts, country configs, cultural contexts, and language files
3. WHEN the FastAPI application starts, THE lifespan handler SHALL verify connectivity to S3 (or LocalStack in local environment)
4. THE health check endpoint SHALL report the status of: database, prompt library (with version and prompt count), AI client readiness, and S3 connectivity
5. WHEN the FastAPI application shuts down, THE lifespan handler SHALL close the AI_Client's HTTP connection pool and release all resources
6. IF any critical service (database, prompt library) fails to initialize, THEN THE application SHALL refuse to start and log a descriptive error message
