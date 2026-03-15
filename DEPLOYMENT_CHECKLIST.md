# GapSense Teacher MVP - Production Deployment Checklist

## Pre-Deployment Configuration

### 1. Environment Variables (.env for production)

Create `.env` file based on `.env.example` with production values:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://gapsense:STRONG_PASSWORD@db-host:5432/gapsense

# AI Provider
ANTHROPIC_API_KEY=sk-ant-production-key-here
GROK_API_KEY=xai-production-key-here  # Fallback

# WhatsApp (choose provider)
WHATSAPP_PROVIDER=meta  # or "twilio"

# Meta WhatsApp Cloud API (recommended for production)
WHATSAPP_API_TOKEN=your_meta_production_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=your_secure_verify_token  # Must match Meta webhook config

# Twilio WhatsApp API (alternative)
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+your_number

# AWS (Africa South - Cape Town region recommended for Ghana)
AWS_REGION=af-south-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
SQS_QUEUE_URL=https://sqs.af-south-1.amazonaws.com/ACCOUNT_ID/gapsense-messages.fifo
S3_MEDIA_BUCKET=gapsense-media-prod

# Auth (if using Cognito)
COGNITO_USER_POOL_ID=af-south-1_xxxxx
COGNITO_CLIENT_ID=your_client_id

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO  # Change from DEBUG
DEBUG=false  # IMPORTANT: Must be false in production

# Data Path (curriculum files)
GAPSENSE_DATA_PATH=/app/data
```

### 2. Database Setup

**Run migrations:**
```bash
docker compose exec web alembic upgrade head
```

**Load curriculum data:**
```bash
# Ensure curriculum files are in gapsense-data/curricula/
docker compose exec web python -m gapsense.scripts.load_curriculum
```

**Verify database:**
```bash
docker compose exec db psql -U gapsense -c "
  SELECT COUNT(*) FROM curriculum_nodes;
  SELECT COUNT(*) FROM schools;
  SELECT COUNT(*) FROM teachers;
"
```

### 3. WhatsApp Webhook Configuration

**Meta WhatsApp Cloud API:**
1. Go to Meta App Dashboard → WhatsApp → Configuration
2. Set webhook URL: `https://your-domain.com/v1/webhooks/whatsapp`
3. Set verify token (must match `WHATSAPP_VERIFY_TOKEN` in .env)
4. Subscribe to webhook fields:
   - `messages` ✅
   - `message_status` ✅

**Twilio WhatsApp API:**
1. Go to Twilio Console → WhatsApp Senders
2. Set webhook URL: `https://your-domain.com/v1/webhooks/whatsapp`
3. HTTP Method: POST
4. Set `Content-Type: application/json` in webhook settings (optional)

**Test webhook verification:**
```bash
# Should return "success" or challenge string
curl "https://your-domain.com/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=test123"
```

### 4. AWS Infrastructure Setup

**S3 Bucket (for exercise book images):**
```bash
aws s3 mb s3://gapsense-media-prod --region af-south-1
aws s3api put-bucket-versioning --bucket gapsense-media-prod --versioning-configuration Status=Enabled
aws s3api put-public-access-block --bucket gapsense-media-prod --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

**SQS Queue (for background image analysis):**
```bash
# Create FIFO queue for image analysis tasks
aws sqs create-queue \
  --queue-name gapsense-messages.fifo \
  --attributes FifoQueue=true,ContentBasedDeduplication=true \
  --region af-south-1
```

**IAM Permissions:**
Ensure service account has:
- `s3:PutObject`, `s3:GetObject` on `gapsense-media-prod`
- `sqs:SendMessage`, `sqs:ReceiveMessage`, `sqs:DeleteMessage` on `gapsense-messages.fifo`

### 5. Docker Deployment

**Build production image:**
```bash
docker build -t gapsense-web:latest .
```

**Start services:**
```bash
docker compose up -d db web
```

**Check health:**
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy","version":"1.0.0"}
```

## Post-Deployment Verification

### 1. API Health Check
```bash
curl https://your-domain.com/health
```

Expected response:
```json
{"status":"healthy","version":"1.0.0","database":"connected"}
```

### 2. WhatsApp Webhook Test
Send "Hi" to your WhatsApp number and verify:
- Teacher receives welcome message
- Logs show: "Webhook received" → "Routing to TeacherFlowExecutor"
- No errors in application logs

### 3. Teacher Onboarding Flow Test

**Test sequence:**
1. Send "START" → Should receive school name prompt
2. Send school name → Should receive class name prompt
3. Send class name → Should receive student count prompt
4. Send student count → Should receive student list prompt
5. Send student names → Should receive confirmation
6. Confirm → Onboarding complete

### 4. Teacher Commands Test

**Test /STATUS:**
```
Teacher sends: /STATUS
Expected: Class overview with student count
```

**Test /GAPS:**
```
Teacher sends: /GAPS
Expected: "No gaps identified yet" or gap breakdown if scans exist
```

**Test /STUDENT:**
```
Teacher sends: /STUDENT Kwame
Expected: Individual student report (or "No scans yet")
```

### 5. Exercise Book Scan Test

**Test image upload flow:**
1. Teacher sends exercise book photo
2. Should receive: "Which student is this for? 1. Student1 2. Student2..."
3. Teacher replies "1"
4. Should receive: "Analyzing [Student]'s exercise book..."
5. Wait ~30 seconds
6. Should receive: Analysis results with gaps identified

## Monitoring & Logs

**Check application logs:**
```bash
docker compose logs web --tail=100 -f
```

**Check worker logs (if using separate worker):**
```bash
docker compose logs worker --tail=100 -f
```

**Monitor SQS queue:**
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.af-south-1.amazonaws.com/ACCOUNT_ID/gapsense-messages.fifo \
  --attribute-names ApproximateNumberOfMessages
```

## Rollback Plan

If issues occur:
```bash
# Stop services
docker compose down

# Restore previous database backup
docker compose exec db psql -U gapsense < backup.sql

# Rollback to previous image
docker compose up -d db web --build
```

## Security Checklist

- [ ] `DEBUG=false` in production .env
- [ ] `LOG_LEVEL=INFO` (not DEBUG) in production
- [ ] Database uses strong password
- [ ] All secrets in .env (never hardcoded)
- [ ] .env is in .gitignore (verify: `git check-ignore .env`)
- [ ] HTTPS enabled for webhook endpoint
- [ ] S3 bucket has public access blocked
- [ ] IAM permissions follow least privilege principle
- [ ] Rate limiting configured (see .env ANTHROPIC_MAX_REQUESTS_PER_MINUTE)

## Teacher MVP Specific Verification

**Core functionality to test:**
- ✅ Teacher onboarding with school registration
- ✅ Student roster creation (bulk upload)
- ✅ Exercise book image upload → student selection
- ✅ Background image analysis via SQS worker
- ✅ Gap profile creation from exercise book
- ✅ Teacher receives analysis results
- ✅ `/STATUS` command shows class overview
- ✅ `/GAPS` command shows common gaps
- ✅ `/STUDENT <name>` command shows individual report

## Known Limitations for Teacher MVP

- Parent flows are present but not actively tested in this deployment
- Parent onboarding links to existing students (teacher creates roster first)
- Multi-language support present but messages currently English-only
- Voice messages and micro-coaching features present but not tested

## Support Contacts

If deployment issues occur:
- Check logs first: `docker compose logs web -f`
- Verify webhook connectivity
- Check AWS credentials and permissions
- Review environment variables match .env.example structure
