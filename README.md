# GapSense Platform

**AI-Powered Foundational Learning Diagnostic Platform for Ghana**

[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## 🎯 MVP Focus (Phase 1a — February 2026)

**The Core Problem We're Solving:**
JHS teachers inherit students with invisible primary-level gaps. A student struggling with fractions might actually have a P4 place-value gap. Teachers need to diagnose these gaps without adding another test.

**Our Solution:**
A WhatsApp-based AI that **analyzes photos of students' exercise books**, identifies error patterns, traces them to foundational gaps, and engages parents with targeted activities.

---

## 🚨 Current Status (February 16, 2026)

**MVP Specification:** Teacher-initiated exercise book scanner + parent evening voice notes
**Current Implementation:** 15% complete

### ✅ What's Working:
- WhatsApp webhook infrastructure
- Parent onboarding flow (FLOW-ONBOARD: 7 steps)
- Student record creation
- Database schema (PostgreSQL)
- AI prompt library (13 prompts in gapsense-data repo)
- Opt-out flow (11+ keywords in 5 languages)

### ❌ What's Missing (Core MVP Features):
- **Exercise Book Scanner** (multimodal AI analysis) — THE CORE FEATURE
- Teacher onboarding + class roster upload
- Multimodal AI integration (Claude/Gemini vision)
- Scheduled parent voice notes (6:30 PM daily in Twi)
- Text-to-speech (Twi)
- Speech-to-text (parent voice responses)
- Teacher conversation partner
- Weekly Gap Map

**See:** [docs/mvp_specification_audit_CRITICAL.md](docs/mvp_specification_audit_CRITICAL.md) for full gap analysis

---

## 📖 The Actual MVP (from MVP Blueprint)

### For Teachers:
```
1. Teacher sends "START" → Registers class → Creates 42 student profiles
2. Teacher sends photo of Kwame's exercise book
3. AI analyzes handwriting → Identifies error patterns
4. Returns: "Kwame errors on borrowing across place values (P4 gap).
   Suggested micro-intervention: 3-min warm-up with GH₵ subtraction."
5. Teacher asks: "I'm teaching fractions tomorrow. What should I worry about?"
6. AI reasons across all diagnosed students → Suggests lesson adjustments
```

### For Parents:
```
1. Teacher shares GapSense number at PTA meeting
2. Parent sends "START" → Links to existing student → Chooses language (Twi)
3. Daily 6:30 PM: Parent receives Twi voice note with 3-minute activity
   "Tonight: Ask Kwame to figure out 3 sachets of pure water at 50p each"
4. Parent sends 👍 when done
5. Parent sends voice note: "He got it but took too long, is that okay?"
6. AI provides pedagogical coaching: "Perfect! Speed comes later..."
```

### Success Criteria (12-Week Pilot):
1. **AI Diagnostic Works:** 75%+ concordance with expert teacher assessment
2. **Humans Use It:** 7/10 teachers scan 2+/week, 60%+ parents respond to 3/5 prompts
3. **Students Improve:** 0.15+ SD improvement on re-scan after 12 weeks

**Scale:** 10 teachers, 100 parents, 400-500 students
**Budget:** Under $700 for 12 weeks
**Region:** Greater Accra
**Subject:** JHS 1 Mathematics ONLY
**Languages:** English + Twi ONLY

---

## 🏗️ Architecture

**Current (Infrastructure Only):**
```
WhatsApp → Webhook → FlowExecutor → Database → WhatsApp
```

**Target MVP Architecture:**
```
WhatsApp → Image Upload → Claude Vision → Exercise Book Analysis
                                        ↓
                                   Gap Profile → Database
                                        ↓
                         6:30 PM → Activity Generator → Twi TTS → Parent Voice Note
                                        ↓
                         Parent Voice → Whisper STT → Micro-Coaching → Twi TTS
```

**Stack:**
- **Backend**: FastAPI (Python 3.12), async everywhere
- **Database**: PostgreSQL 16
- **AI (Planned)**:
  - Multimodal: Claude Sonnet 4.5 with vision OR Gemini Pro Vision
  - Text: Claude Sonnet/Haiku for conversation
  - TTS: Google Cloud TTS (Twi) or ElevenLabs
  - STT: Whisper API
- **Messaging**: WhatsApp Cloud API
- **Infrastructure**: AWS (Cape Town region)

---

## 📁 Project Structure

```
gapsense/
├── src/gapsense/
│   ├── core/                  # Models, config
│   ├── engagement/            # WhatsApp flows (ONBOARD, OPT-OUT)
│   ├── webhooks/              # WhatsApp webhook handlers
│   ├── diagnostic/            # Diagnostic engine (partial)
│   ├── ai/                    # AI client + prompt loader
│   └── api/                   # REST API endpoints
├── tests/                     # 268 tests (58% coverage)
├── alembic/                   # Database migrations (6 versions)
├── docs/                      # Documentation
│   ├── mvp_specification_audit_CRITICAL.md    # Gap analysis
│   └── mvp_user_flows_realistic_status.md     # Realistic flows
└── scripts/                   # Utility scripts
```

**Proprietary Data (Separate Repo):**
```
gapsense-data/
├── prompts/                   # 13 AI prompts (COMPLETE)
│   └── gapsense_prompt_library_v1.1.json
├── curriculum/                # NaCCA prerequisite graph
│   └── gapsense_prerequisite_graph_v1.2.json
└── business/                  # Strategy docs
    ├── GapSense_MVP_Blueprint.docx           # ← SOURCE OF TRUTH
    └── GapSense_v2_AI_Native_Redesign.docx
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 16
- Poetry
- Access to `gapsense-data` private repo

### Setup

```bash
# 1. Clone repos
git clone <gapsense-repo>
cd gapsense

# Clone data repo (sibling directory)
cd ..
git clone <gapsense-data-repo>  # Private
cd gapsense

# 2. Install dependencies
poetry install

# 3. Set up database
createdb gapsense_dev
poetry run alembic upgrade head

# 4. Set environment variables
cp .env.example .env
# Edit .env with your credentials:
# - DATABASE_URL
# - ANTHROPIC_API_KEY (for AI)
# - WHATSAPP_VERIFY_TOKEN
# - WHATSAPP_PHONE_NUMBER_ID
# - WHATSAPP_ACCESS_TOKEN

# 5. Load curriculum data
export GAPSENSE_DATA_PATH=../gapsense-data
poetry run python scripts/load_curriculum.py

# 6. Run tests
poetry run pytest

# 7. Start server
poetry run uvicorn gapsense.main:app --reload
```

---

## 🎨 Frontend Development Guide

### Overview

The GapSense frontend is a **mobile-first, progressive web app** built with vanilla JavaScript and optimized for Ghana's 3G networks. All frontend code lives in `/public/` and is served statically by Vite.

### Architecture

```
public/
├── frontend/
│   ├── css/
│   │   ├── base/           # Variables, reset, typography
│   │   ├── layouts/        # Page layouts (demo, dashboard)
│   │   ├── components/     # Component-specific styles
│   │   └── demo.css        # Main entry point
│   ├── js/
│   │   ├── constants.js    # Config (API URLs, polling settings)
│   │   ├── state.js        # Global state management
│   │   ├── api.js          # API client with adaptive polling
│   │   ├── ui.js           # DOM manipulation
│   │   ├── mobile.js       # Touch gestures, swipes
│   │   ├── slides.js       # WhatsApp simulator slides
│   │   ├── APIClient.js    # Robust HTTP client with retry
│   │   └── components/     # Reusable components
│   │       ├── Toast.js
│   │       ├── LoadingSpinner.js
│   │       └── TouchHandler.js
│   ├── demo.html           # Main demo page
│   ├── teacher_reports.html # Teacher dashboard
│   ├── student_detailed_report.html # Student analysis
│   └── sw.js               # Service Worker (offline PWA)
├── index.html              # Landing page
└── assets/                 # Images, fonts
```

### Tech Stack

- **No Framework**: Vanilla JavaScript (ES6 modules)
- **Build Tool**: Vite 5.0 (fast HMR, optimized builds)
- **Styling**: Pure CSS with CSS custom properties
- **Type Checking**: TypeScript (checkJs mode for gradual typing)
- **Bundle Size**: <200KB target for 3G networks
- **Offline**: Service Worker with cache-first strategy

### Key Design Principles

1. **Mobile-First**: All UI designed for 320px+ screens first
2. **Touch-Optimized**: 44px+ touch targets, swipe gestures
3. **Battery-Friendly**: Adaptive polling, pause when tab hidden
4. **Offline-First**: Service Worker caches assets
5. **3G-Optimized**: Lazy loading, code splitting, <200KB bundle
6. **Accessibility**: ARIA labels, keyboard navigation, screen readers

### Getting Started

#### 1. Install Dependencies

```bash
npm install
```

This installs:
- `vite` - Build tool and dev server
- `typescript` - Type checking for JS files
- `@types/node` - Node.js type definitions
- `terser` - JavaScript minifier

#### 2. Development Server

```bash
npm run dev
```

- Opens `http://localhost:5173`
- Hot Module Replacement (HMR) enabled
- Auto-reloads on file changes

#### 3. Type Checking

```bash
# Check types once
npm run type-check

# Watch mode (live type checking)
npm run type-check:watch

# Combined linting (JS + CSS + Types)
npm run lint
```

#### 4. Build for Production

```bash
npm run build
```

Outputs to `/dist/`:
- Minified JS (<15KB gzipped)
- Optimized CSS
- Code splitting per route
- Source maps for debugging

#### 5. Preview Production Build

```bash
npm run preview
```

Tests the production build locally before deploying.

### Making Changes

#### Adding a New Page

1. **Create HTML file** in `/public/`
   ```html
   <!DOCTYPE html>
   <html lang="en">
   <head>
       <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <link rel="stylesheet" href="/frontend/css/demo.css">
   </head>
   <body>
       <!-- Your content -->
       <script type="module" src="/frontend/js/main.js"></script>
   </body>
   </html>
   ```

2. **Add route** in backend (`src/gapsense/web/demo.py`)
   ```python
   @router.get("/new-page", response_class=HTMLResponse)
   async def new_page(request: Request):
       return templates.TemplateResponse("new_page.html", {"request": request})
   ```

3. **Test locally**: Visit `http://localhost:5173/demo/new-page`

#### Adding a New Component

1. **Create JS module** in `/public/frontend/js/components/`
   ```javascript
   // MyComponent.js
   export class MyComponent {
       constructor(options) {
           this.options = options;
       }

       render() {
           // DOM creation
       }
   }
   ```

2. **Import in main.js**
   ```javascript
   import { MyComponent } from './components/MyComponent.js';

   const myComp = new MyComponent({ /* options */ });
   myComp.render();
   ```

3. **Add JSDoc types** for TypeScript checking
   ```javascript
   /**
    * @typedef {Object} MyComponentOptions
    * @property {string} title
    * @property {boolean} isActive
    */

   /**
    * @param {MyComponentOptions} options
    */
   constructor(options) { }
   ```

#### Modifying Styles

1. **Find the right file**:
   - Global variables: `/public/frontend/css/base/_variables.css`
   - Layout: `/public/frontend/css/layouts/demo.css`
   - Component: `/public/frontend/css/components/<name>.css`

2. **Use CSS custom properties**:
   ```css
   :root {
       --primary-color: #25D366;
       --mobile-padding: 16px;
   }

   .my-element {
       color: var(--primary-color);
       padding: var(--mobile-padding);
   }
   ```

3. **Mobile-first media queries**:
   ```css
   /* Mobile default */
   .card {
       padding: 16px;
   }

   /* Tablet and up */
   @media (min-width: 768px) {
       .card {
           padding: 24px;
       }
   }
   ```

#### Updating API Endpoints

1. **Edit constants** in `/public/frontend/js/constants.js`
   ```javascript
   export const API = {
       MESSAGE: '/demo/api/message',
       NEW_ENDPOINT: '/demo/api/new-endpoint'
   };
   ```

2. **Add API function** in `/public/frontend/js/api.js`
   ```javascript
   export async function callNewEndpoint(data) {
       const response = await fetch(API.NEW_ENDPOINT, {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify(data)
       });
       return response.json();
   }
   ```

3. **Create backend route** in `src/gapsense/web/demo.py`
   ```python
   @router.post("/api/new-endpoint")
   async def new_endpoint(data: dict):
       return {"success": True, "data": data}
   ```

### Mobile Optimizations

#### Battery-Friendly Polling

The app uses **adaptive polling** that saves battery:

```javascript
// constants.js
export const POLLING = {
    INITIAL_INTERVAL: 1000,    // Start fast (1s)
    MAX_INTERVAL: 5000,        // Max 5s between polls
    BACKOFF_MULTIPLIER: 1.5,   // Exponential backoff
    PAUSE_WHEN_HIDDEN: true    // Pause when tab hidden
};
```

**How it works**:
- Starts at 1s for quick feedback
- Backs off to 5s to save battery (1s → 1.5s → 2.25s → 3.38s → 5s)
- **Pauses completely when tab is hidden** (Page Visibility API)
- Saves ~70% battery vs fixed 2s polling

#### Virtual Scrolling

Long lists (50+ students) use **virtual scrolling**:

```javascript
// Only loads 15 students initially
const BATCH_SIZE = 15;

// Loads more as user scrolls (Intersection Observer)
observer.observe(sentinel);
```

#### Lazy Loading Images

```html
<img loading="lazy" src="/assets/image.jpg" alt="...">
```

#### Code Splitting

Vite automatically splits code per route:
- `/demo` → `demo-[hash].js`
- `/reports` → `reports-[hash].js`

### Performance Budget

- **Total Bundle**: <200KB (uncompressed)
- **Gzipped**: ~15KB for demo page
- **Time to Interactive**: <3s on 3G
- **First Contentful Paint**: <2s on 3G

Check bundle size:
```bash
npm run build
ls -lh dist/assets/
```

### Service Worker (Offline Support)

The Service Worker caches assets for offline use:

```javascript
// Update cache version to bust cache
const CACHE_VERSION = 'gapsense-v1.0.5';

// Assets cached on install
const STATIC_ASSETS = [
    '/',
    '/demo.html',
    '/frontend/css/demo.css',
    '/frontend/js/main.js',
    // ...
];
```

**Strategy**:
- **Static assets**: Cache-first
- **API calls**: Network-first, fallback to cache
- **Cache busting**: Update `CACHE_VERSION` on deploy

### TypeScript Integration

We use TypeScript for **type checking JavaScript** (not compilation):

```javascript
/**
 * Upload image to server
 * @param {File} file - Image file
 * @param {string} phoneNumber - Teacher phone
 * @returns {Promise<{success: boolean, report_id?: string}>}
 */
async function uploadImage(file, phoneNumber) {
    // TypeScript checks types via JSDoc
}
```

**Benefits**:
- Type safety without converting to `.ts`
- IntelliSense in VS Code
- Catch errors before runtime

See [TYPESCRIPT.md](TYPESCRIPT.md) for full guide.

### Deployment

#### Vercel (Current)

```bash
# Deploy to production
vercel --prod
```

- Auto-deploys on `git push` to `main`
- Preview deployments for PRs
- CDN-backed (global edge network)

#### Backend + Frontend Together

The backend serves frontend files statically:

```python
# src/gapsense/main.py
app.mount("/", StaticFiles(directory="public", html=True), name="public")
```

Both backend and frontend deploy together via Docker/ECS.

### Testing

#### Manual Testing Checklist

- [ ] Test on real mobile devices (not just DevTools)
- [ ] Test on 3G throttling (Chrome DevTools → Network)
- [ ] Test offline (Service Worker)
- [ ] Test swipe gestures on touch devices
- [ ] Test adaptive polling (switch tabs)
- [ ] Test virtual scrolling (50+ students)

#### Browser Support

- **iOS Safari** 14+ ✅
- **Chrome Mobile** 90+ ✅
- **Firefox Mobile** 90+ ✅
- **Desktop** (fallback) ✅

#### Accessibility Testing

```bash
# Run Lighthouse audit
npm run lighthouse

# Check ARIA labels
# Use screen reader: VoiceOver (iOS), TalkBack (Android)
```

### Common Gotchas

1. **Cache not updating?**
   - Bump `CACHE_VERSION` in `sw.js`
   - Hard refresh: Cmd+Shift+R (Mac) / Ctrl+Shift+R (Windows)

2. **HMR not working?**
   - Restart dev server: `npm run dev`
   - Check browser console for errors

3. **TypeScript errors?**
   - Add JSDoc types to functions
   - Use `@ts-ignore` for unavoidable errors

4. **Bundle size too large?**
   - Use dynamic imports: `const module = await import('./big-module.js')`
   - Check bundle analyzer: `npm run analyze`

5. **Mobile styles not applying?**
   - Check viewport meta tag: `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
   - Use mobile-first media queries: `@media (min-width: 768px)`

### Useful Commands

```bash
# Development
npm run dev                  # Start dev server
npm run type-check:watch     # Live type checking
npm run lint                 # Check JS + CSS + types

# Production
npm run build                # Build for production
npm run preview              # Test production build
npm run analyze              # Bundle size visualizer

# Deployment
vercel --prod                # Deploy to Vercel production
```

### Resources

- [Vite Guide](https://vitejs.dev/guide/)
- [TypeScript + JSDoc](https://www.typescriptlang.org/docs/handbook/jsdoc-supported-types.html)
- [Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [Mobile Web Best Practices](https://web.dev/mobile/)

---

## 📊 Development Status

### Phase 1a MVP (Target: 8-10 weeks from now)

| Component | Status | Notes |
|-----------|--------|-------|
| **Infrastructure** | ✅ 75% | WhatsApp, DB, API working |
| **Parent Onboarding** | ✅ 100% | FLOW-ONBOARD complete |
| **Teacher Onboarding** | ❌ 0% | Not started |
| **Exercise Book Scanner** | ❌ 0% | Core MVP feature missing |
| **Multimodal AI** | ❌ 0% | Not integrated |
| **Parent Voice Notes** | ❌ 0% | TTS not implemented |
| **Voice Micro-Coaching** | ❌ 0% | STT not implemented |
| **Teacher Conversation** | ❌ 0% | Not started |
| **Scheduled Messaging** | ❌ 0% | Not implemented |

**Overall: 15% complete toward MVP**

**Next 8 weeks (to MVP):**
- Week 1-2: NaCCA knowledge base + Exercise Book Analyzer prompt + test Twi TTS
- Week 3-4: Multimodal AI integration + image upload
- Week 5-6: Parent voice note system (TTS + activity generator)
- Week 7-8: Teacher conversation partner + integration
- Week 9-20: 12-week pilot measurement

---

## 🧪 Testing

```bash
# Run all tests
poetry run pytest

# With coverage
poetry run pytest --cov=src/gapsense --cov-report=html

# Run specific test
poetry run pytest tests/unit/test_flow_executor.py -v

# Integration tests only
poetry run pytest tests/integration/ -v
```

**Current Coverage:**
- Overall: 58%
- flow_executor.py: 72%
- whatsapp.py: 67%

---

## 🚢 Production Deployment

### Prerequisites
- AWS CLI configured with `gapsense-prod` profile
- Docker with buildx support
- ECR repository: `607415053998.dkr.ecr.us-east-1.amazonaws.com/gapsense-web`
- ECS cluster: `gapsense-prod` (us-east-1)

### Build and Push Docker Image

```bash
# 1. Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  607415053998.dkr.ecr.us-east-1.amazonaws.com

# 2. Build for production (linux/amd64 platform)
docker buildx build \
  --platform linux/amd64 \
  --target production \
  -t gapsense-web:latest \
  -t 607415053998.dkr.ecr.us-east-1.amazonaws.com/gapsense-web:latest \
  --load .

# 3. Push to ECR
docker push 607415053998.dkr.ecr.us-east-1.amazonaws.com/gapsense-web:latest
```

### Deploy to ECS

#### Option 1: Force New Deployment (Most Common)
```bash
# Deploy web service
aws ecs update-service \
  --cluster gapsense-prod \
  --service gapsense-web \
  --force-new-deployment \
  --region us-east-1

# Deploy worker service
aws ecs update-service \
  --cluster gapsense-prod \
  --service gapsense-worker \
  --force-new-deployment \
  --region us-east-1
```

#### Option 2: Update Task Definition First
```bash
# Register new task definitions
aws ecs register-task-definition \
  --cli-input-json file:///tmp/ecs-task-web.json \
  --region us-east-1 \
  --query 'taskDefinition.[family,taskDefinitionArn,status]' \
  --output table

aws ecs register-task-definition \
  --cli-input-json file:///tmp/ecs-task-worker.json \
  --region us-east-1 \
  --query 'taskDefinition.[family,taskDefinitionArn,status]' \
  --output table

# Update services with specific task definition version
aws ecs update-service \
  --cluster gapsense-prod \
  --service gapsense-web \
  --task-definition gapsense-web:3 \
  --force-new-deployment \
  --region us-east-1

aws ecs update-service \
  --cluster gapsense-prod \
  --service gapsense-worker \
  --task-definition gapsense-worker:3 \
  --force-new-deployment \
  --region us-east-1
```

### Monitoring and Verification

```bash
# Check service status
aws ecs describe-services \
  --cluster gapsense-prod \
  --services gapsense-web gapsense-worker \
  --region us-east-1 \
  --query 'services[*].[serviceName,runningCount,desiredCount,deployments[0].rolloutState]' \
  --output table

# Monitor web logs (real-time)
aws logs tail /ecs/gapsense-web \
  --region us-east-1 \
  --follow \
  --format short

# Monitor worker logs (real-time)
aws logs tail /ecs/gapsense-worker \
  --region us-east-1 \
  --follow \
  --format short

# Check recent logs (last 5 minutes)
aws logs tail /ecs/gapsense-web \
  --region us-east-1 \
  --since 5m \
  --format short

# Test health endpoint
curl -s http://3.83.162.241:8000/health
curl -s http://52.87.46.142:8000/health
```

### Database Migrations (Production)

Run Alembic migrations via a one-off ECS Fargate task with a command override. This spins up a temporary container using the same image/secrets as the web service, runs the migration, and exits.

```bash
# 1. Get network config from the running web service
aws ecs describe-services \
  --cluster gapsense-prod \
  --services gapsense-web \
  --region us-east-1 \
  --query 'services[0].networkConfiguration'

# 2. Run migration as a one-off ECS task
aws ecs run-task \
  --cluster gapsense-prod \
  --task-definition gapsense-web \
  --launch-type FARGATE \
  --network-configuration 'awsvpcConfiguration={subnets=[subnet-0ac74240c02834391],securityGroups=[sg-082576d47f78f2cf4],assignPublicIp=ENABLED}' \
  --overrides '{"containerOverrides":[{"name":"gapsense-web","command":["alembic","upgrade","head"]}]}' \
  --region us-east-1

# 3. Monitor the task (get task ID from run-task output)
aws ecs describe-tasks \
  --cluster gapsense-prod \
  --tasks <TASK_ID> \
  --region us-east-1 \
  --query 'tasks[0].{status:lastStatus,exitCode:containers[0].exitCode,reason:stoppedReason}'

# 4. Verify in logs
aws logs tail /ecs/gapsense-web \
  --region us-east-1 \
  --since 5m \
  --format short | grep -i alembic
```

> **Note:** The migration task reuses the `gapsense-web` task definition, which already has the `DATABASE_URL` secret from AWS Secrets Manager. No need to pass credentials manually.

### Production E2E Testing

Run the E2E test against production from inside the local Docker container:

```bash
# Run production E2E test (pass env var with -e flag)
docker compose exec \
  -e E2E_BASE_URL=http://gapsense-prod-alb-1888969750.us-east-1.elb.amazonaws.com \
  web pytest tests/e2e/test_demo_flow_e2e.py::TestDemoFlowE2E::test_complete_demo_flow -xvs

# Run local E2E test (no env var = uses ASGI transport)
docker compose exec web pytest tests/e2e/test_demo_flow_e2e.py::TestDemoFlowE2E::test_complete_demo_flow -xvs
```

The production test:
- Sends real HTTP requests to the ALB
- Skips direct DB verification (polls dashboard instead)
- Waits up to 120s for the worker to process the AI pipeline
- Verifies the gap profile appears on the dashboard

### Production URLs

| Resource | URL |
|----------|-----|
| ALB | `http://gapsense-prod-alb-1888969750.us-east-1.elb.amazonaws.com` |
| Health | `http://gapsense-prod-alb-1888969750.us-east-1.elb.amazonaws.com/health` |
| Demo Dashboard | `http://gapsense-prod-alb-1888969750.us-east-1.elb.amazonaws.com/demo/reports/<phone>` |

### Secrets Management

Secrets are stored in AWS Secrets Manager and injected into ECS tasks:

| Secret | ARN Path |
|--------|----------|
| DATABASE_URL | `gapsense/prod/database` |
| ANTHROPIC_API_KEY | `gapsense/prod/anthropic` |
| GROK_API_KEY | `gapsense/prod/grok` |
| TWILIO_* | `gapsense/prod/twilio` |

```bash
# List all production secrets
aws secretsmanager list-secrets \
  --region us-east-1 \
  --query 'SecretList[?starts_with(Name, `gapsense/prod/`)].[Name]' \
  --output table
```

### Infrastructure Setup (One-Time)

```bash
# Create S3 bucket for media
aws s3api create-bucket \
  --bucket gapsense-media-prod \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket gapsense-media-prod \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket gapsense-media-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Create CloudWatch log groups
aws logs create-log-group \
  --log-group-name /ecs/gapsense-web \
  --region us-east-1

aws logs create-log-group \
  --log-group-name /ecs/gapsense-worker \
  --region us-east-1

# List secrets (verify configuration)
aws secretsmanager list-secrets \
  --region us-east-1 \
  --query 'SecretList[?starts_with(Name, `gapsense/prod/`)].[Name,ARN]' \
  --output table
```

### Deployment Checklist

Before deploying to production:

1. ✅ **Test locally**: Run E2E tests with `docker compose`
2. ✅ **Review changes**: Check `git diff` and `git status`
3. ✅ **Build image**: Ensure `docker buildx build` succeeds
4. ✅ **Push to ECR**: Verify image uploaded successfully
5. ✅ **Deploy services**: Update both web and worker services
6. ✅ **Monitor logs**: Watch for errors in first 2-3 minutes
7. ✅ **Test endpoints**: Verify `/health` returns 200
8. ✅ **Check RDS**: Ensure database connection works
9. ✅ **Test WhatsApp**: Send test message to verify webhook
10. ✅ **Monitor metrics**: Check CloudWatch for errors/performance

### Rollback Procedure

```bash
# List recent task definition versions
aws ecs list-task-definitions \
  --family-prefix gapsense-web \
  --sort DESC \
  --max-items 5 \
  --region us-east-1

# Rollback to previous version
aws ecs update-service \
  --cluster gapsense-prod \
  --service gapsense-web \
  --task-definition gapsense-web:2 \
  --force-new-deployment \
  --region us-east-1
```

---

## 📚 Key Documents

### Specifications (Source of Truth):
- **[GapSense_MVP_Blueprint.docx](../gapsense-data/business/GapSense_MVP_Blueprint.docx)** — The actual MVP (8 weeks, $700)
- **[gapsense_prompt_library_v1.1.json](../gapsense-data/prompts/)** — All 13 AI prompts
- **[gapsense_prerequisite_graph_v1.2.json](../gapsense-data/curriculum/)** — NaCCA curriculum

### Current Status:
- **[mvp_specification_audit_CRITICAL.md](docs/mvp_specification_audit_CRITICAL.md)** — Gap analysis
- **[mvp_user_flows_realistic_status.md](docs/mvp_user_flows_realistic_status.md)** — Real-world flows

### Architecture:
- **[ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)** — System design
- **[gapsense_adr.md](docs/architecture/gapsense_adr.md)** — Architecture decisions

---

## 🎯 MVP Success Metrics

From MVP Blueprint, Section 6:

**Question 1: Does the AI diagnostic work?**
- Metric: 75%+ concordance between AI and expert teacher on root cause identification
- Test: 100 exercise book scans validated by expert teachers

**Question 2: Do humans use it?**
- Teachers: 7/10 complete 2+ scans/week for 8+ of 12 weeks
- Parents: 60%+ respond to 3+ of 5 weekly prompts after month 1
- Wolf/Aurino: Parents with no formal education engage at 40%+ of overall rate

**Question 3: Do students improve?**
- Metric: 0.15+ standard deviation improvement on re-scan after 12 weeks
- Stronger signal: Students with active parent engagement improve more

---

## 📝 License

Proprietary. © 2026 GapSense. All rights reserved.

---

## 🤝 Contributing

This is a private project. Contact the team for access.

---

**Last Updated:** February 16, 2026
**MVP Target:** April 2026 (8-10 weeks from now)
