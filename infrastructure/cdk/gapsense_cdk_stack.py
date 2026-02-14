"""
GapSense AWS CDK Infrastructure
Deploys: VPC, RDS PostgreSQL, Fargate (web + worker), SQS, S3, Cognito, ALB
Region: af-south-1 (Cape Town)
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_rds as rds,
    aws_sqs as sqs,
    aws_s3 as s3,
    aws_cognito as cognito,
    aws_secretsmanager as sm,
    aws_logs as logs,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
)
from constructs import Construct


class GapSenseStack(Stack):
    def __init__(self, scope: Construct, id: str, env_name: str = "staging", **kwargs):
        super().__init__(scope, id, **kwargs)

        is_prod = env_name == "production"

        # ==============================
        # VPC
        # ==============================
        vpc = ec2.Vpc(
            self, "GapSenseVPC",
            max_azs=2,
            nat_gateways=1 if not is_prod else 2,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
                ec2.SubnetConfiguration(name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=24),
                ec2.SubnetConfiguration(name="Isolated", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24),
            ],
        )

        # ==============================
        # RDS PostgreSQL
        # ==============================
        db_credentials = rds.DatabaseSecret(self, "DBCredentials", username="gapsense")

        database = rds.DatabaseInstance(
            self, "GapSenseDB",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_16_4),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.MEDIUM if is_prod else ec2.InstanceSize.SMALL
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            credentials=rds.Credentials.from_secret(db_credentials),
            database_name="gapsense",
            multi_az=is_prod,
            storage_encrypted=True,
            backup_retention=Duration.days(7 if is_prod else 1),
            deletion_protection=is_prod,
            removal_policy=RemovalPolicy.RETAIN if is_prod else RemovalPolicy.DESTROY,
            allocated_storage=20,
            max_allocated_storage=100 if is_prod else 50,
        )

        # ==============================
        # SQS Queues
        # ==============================
        dlq = sqs.Queue(
            self, "MessagesDLQ",
            queue_name=f"gapsense-messages-dlq-{env_name}.fifo",
            fifo=True,
            retention_period=Duration.days(14),
        )

        message_queue = sqs.Queue(
            self, "MessagesQueue",
            queue_name=f"gapsense-messages-{env_name}.fifo",
            fifo=True,
            content_based_deduplication=True,
            visibility_timeout=Duration.seconds(120),  # AI processing can take up to 60s
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=3, queue=dlq),
        )

        # ==============================
        # S3 — Media Storage
        # ==============================
        media_bucket = s3.Bucket(
            self, "MediaBucket",
            bucket_name=f"gapsense-media-{env_name}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                s3.LifecycleRule(expiration=Duration.days(365), prefix="voice-notes/"),
                s3.LifecycleRule(expiration=Duration.days(365), prefix="exercise-photos/"),
            ],
            removal_policy=RemovalPolicy.RETAIN,
        )

        # ==============================
        # Cognito — Authentication
        # ==============================
        user_pool = cognito.UserPool(
            self, "GapSenseUserPool",
            user_pool_name=f"gapsense-{env_name}",
            self_sign_up_enabled=False,  # Teachers added by admin
            sign_in_aliases=cognito.SignInAliases(phone=True, email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8, require_digits=True, require_lowercase=True,
            ),
            removal_policy=RemovalPolicy.RETAIN if is_prod else RemovalPolicy.DESTROY,
        )

        user_pool_client = user_pool.add_client(
            "GapSenseWebClient",
            auth_flows=cognito.AuthFlow(user_srp=True, user_password=True),
            generate_secret=False,
        )

        # ==============================
        # Secrets Manager — API Keys
        # ==============================
        anthropic_secret = sm.Secret(
            self, "AnthropicAPIKey",
            secret_name=f"gapsense/{env_name}/anthropic-api-key",
            description="Anthropic Claude API key for GapSense AI inference",
        )

        whatsapp_secret = sm.Secret(
            self, "WhatsAppSecrets",
            secret_name=f"gapsense/{env_name}/whatsapp",
            description="WhatsApp Cloud API token and phone number ID",
        )

        # ==============================
        # ECS Cluster
        # ==============================
        cluster = ecs.Cluster(
            self, "GapSenseCluster",
            vpc=vpc,
            cluster_name=f"gapsense-{env_name}",
            container_insights=is_prod,
        )

        # ==============================
        # Task Definition (shared between web & worker)
        # ==============================
        task_def = ecs.FargateTaskDefinition(
            self, "GapSenseTask",
            cpu=512 if is_prod else 256,
            memory_limit_mib=1024 if is_prod else 512,
        )

        # Common environment variables
        common_env = {
            "ENVIRONMENT": env_name,
            "AWS_REGION": self.region,
            "SQS_QUEUE_URL": message_queue.queue_url,
            "S3_MEDIA_BUCKET": media_bucket.bucket_name,
            "COGNITO_USER_POOL_ID": user_pool.user_pool_id,
            "COGNITO_CLIENT_ID": user_pool_client.user_pool_client_id,
            "LOG_LEVEL": "INFO" if is_prod else "DEBUG",
        }

        common_secrets = {
            "DATABASE_URL": ecs.Secret.from_secrets_manager(db_credentials, "connectionString"),
            "ANTHROPIC_API_KEY": ecs.Secret.from_secrets_manager(anthropic_secret),
            "WHATSAPP_API_TOKEN": ecs.Secret.from_secrets_manager(whatsapp_secret, "api_token"),
            "WHATSAPP_PHONE_NUMBER_ID": ecs.Secret.from_secrets_manager(whatsapp_secret, "phone_number_id"),
            "WHATSAPP_VERIFY_TOKEN": ecs.Secret.from_secrets_manager(whatsapp_secret, "verify_token"),
        }

        # Web container
        web_container = task_def.add_container(
            "web",
            image=ecs.ContainerImage.from_asset(".", file="Dockerfile", target="production"),
            environment=common_env,
            secrets=common_secrets,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="gapsense-web",
                log_retention=logs.RetentionDays.ONE_MONTH,
            ),
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8000/v1/health/ready || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
            ),
        )
        web_container.add_port_mappings(ecs.PortMapping(container_port=8000))

        # ==============================
        # Fargate Service — Web (ALB)
        # ==============================
        web_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "GapSenseWebService",
            cluster=cluster,
            task_definition=task_def,
            desired_count=1 if not is_prod else 2,
            public_load_balancer=True,
            listener_port=443,
            redirect_http=True,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
        )

        web_service.target_group.configure_health_check(
            path="/v1/health/ready",
            interval=Duration.seconds(30),
            healthy_threshold_count=2,
        )

        # Auto-scaling
        scaling = web_service.service.auto_scale_task_count(max_capacity=4 if is_prod else 2)
        scaling.scale_on_request_count("RequestScaling", requests_per_target=500)

        # ==============================
        # Fargate Service — Worker
        # ==============================
        worker_task_def = ecs.FargateTaskDefinition(
            self, "GapSenseWorkerTask",
            cpu=512 if is_prod else 256,
            memory_limit_mib=1024 if is_prod else 512,
        )

        worker_container = worker_task_def.add_container(
            "worker",
            image=ecs.ContainerImage.from_asset(".", file="Dockerfile", target="production"),
            command=["python", "-m", "gapsense.worker.main"],
            environment=common_env,
            secrets=common_secrets,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="gapsense-worker",
                log_retention=logs.RetentionDays.ONE_MONTH,
            ),
        )

        worker_service = ecs.FargateService(
            self, "GapSenseWorkerService",
            cluster=cluster,
            task_definition=worker_task_def,
            desired_count=1,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
        )

        # ==============================
        # IAM Permissions
        # ==============================
        message_queue.grant_send_messages(task_def.task_role)
        message_queue.grant_consume_messages(worker_task_def.task_role)
        media_bucket.grant_read_write(task_def.task_role)
        media_bucket.grant_read_write(worker_task_def.task_role)
        database.connections.allow_from(web_service.service, ec2.Port.tcp(5432))
        database.connections.allow_from(worker_service, ec2.Port.tcp(5432))

        # ==============================
        # Outputs
        # ==============================
        cdk.CfnOutput(self, "ALBURL", value=web_service.load_balancer.load_balancer_dns_name)
        cdk.CfnOutput(self, "QueueURL", value=message_queue.queue_url)
        cdk.CfnOutput(self, "DatabaseEndpoint", value=database.db_instance_endpoint_address)
        cdk.CfnOutput(self, "MediaBucket", value=media_bucket.bucket_name)
        cdk.CfnOutput(self, "CognitoUserPoolId", value=user_pool.user_pool_id)


# ==============================
# CDK App Entrypoint
# ==============================
app = cdk.App()

env_name = app.node.try_get_context("env") or "staging"

GapSenseStack(
    app, f"GapSense-{env_name.capitalize()}",
    env_name=env_name,
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region="af-south-1",
    ),
)

app.synth()
