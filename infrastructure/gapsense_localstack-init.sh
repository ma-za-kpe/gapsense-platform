#!/bin/bash
# LocalStack init script — creates SQS queues and S3 buckets for local dev

echo "Creating SQS queues..."
awslocal sqs create-queue --queue-name gapsense-messages.fifo --attributes FifoQueue=true,ContentBasedDeduplication=true
awslocal sqs create-queue --queue-name gapsense-messages-dlq.fifo --attributes FifoQueue=true

echo "Creating S3 buckets..."
awslocal s3 mb s3://gapsense-media-local

echo "LocalStack init complete!"
