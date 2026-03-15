# GapSense AWS Deployment Checklist

## Pre-Deployment Audit

### 1. Code Quality & Security
- [ ] All pre-commit hooks pass (ruff, mypy, bandit, detect-secrets)
- [ ] No real secrets in codebase (use AWS Secrets Manager)
- [ ] All tests pass with >80% coverage
- [ ] Vulnerability scan passed (safety check)
- [ ] No dead code (vulture check)
- [ ] Dependencies audited (deptry check)

### 2. Database Migrations
- [ ] All Alembic migrations tested locally
- [ ] Migration rollback plans documented
- [ ] Database backup strategy in place
- [ ] `analysis_metadata` column added to `gap_profiles`
- [ ] Curriculum data loaded (Ghana PRIMARY + SECONDARY)

### 3. Environment Configuration
- [ ] Production `.env` file configured (DO NOT commit)
- [ ] AWS credentials configured
- [ ] Anthropic API key in AWS Secrets Manager
- [ ] Twilio credentials in AWS Secrets Manager
- [ ] S3 bucket created for media storage
- [ ] SQS FIFO queue created for worker tasks
- [ ] RDS PostgreSQL database provisioned

### 4. Application Configuration
```bash
# Required environment variables
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/gapsense
ANTHROPIC_API_KEY=<from Secrets Manager>
TWILIO_ACCOUNT_SID=<from Secrets Manager>
TWILIO_AUTH_TOKEN=<from Secrets Manager>
TWILIO_PHONE_NUMBER=<from Secrets Manager>
WHATSAPP_WEBHOOK_VERIFY_TOKEN=<random secure string>
AWS_ACCESS_KEY_ID=<IAM credentials>
AWS_SECRET_ACCESS_KEY=<IAM credentials>
AWS_REGION=us-east-1
S3_BUCKET_NAME=gapsense-media-prod
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/...
APP_URL=https://your-domain.com
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## AWS Infrastructure Setup

### 5. Networking
- [ ] VPC created with public and private subnets
- [ ] Security groups configured:
  - Web: 80, 443 inbound
  - Database: 5432 from web only
  - Worker: Outbound only for S3/SQS access
- [ ] Application Load Balancer configured
- [ ] SSL/TLS certificate obtained (ACM)
- [ ] DNS records configured

### 6. Compute Resources
- [ ] ECS cluster created
- [ ] Task definitions created for:
  - `gapsense-web` (Fargate)
  - `gapsense-worker` (Fargate)
- [ ] Auto-scaling policies configured
- [ ] CloudWatch logs enabled
- [ ] Health checks configured

### 7. Database (RDS PostgreSQL)
- [ ] RDS instance provisioned (PostgreSQL 15+)
- [ ] Automated backups enabled (7-day retention minimum)
- [ ] Multi-AZ deployment for production
- [ ] Connection pooling configured
- [ ] Performance Insights enabled
- [ ] Encryption at rest enabled
- [ ] Snapshot before deployment

### 8. Storage (S3)
- [ ] S3 bucket created with versioning
- [ ] Bucket policy configured (restrict public access)
- [ ] Lifecycle policies for old media
- [ ] CORS configured for web uploads
- [ ] Server-side encryption enabled
- [ ] CloudFront CDN optional (for media delivery)

### 9. Message Queue (SQS)
- [ ] FIFO queue created: `gapsense-messages.fifo`
- [ ] Dead-letter queue configured
- [ ] Message retention: 14 days
- [ ] IAM permissions for worker to consume

### 10. Secrets Management
- [ ] AWS Secrets Manager configured
- [ ] Secrets rotation policy enabled
- [ ] IAM roles grant access to secrets
- [ ] Application code updated to fetch from Secrets Manager

## Deployment Process

### 11. Docker Images
- [ ] Build multi-arch images (linux/amd64)
- [ ] Push to Amazon ECR
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker buildx build --platform linux/amd64 -t gapsense-web:latest --target=production .
docker tag gapsense-web:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/gapsense-web:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/gapsense-web:latest
```
- [ ] Images scanned for vulnerabilities (ECR scanning)

### 12. Database Migration
```bash
# Run migrations before deploying new code
docker run -e DATABASE_URL=<prod-url> gapsense-web alembic upgrade head
```
- [ ] Backup database before migration
- [ ] Test migrations on staging first
- [ ] Monitor for errors during migration

### 13. Curriculum Data Loading
```bash
# Load curriculum data (one-time setup)
docker run gapsense-web python scripts/load_curriculum.py
```
- [ ] Verify all nodes loaded correctly
- [ ] Check prerequisite edges created

### 14. Service Deployment
- [ ] Deploy web service (ECS/Fargate)
- [ ] Deploy worker service (ECS/Fargate)
- [ ] Verify health checks passing
- [ ] Check CloudWatch logs for errors
- [ ] Test /health endpoint

### 15. WhatsApp Integration
- [ ] Twilio webhook URL configured
- [ ] Webhook signature validation enabled
- [ ] Phone number provisioned and verified
- [ ] Template messages approved by Meta
- [ ] Test message flow end-to-end

## Post-Deployment Validation

### 16. Smoke Tests
- [ ] Web UI loads at https://your-domain.com
- [ ] Demo UI works: /demo
- [ ] Teacher dashboard accessible: /demo/reports/{phone}
- [ ] Exercise book upload works
- [ ] Worker processes tasks (check SQS queue)
- [ ] AI analysis completes (check logs)
- [ ] Dashboard shows results
- [ ] Detailed reports render correctly

### 17. Monitoring & Alerts
- [ ] CloudWatch alarms configured:
  - High CPU/memory usage
  - Database connection errors
  - SQS queue depth
  - Failed tasks
  - API error rates
- [ ] CloudWatch dashboards created
- [ ] SNS topics for alerts
- [ ] PagerDuty/Slack integration

### 18. Performance Testing
- [ ] Load test with 100 concurrent users
- [ ] Database query performance acceptable
- [ ] S3 upload/download speed acceptable
- [ ] Worker task processing time < 30s
- [ ] API response times < 2s (p95)

### 19. Security Hardening
- [ ] WAF rules configured (AWS WAF)
- [ ] Rate limiting enabled
- [ ] DDoS protection (AWS Shield)
- [ ] IAM least privilege principle applied
- [ ] Security group rules reviewed
- [ ] Encryption in transit (TLS)
- [ ] Encryption at rest (S3, RDS, EBS)

### 20. Documentation
- [ ] Runbook for common issues
- [ ] Incident response plan
- [ ] Rollback procedure documented
- [ ] Architecture diagram updated
- [ ] API documentation published
- [ ] User guides for teachers

## Rollback Plan

### 21. Rollback Procedure
1. Identify issue (monitoring alerts)
2. Revert ECS task definition to previous version
3. Force new deployment with old image
4. If database migration issue:
   - Run Alembic downgrade
   - Restore from RDS snapshot
5. Monitor health checks
6. Verify rollback successful

### 22. Communication
- [ ] Status page updated
- [ ] Stakeholders notified
- [ ] Post-mortem scheduled

## Cost Optimization

### 23. Resource Right-Sizing
- [ ] Review CloudWatch metrics for over-provisioning
- [ ] Use Reserved Instances for RDS (1-year commitment)
- [ ] Enable S3 Intelligent-Tiering
- [ ] Set up Cost Explorer alerts
- [ ] Use Fargate Spot for worker tasks (non-critical)

## Compliance & Legal

### 24. Data Privacy
- [ ] GDPR compliance reviewed (if EU users)
- [ ] Data retention policies implemented
- [ ] User data export capability
- [ ] User data deletion capability
- [ ] Privacy policy updated
- [ ] Terms of service updated

---

## Quick Reference Commands

### View Logs
```bash
aws logs tail /ecs/gapsense-web --follow
aws logs tail /ecs/gapsense-worker --follow
```

### Database Access
```bash
psql "postgresql://user:pass@rds-endpoint:5432/gapsense"
```

### Check SQS Queue
```bash
aws sqs get-queue-attributes --queue-url <URL> --attribute-names ApproximateNumberOfMessages
```

### Scale Services
```bash
aws ecs update-service --cluster gapsense --service gapsense-web --desired-count 3
aws ecs update-service --cluster gapsense --service gapsense-worker --desired-count 2
```

### Force New Deployment
```bash
aws ecs update-service --cluster gapsense --service gapsense-web --force-new-deployment
```

---

## Support Contacts

- **DevOps Lead**: [contact]
- **Database Admin**: [contact]
- **Security Team**: [contact]
- **On-Call**: [PagerDuty rotation]

---

**Last Updated**: 2026-03-15
**Version**: 1.0
**Maintained By**: DevOps Team
