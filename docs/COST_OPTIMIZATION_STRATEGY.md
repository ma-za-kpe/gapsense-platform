# GapSense Cost Optimization Strategy
**Leveraging Billing APIs for Zero-Waste Platform**

Version: 1.0.0 | Author: Maku Mazakpe | Date: 2026-02-14

---

## Executive Summary

**Current Budget:** $70-110/month MVP, $180-210/month production
**Goal:** Reduce waste by 30-40% through automated monitoring and right-sizing
**Target:** $50-70/month MVP, $120-150/month production

**Strategy:** Use billing APIs from AWS, Anthropic, and Meta to track every dollar in real-time, auto-scale resources, and prevent waste.

---

## 1. AWS COST TRACKING & OPTIMIZATION

### 1.1 AWS Cost Explorer API

**Track daily costs per service in real-time:**

```python
# src/gapsense/monitoring/aws_costs.py
import boto3
from datetime import datetime, timedelta
from typing import Dict

class AWSCostMonitor:
    """Monitor AWS costs using Cost Explorer API."""

    def __init__(self):
        self.ce_client = boto3.client('ce', region_name='af-south-1')

    async def get_daily_costs(self) -> Dict[str, float]:
        """Get yesterday's costs broken down by service."""
        end = datetime.now().date()
        start = end - timedelta(days=1)

        response = self.ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start.isoformat(),
                'End': end.isoformat()
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'}
            ]
        )

        costs = {}
        for result in response['ResultsByTime']:
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                costs[service] = cost

        return costs

    async def get_monthly_forecast(self) -> float:
        """Get AWS forecast for end-of-month total."""
        start = datetime.now().date()
        end = (start.replace(day=1) + timedelta(days=32)).replace(day=1)

        response = self.ce_client.get_cost_forecast(
            TimePeriod={
                'Start': start.isoformat(),
                'End': end.isoformat()
            },
            Metric='UNBLENDED_COST',
            Granularity='MONTHLY'
        )

        return float(response['Total']['Amount'])

    async def check_budget_alerts(self) -> Dict:
        """Check if we're exceeding budget thresholds."""
        forecast = await self.get_monthly_forecast()

        thresholds = {
            'staging': 80.0,   # $80/month max for staging
            'production': 160.0  # $160/month max for production
        }

        env = settings.ENVIRONMENT
        budget = thresholds.get(env, 100.0)

        return {
            'forecasted_cost': forecast,
            'budget': budget,
            'percentage_used': (forecast / budget) * 100,
            'at_risk': forecast > budget * 0.8,  # Alert at 80%
            'over_budget': forecast > budget
        }
```

**Automation: Daily Cost Email**
```python
# src/gapsense/monitoring/cost_alerts.py
async def send_daily_cost_report():
    """Send daily cost breakdown to team."""
    monitor = AWSCostMonitor()

    costs = await monitor.get_daily_costs()
    budget_status = await monitor.check_budget_alerts()

    # Top 5 expensive services
    top_services = sorted(costs.items(), key=lambda x: x[1], reverse=True)[:5]

    report = f"""
    📊 GapSense Daily AWS Cost Report

    Yesterday's Total: ${sum(costs.values()):.2f}

    Top Services:
    {chr(10).join(f"  • {svc}: ${cost:.2f}" for svc, cost in top_services)}

    Monthly Forecast: ${budget_status['forecasted_cost']:.2f}
    Budget: ${budget_status['budget']:.2f}
    Usage: {budget_status['percentage_used']:.1f}%

    {'⚠️  AT RISK - Projected to exceed budget!' if budget_status['at_risk'] else '✅ On track'}
    """

    # Send via email/Slack
    await notify_team(report)
```

---

### 1.2 AWS Budgets API - Automated Alerts

**Set up programmatic budgets with auto-actions:**

```python
# infrastructure/cdk/monitoring_stack.py
from aws_cdk import aws_budgets as budgets

class MonitoringStack(Stack):
    def __init__(self, scope, id, env_name='staging', **kwargs):
        super().__init__(scope, id, **kwargs)

        # Budget with alerts
        budget = budgets.CfnBudget(
            self, 'MonthlyBudget',
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name=f'gapsense-{env_name}-monthly',
                budget_type='COST',
                time_unit='MONTHLY',
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=80.0 if env_name == 'staging' else 160.0,
                    unit='USD'
                )
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator='GREATER_THAN',
                        notification_type='ACTUAL',
                        threshold=80,  # 80% of budget
                        threshold_type='PERCENTAGE'
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type='EMAIL',
                            address='maku@gapsense.app'
                        )
                    ]
                ),
                # Second alert at 100%
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator='GREATER_THAN',
                        notification_type='FORECASTED',
                        threshold=100,
                        threshold_type='PERCENTAGE'
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type='EMAIL',
                            address='maku@gapsense.app'
                        )
                    ]
                )
            ]
        )
```

---

### 1.3 CloudWatch Metrics - Resource Right-Sizing

**Track actual resource utilization to identify over-provisioning:**

```python
# src/gapsense/monitoring/resource_utilization.py
import boto3
from datetime import datetime, timedelta

class ResourceUtilizationMonitor:
    """Monitor resource usage to identify waste."""

    def __init__(self):
        self.cw_client = boto3.client('cloudwatch', region_name='af-south-1')
        self.rds_client = boto3.client('rds', region_name='af-south-1')
        self.ecs_client = boto3.client('ecs', region_name='af-south-1')

    async def check_rds_utilization(self) -> Dict:
        """Check if RDS is over/under-provisioned."""
        end = datetime.now()
        start = end - timedelta(days=7)  # Last 7 days

        # CPU Utilization
        cpu_response = self.cw_client.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='CPUUtilization',
            Dimensions=[
                {'Name': 'DBInstanceIdentifier', 'Value': 'gapsense-db'}
            ],
            StartTime=start,
            EndTime=end,
            Period=3600,  # 1 hour
            Statistics=['Average', 'Maximum']
        )

        avg_cpu = sum(dp['Average'] for dp in cpu_response['Datapoints']) / len(cpu_response['Datapoints'])
        max_cpu = max(dp['Maximum'] for dp in cpu_response['Datapoints'])

        # Database Connections
        conn_response = self.cw_client.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='DatabaseConnections',
            Dimensions=[
                {'Name': 'DBInstanceIdentifier', 'Value': 'gapsense-db'}
            ],
            StartTime=start,
            EndTime=end,
            Period=3600,
            Statistics=['Average', 'Maximum']
        )

        avg_connections = sum(dp['Average'] for dp in conn_response['Datapoints']) / len(conn_response['Datapoints'])

        return {
            'avg_cpu_7d': avg_cpu,
            'max_cpu_7d': max_cpu,
            'avg_connections': avg_connections,
            'recommendation': self._rds_recommendation(avg_cpu, max_cpu, avg_connections)
        }

    def _rds_recommendation(self, avg_cpu, max_cpu, avg_connections):
        """Recommend RDS instance size changes."""
        if avg_cpu < 20 and max_cpu < 40:
            return {
                'action': 'DOWNSIZE',
                'from': 't3.small',
                'to': 't3.micro',
                'savings': '$6.50/month',
                'reason': f'CPU avg {avg_cpu:.1f}%, max {max_cpu:.1f}% - underutilized'
            }
        elif avg_cpu > 70 or max_cpu > 90:
            return {
                'action': 'UPSIZE',
                'from': 't3.small',
                'to': 't3.medium',
                'cost': '+$13/month',
                'reason': f'CPU avg {avg_cpu:.1f}%, max {max_cpu:.1f}% - needs more capacity'
            }
        else:
            return {
                'action': 'KEEP',
                'reason': f'CPU avg {avg_cpu:.1f}%, max {max_cpu:.1f}% - right-sized'
            }

    async def check_fargate_utilization(self) -> Dict:
        """Check Fargate task CPU/memory usage."""
        # Similar logic for ECS metrics
        # Recommend smaller task sizes if underutilized
        pass
```

**Automation: Weekly Right-Sizing Report**
```python
async def weekly_rightsizing_check():
    """Check if we can downsize resources to save money."""
    monitor = ResourceUtilizationMonitor()

    rds_rec = await monitor.check_rds_utilization()
    fargate_rec = await monitor.check_fargate_utilization()

    report = f"""
    💰 Weekly Right-Sizing Recommendations

    RDS PostgreSQL:
      • Current: {rds_rec['recommendation']['from']}
      • Recommendation: {rds_rec['recommendation']['action']}
      • Potential savings: {rds_rec['recommendation'].get('savings', 'N/A')}
      • Reason: {rds_rec['recommendation']['reason']}

    Fargate Tasks:
      • [Similar breakdown]

    Total Potential Monthly Savings: $XX.XX
    """

    await notify_team(report)
```

---

### 1.4 NAT Gateway Optimization (Biggest Cost!)

**Current cost: $32-64/month (40% of AWS bill)**

**Optimization strategies:**

```python
# Option 1: NAT Instances instead of NAT Gateway (for staging)
# Savings: $32/month → $3.50/month (t3.nano NAT instance)

# Option 2: VPC Endpoints for AWS services (avoid NAT data transfer)
from aws_cdk import aws_ec2 as ec2

class NetworkStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Add VPC endpoints to avoid NAT Gateway costs
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3
        )

        self.vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER
        )

        self.vpc.add_interface_endpoint(
            "SQSEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SQS
        )

        # Estimated savings: $10-15/month in data transfer costs
```

---

## 2. ANTHROPIC CLAUDE COST TRACKING

### 2.1 Token Usage Monitoring

**Anthropic doesn't have a billing API, but we can track via response headers:**

```python
# src/gapsense/ai/cost_tracker.py
from dataclasses import dataclass
from datetime import datetime
import structlog

logger = structlog.get_logger()

@dataclass
class AIUsageMetrics:
    """Track AI usage and costs."""
    timestamp: datetime
    prompt_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    cost_usd: float

class AnthropicCostTracker:
    """Track Anthropic Claude usage and costs."""

    # Pricing (as of 2026-02)
    PRICING = {
        'claude-sonnet-4.5': {
            'input': 3.00 / 1_000_000,      # $3 per 1M tokens
            'output': 15.00 / 1_000_000,    # $15 per 1M tokens
            'cache_write': 3.75 / 1_000_000,
            'cache_read': 0.30 / 1_000_000  # 90% discount
        },
        'claude-haiku-4.5': {
            'input': 0.25 / 1_000_000,
            'output': 1.25 / 1_000_000,
            'cache_write': 0.30 / 1_000_000,
            'cache_read': 0.03 / 1_000_000
        }
    }

    async def track_usage(
        self,
        prompt_id: str,
        model: str,
        response: dict
    ) -> AIUsageMetrics:
        """Extract usage from Anthropic response and calculate cost."""
        usage = response.get('usage', {})

        input_tokens = usage.get('input_tokens', 0)
        output_tokens = usage.get('output_tokens', 0)
        cached_tokens = usage.get('cache_read_input_tokens', 0)
        cache_creation_tokens = usage.get('cache_creation_input_tokens', 0)

        pricing = self.PRICING.get(model, self.PRICING['claude-sonnet-4.5'])

        # Calculate cost
        cost = (
            (input_tokens - cached_tokens - cache_creation_tokens) * pricing['input'] +
            output_tokens * pricing['output'] +
            cached_tokens * pricing['cache_read'] +
            cache_creation_tokens * pricing['cache_write']
        )

        metrics = AIUsageMetrics(
            timestamp=datetime.now(),
            prompt_id=prompt_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            cost_usd=cost
        )

        # Log to database for analytics
        await self._store_metrics(metrics)

        logger.info(
            "ai_usage_tracked",
            prompt_id=prompt_id,
            model=model,
            cost_usd=round(cost, 6),
            cache_hit_rate=cached_tokens / max(input_tokens, 1) * 100
        )

        return metrics

    async def get_monthly_ai_costs(self) -> Dict:
        """Get AI costs for current month grouped by prompt."""
        query = """
        SELECT
            prompt_id,
            COUNT(*) as call_count,
            SUM(input_tokens) as total_input_tokens,
            SUM(output_tokens) as total_output_tokens,
            SUM(cached_tokens) as total_cached_tokens,
            SUM(cost_usd) as total_cost,
            AVG(cached_tokens::float / NULLIF(input_tokens, 0)) * 100 as avg_cache_hit_rate
        FROM ai_usage_metrics
        WHERE timestamp >= date_trunc('month', CURRENT_DATE)
        GROUP BY prompt_id
        ORDER BY total_cost DESC
        """

        results = await db.execute(query)

        total_cost = sum(r['total_cost'] for r in results)

        return {
            'total_cost': total_cost,
            'by_prompt': results,
            'projected_monthly': total_cost * 30 / datetime.now().day
        }

    async def optimize_prompt_usage(self) -> List[Dict]:
        """Identify prompts that could be optimized."""
        costs = await self.get_monthly_ai_costs()

        recommendations = []

        for prompt_data in costs['by_prompt']:
            # Low cache hit rate = wasting money
            if prompt_data['avg_cache_hit_rate'] < 50:
                recommendations.append({
                    'prompt_id': prompt_data['prompt_id'],
                    'issue': 'LOW_CACHE_HIT_RATE',
                    'current_rate': prompt_data['avg_cache_hit_rate'],
                    'potential_savings': prompt_data['total_cost'] * 0.4,  # Could save 40%
                    'action': 'Review prompt structure to maximize caching'
                })

            # Using expensive model when cheaper would work
            if 'sonnet' in prompt_data['prompt_id'] and prompt_data['avg_output_tokens'] < 500:
                recommendations.append({
                    'prompt_id': prompt_data['prompt_id'],
                    'issue': 'OVERPROVISIONED_MODEL',
                    'action': 'Consider switching to Haiku for short responses',
                    'potential_savings': prompt_data['total_cost'] * 0.7  # Haiku is ~70% cheaper
                })

        return recommendations
```

**Database schema for AI cost tracking:**
```sql
CREATE TABLE ai_usage_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    prompt_id VARCHAR(20) NOT NULL,
    model VARCHAR(50) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cached_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd DECIMAL(10, 6) NOT NULL,
    session_id UUID REFERENCES diagnostic_sessions(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_usage_timestamp ON ai_usage_metrics(timestamp DESC);
CREATE INDEX idx_ai_usage_prompt ON ai_usage_metrics(prompt_id);
CREATE INDEX idx_ai_usage_month ON ai_usage_metrics(date_trunc('month', timestamp));
```

---

### 2.2 Automated AI Cost Alerts

```python
# src/gapsense/monitoring/ai_cost_alerts.py
async def check_ai_budget():
    """Alert if AI costs exceed threshold."""
    tracker = AnthropicCostTracker()
    costs = await tracker.get_monthly_ai_costs()

    # Budget: $30/month for AI
    AI_BUDGET = 30.0

    if costs['projected_monthly'] > AI_BUDGET * 0.8:
        await notify_team(f"""
        ⚠️  AI Cost Alert

        Current month: ${costs['total_cost']:.2f}
        Projected: ${costs['projected_monthly']:.2f}
        Budget: ${AI_BUDGET}

        Top expensive prompts:
        {format_top_prompts(costs['by_prompt'][:3])}
        """)

    # Check optimization opportunities
    optimizations = await tracker.optimize_prompt_usage()
    if optimizations:
        total_potential_savings = sum(opt['potential_savings'] for opt in optimizations)
        await notify_team(f"""
        💡 AI Optimization Opportunities

        Potential monthly savings: ${total_potential_savings:.2f}

        Recommendations:
        {format_recommendations(optimizations)}
        """)
```

---

## 3. WHATSAPP CLOUD API COST TRACKING

### 3.1 Conversation-Based Pricing

**Meta's pricing:**
- First 1,000 conversations/month: **FREE**
- After that: ~$0.005-0.02 per conversation (varies by country)
- Business-initiated: Higher cost
- User-initiated: Lower cost

```python
# src/gapsense/monitoring/whatsapp_costs.py
class WhatsAppCostTracker:
    """Track WhatsApp conversation costs."""

    async def track_conversation(
        self,
        phone: str,
        direction: str,  # 'inbound' or 'outbound'
        category: str    # 'utility', 'marketing', 'authentication'
    ):
        """Track a WhatsApp conversation."""
        # Log to database
        await db.execute("""
            INSERT INTO whatsapp_conversations
            (phone, direction, category, timestamp)
            VALUES ($1, $2, $3, NOW())
        """, phone, direction, category)

    async def get_monthly_conversation_count(self) -> Dict:
        """Get conversation count for billing estimation."""
        result = await db.fetch_one("""
            SELECT
                COUNT(*) as total_conversations,
                COUNT(*) FILTER (WHERE direction = 'outbound') as business_initiated,
                COUNT(*) FILTER (WHERE direction = 'inbound') as user_initiated,
                COUNT(DISTINCT phone) as unique_users
            FROM whatsapp_conversations
            WHERE timestamp >= date_trunc('month', CURRENT_DATE)
        """)

        # Estimate costs (Ghana pricing)
        FREE_TIER = 1000
        COST_PER_CONVERSATION = 0.012  # $0.012 for utility conversations in Ghana

        billable = max(0, result['total_conversations'] - FREE_TIER)
        estimated_cost = billable * COST_PER_CONVERSATION

        return {
            'total_conversations': result['total_conversations'],
            'free_tier_remaining': max(0, FREE_TIER - result['total_conversations']),
            'billable_conversations': billable,
            'estimated_cost': estimated_cost,
            'unique_users': result['unique_users']
        }

    async def optimize_message_volume(self) -> List[Dict]:
        """Find ways to reduce WhatsApp costs."""
        # Check for high-frequency users (maybe spamming)
        high_volume_users = await db.fetch_all("""
            SELECT phone, COUNT(*) as message_count
            FROM whatsapp_conversations
            WHERE timestamp >= NOW() - INTERVAL '7 days'
            GROUP BY phone
            HAVING COUNT(*) > 20
            ORDER BY message_count DESC
        """)

        recommendations = []

        for user in high_volume_users:
            recommendations.append({
                'phone': user['phone'],
                'issue': 'HIGH_MESSAGE_VOLUME',
                'count_7d': user['message_count'],
                'action': 'Review conversation flow - may need rate limiting',
                'potential_savings': (user['message_count'] - 10) * 0.012  # Assume 10 is normal
            })

        return recommendations
```

---

## 4. UNIFIED COST DASHBOARD

### 4.1 Real-Time Cost Monitoring Endpoint

```python
# src/gapsense/monitoring/router.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

@router.get("/costs/summary")
async def get_cost_summary(
    current_user = Depends(require_admin)
):
    """Get real-time cost summary across all services."""
    aws_monitor = AWSCostMonitor()
    ai_tracker = AnthropicCostTracker()
    wa_tracker = WhatsAppCostTracker()

    # Get all costs
    aws_costs = await aws_monitor.get_daily_costs()
    aws_forecast = await aws_monitor.get_monthly_forecast()
    ai_costs = await ai_tracker.get_monthly_ai_costs()
    wa_costs = await wa_tracker.get_monthly_conversation_count()

    return {
        'aws': {
            'yesterday': sum(aws_costs.values()),
            'monthly_forecast': aws_forecast,
            'by_service': aws_costs
        },
        'anthropic': {
            'month_to_date': ai_costs['total_cost'],
            'projected_monthly': ai_costs['projected_monthly'],
            'by_prompt': ai_costs['by_prompt']
        },
        'whatsapp': {
            'conversations': wa_costs['total_conversations'],
            'estimated_cost': wa_costs['estimated_cost'],
            'free_tier_remaining': wa_costs['free_tier_remaining']
        },
        'total_monthly_forecast': (
            aws_forecast +
            ai_costs['projected_monthly'] +
            wa_costs['estimated_cost']
        )
    }

@router.get("/costs/optimizations")
async def get_optimization_recommendations(
    current_user = Depends(require_admin)
):
    """Get cost optimization recommendations."""
    resource_monitor = ResourceUtilizationMonitor()
    ai_tracker = AnthropicCostTracker()
    wa_tracker = WhatsAppCostTracker()

    return {
        'aws_rightsizing': await resource_monitor.check_all_resources(),
        'ai_optimizations': await ai_tracker.optimize_prompt_usage(),
        'whatsapp_optimizations': await wa_tracker.optimize_message_volume()
    }
```

---

## 5. AUTOMATED COST OPTIMIZATION ACTIONS

### 5.1 Auto-Scaling Based on Cost

```python
# src/gapsense/monitoring/auto_optimizer.py
class AutoCostOptimizer:
    """Automatically optimize resources to reduce costs."""

    async def run_daily_optimization(self):
        """Run daily cost optimization checks."""
        logger.info("Starting daily cost optimization")

        # 1. Check if we can downsize RDS during off-hours
        await self._optimize_rds_schedule()

        # 2. Scale down Fargate tasks if low traffic
        await self._optimize_fargate_tasks()

        # 3. Clean up old S3 objects
        await self._cleanup_s3()

        # 4. Pause expensive features if over budget
        await self._pause_if_over_budget()

    async def _optimize_rds_schedule(self):
        """Scale RDS down during low-traffic hours."""
        current_hour = datetime.now().hour

        # Ghana time: Low traffic 11pm - 6am
        if 23 <= current_hour or current_hour <= 6:
            # Check if we can use smaller instance
            rds = boto3.client('rds')
            instance = await rds.describe_db_instances(
                DBInstanceIdentifier='gapsense-db'
            )

            current_class = instance['DBInstances'][0]['DBInstanceClass']

            if current_class == 'db.t3.small':
                # Downsize to micro during off-hours (saves ~$5/day)
                await rds.modify_db_instance(
                    DBInstanceIdentifier='gapsense-db',
                    DBInstanceClass='db.t3.micro',
                    ApplyImmediately=True
                )
                logger.info("RDS downsized to t3.micro for off-hours")

    async def _optimize_fargate_tasks(self):
        """Scale down Fargate if low message volume."""
        # Check SQS queue depth
        sqs = boto3.client('sqs')
        attrs = await sqs.get_queue_attributes(
            QueueUrl=settings.SQS_QUEUE_URL,
            AttributeNames=['ApproximateNumberOfMessages']
        )

        queue_depth = int(attrs['Attributes']['ApproximateNumberOfMessages'])

        # If queue is empty, scale down worker to 0
        if queue_depth == 0:
            ecs = boto3.client('ecs')
            await ecs.update_service(
                cluster='gapsense-staging',
                service='worker',
                desiredCount=0
            )
            logger.info("Scaled worker to 0 - no messages in queue")

    async def _cleanup_s3(self):
        """Delete old media files to reduce S3 costs."""
        s3 = boto3.client('s3')
        bucket = settings.S3_MEDIA_BUCKET

        # Delete files older than 90 days (already in lifecycle policy, but double-check)
        cutoff = datetime.now() - timedelta(days=90)

        # Also: Delete failed uploads or temp files
        response = await s3.list_objects_v2(
            Bucket=bucket,
            Prefix='temp/'
        )

        for obj in response.get('Contents', []):
            if obj['LastModified'].replace(tzinfo=None) < cutoff:
                await s3.delete_object(
                    Bucket=bucket,
                    Key=obj['Key']
                )

        logger.info("S3 cleanup completed")

    async def _pause_if_over_budget(self):
        """Pause non-essential features if we're over budget."""
        monitor = AWSCostMonitor()
        budget_status = await monitor.check_budget_alerts()

        if budget_status['over_budget']:
            # Pause scheduled reminders (save on SQS + AI costs)
            await db.execute("""
                UPDATE parent_activities
                SET scheduled_reminder = NULL
                WHERE scheduled_reminder > NOW()
            """)

            # Alert team
            await notify_team(f"""
            🚨 BUDGET EXCEEDED - Auto-Optimization Triggered

            Forecasted: ${budget_status['forecasted_cost']:.2f}
            Budget: ${budget_status['budget']:.2f}

            Actions taken:
            • Paused scheduled reminders
            • Review needed before re-enabling
            """)

            logger.warning("Over budget - paused scheduled features")
```

---

## 6. IMPLEMENTATION CHECKLIST

### Phase 1: Monitoring (Week 1)
- [ ] Add `ai_usage_metrics` table to database schema
- [ ] Add `whatsapp_conversations` table to database schema
- [ ] Implement `AWSCostMonitor` service
- [ ] Implement `AnthropicCostTracker` in AI client
- [ ] Implement `WhatsAppCostTracker` in webhook handler
- [ ] Create `/monitoring/costs/summary` endpoint
- [ ] Set up AWS Budgets via CDK
- [ ] Deploy CloudWatch dashboards

### Phase 2: Alerting (Week 2)
- [ ] Daily cost report email
- [ ] Weekly right-sizing recommendations
- [ ] Budget alerts at 80% and 100%
- [ ] AI optimization alerts
- [ ] WhatsApp conversation warnings

### Phase 3: Auto-Optimization (Week 3)
- [ ] NAT Gateway → VPC Endpoints migration
- [ ] RDS off-hours scheduling
- [ ] Fargate auto-scaling based on queue depth
- [ ] S3 lifecycle cleanup automation
- [ ] Over-budget auto-pause feature

### Phase 4: Advanced (Week 4)
- [ ] Reserved Instance analysis (RDS)
- [ ] Savings Plans analysis (Fargate)
- [ ] Cost anomaly detection (ML-based)
- [ ] Multi-environment cost comparison
- [ ] ROI tracking per feature

---

## 7. EXPECTED SAVINGS

| Optimization | Current Cost | Optimized Cost | Monthly Savings |
|-------------|--------------|----------------|-----------------|
| **NAT Gateway** (staging: NAT instance instead) | $32 | $3.50 | **$28.50** |
| **VPC Endpoints** (reduce data transfer) | Included | Included | **$10** |
| **RDS Off-Hours Scaling** (12h/day downsize) | $13 | $9 | **$4** |
| **Fargate Right-Sizing** (reduce to 128 CPU) | $10 | $5 | **$5** |
| **S3 Aggressive Cleanup** (30-day lifecycle) | $2 | $1 | **$1** |
| **AI Prompt Caching** (increase cache hit rate 50%→80%) | $30 | $20 | **$10** |
| **AI Model Optimization** (Haiku for simple prompts) | Included | Included | **$5** |
| **WhatsApp Template Optimization** (reduce re-engagement frequency) | $5 | $3 | **$2** |

**Total Monthly Savings: $65.50 (46% reduction!)**

**New Costs:**
- MVP: $76 → **$50**
- Production: $156 → **$105**

---

## 8. COST MONITORING DASHBOARD (UI)

**Create admin dashboard at `/admin/costs`:**

```jsx
// Simple HTML dashboard showing:
{
  "aws": {
    "current_month": "$45.23",
    "forecast": "$67.50",
    "top_services": [
      {"name": "NAT Gateway", "cost": "$16.00", "percentage": 35.4},
      {"name": "RDS", "cost": "$13.00", "percentage": 28.8},
      {"name": "Fargate", "cost": "$10.00", "percentage": 22.1}
    ]
  },
  "ai": {
    "current_month": "$12.34",
    "forecast": "$18.50",
    "cache_hit_rate": "67%",
    "top_prompts": [
      {"id": "DIAG-001", "cost": "$5.00", "calls": 234},
      {"id": "PARENT-001", "cost": "$3.50", "calls": 456}
    ]
  },
  "whatsapp": {
    "conversations": 450,
    "free_tier_remaining": 550,
    "estimated_cost": "$0.00"
  },
  "optimizations": [
    "💰 Downsize RDS to t3.micro - save $4/month",
    "🔄 Increase AI cache hit rate - save $10/month"
  ]
}
```

---

## CONCLUSION

By leveraging billing APIs from AWS, tracking Anthropic usage, and monitoring WhatsApp conversations, we can:

1. **Track every dollar in real-time** (daily granularity)
2. **Alert before overspending** (80% budget threshold)
3. **Auto-optimize resources** (right-sizing, scaling, cleanup)
4. **Reduce costs by 40-50%** ($76 → $50 for MVP)

**Key principle:** *Measure everything, optimize continuously, never waste.*
