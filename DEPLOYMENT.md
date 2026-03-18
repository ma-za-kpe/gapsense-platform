# GapSense Deployment Guide

## Environment Configuration

### 1. AWS Secrets Manager

All production secrets are stored in AWS Secrets Manager (us-east-1):

```bash
# List all secrets
aws secretsmanager list-secrets --region us-east-1 --query 'SecretList[?contains(Name, `gapsense`)]'

# Current secrets:
- gapsense/prod/database     # PostgreSQL credentials
- gapsense/prod/anthropic    # Anthropic API key
- gapsense/prod/grok         # Grok API key
- gapsense/prod/twilio       # Twilio WhatsApp credentials
- gapsense/prod/openai       # OpenAI API key
- gapsense/prod/api-base-url # API base URL (AWS ALB)
```

#### Retrieve a secret:
```bash
aws secretsmanager get-secret-value \
  --secret-id gapsense/prod/api-base-url \
  --region us-east-1 \
  --query 'SecretString' \
  --output text
```

### 2. Vercel Environment Variables

Set via Vercel CLI or Dashboard:

```bash
# Add environment variable
vercel env add API_BASE_URL production

# List environment variables
vercel env ls

# Pull environment variables to local .env
vercel env pull
```

**Current Vercel environment variables:**
- `API_BASE_URL` - Backend API base URL (production only)

### 3. Local Development

For local development, copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

#### Key variables for local development:

```bash
# Local Docker backend
VITE_API_BASE_URL=http://localhost:8000

# Or test against production AWS
VITE_API_BASE_URL=http://gapsense-prod-alb-1888969750.us-east-1.elb.amazonaws.com
```

## Deployment Workflows

### Production Deployment (Vercel)

1. **Generate vercel.json** from template:
   ```bash
   ./scripts/generate-vercel-config.sh
   ```
   This fetches `API_BASE_URL` from AWS Secrets Manager and generates `vercel.json`.

2. **Deploy to Vercel**:
   ```bash
   vercel --prod
   ```

### Local Testing

1. **Start Docker backend**:
   ```bash
   docker compose up -d
   ```

2. **Start Vite dev server**:
   ```bash
   npm run dev
   ```

   Vite will proxy `/demo/api/*` to `$VITE_API_BASE_URL` (from `.env`).

3. **Access demo**:
   - Frontend: http://localhost:3000/demo.html
   - Backend API: http://localhost:8000/demo/api/...

## Configuration Management

### Updating API Base URL

**In AWS Secrets Manager:**
```bash
aws secretsmanager update-secret \
  --secret-id gapsense/prod/api-base-url \
  --secret-string '{"url":"http://new-alb-url.amazonaws.com"}' \
  --region us-east-1
```

**In Vercel:**
```bash
# Remove old value
vercel env rm API_BASE_URL production

# Add new value
vercel env add API_BASE_URL production
```

**Regenerate vercel.json:**
```bash
./scripts/generate-vercel-config.sh
git add vercel.json
git commit -m "chore: update API base URL"
vercel --prod
```

## Architecture

```
┌─────────────────┐
│   Vercel CDN    │  (Static files: HTML, CSS, JS)
│  (Frontend)     │
└────────┬────────┘
         │
         │ /demo/api/* rewrites to API_BASE_URL
         ↓
┌─────────────────┐
│   AWS ALB       │  (Load Balancer)
│  us-east-1      │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   ECS Fargate   │  (Backend containers)
│   FastAPI       │
└─────────────────┘
```

## Security Best Practices

1. ✅ **Never commit secrets** to git (.env is in .gitignore)
2. ✅ **Use AWS Secrets Manager** for production secrets
3. ✅ **Use Vercel environment variables** for deployment-specific config
4. ✅ **Rotate secrets regularly** (especially API keys)
5. ✅ **Use IAM roles** for AWS service access (not hardcoded keys)

## Troubleshooting

### Vercel deployment fails with "Cannot connect to backend"
- Check `vercel.json` has correct API_BASE_URL
- Run `./scripts/generate-vercel-config.sh` to regenerate
- Verify AWS ALB is accessible: `curl http://gapsense-prod-alb-...amazonaws.com/health`

### Local dev server cannot reach backend
- Check `VITE_API_BASE_URL` in `.env`
- Ensure Docker is running: `docker compose ps`
- Check backend health: `curl http://localhost:8000/health`

### Environment variable not updating
- Restart Vite dev server after changing `.env`
- Redeploy to Vercel after updating environment variables
- Clear Vercel cache: `vercel --prod --force`
