#!/bin/bash

set -e

echo "========================================="
echo "Streamlit Application Deployment"
echo "========================================="
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Step 1: Build and Push Docker Image
echo "Step 1: Building and pushing Docker image..."

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Could not get AWS Account ID. Please check your AWS credentials."
    exit 1
fi

ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/ws_streamlit"
IMAGE_TAG="latest"

echo "  ECR Repository: ${ECR_REPO}"
echo "  Image Tag: ${IMAGE_TAG}"
echo "  AWS Region: ${AWS_REGION}"
echo ""

echo "  Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO}

if [ $? -ne 0 ]; then
    echo "❌ Failed to login to ECR"
    exit 1
fi

echo "  Building Docker image..."
docker build -t ws-streamlit:${IMAGE_TAG} .

if [ $? -ne 0 ]; then
    echo "❌ Failed to build Docker image"
    exit 1
fi

echo "  Tagging image for ECR..."
docker tag ws-streamlit:${IMAGE_TAG} ${ECR_REPO}:${IMAGE_TAG}

echo "  Pushing image to ECR..."
docker push ${ECR_REPO}:${IMAGE_TAG}

if [ $? -ne 0 ]; then
    echo "❌ Failed to push Docker image to ECR"
    exit 1
fi

echo "  ✅ Image successfully pushed to ${ECR_REPO}:${IMAGE_TAG}"

echo ""
echo "Step 2: Getting EC2 instance information..."
cd ../ws_infrastructure

# Check if terraform is initialized
if [ ! -d ".terraform" ]; then
    echo "⚠️  Terraform not initialized. Initializing..."
    terraform init -reconfigure > /dev/null 2>&1 || true
fi

EC2_IP=$(terraform output -raw ec2_public_ip 2>/dev/null || echo "")
if [ -z "$EC2_IP" ]; then
    echo "❌ Could not get EC2 IP from terraform output"
    echo "Please ensure terraform is applied and outputs are available"
    exit 1
fi

echo "EC2 IP: ${EC2_IP}"

# Check SSH key
KEY_FILE="$HOME/.ssh/ws-analytics-key-pair.pem"
if [ ! -f "$KEY_FILE" ]; then
    echo "❌ SSH key not found: $KEY_FILE"
    exit 1
fi

echo ""
echo "Step 3: Deploying to EC2 instance..."
echo "This will:"
echo "  - Pull the latest Docker image"
echo "  - Stop and remove the old container"
echo "  - Start a new container with the latest image"
echo ""

ssh -i "$KEY_FILE" ec2-user@${EC2_IP} << 'DEPLOY_EOF'
set -e

echo "Logging into ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 596947055484.dkr.ecr.us-east-1.amazonaws.com/ws_streamlit

echo "Pulling latest image..."
docker pull 596947055484.dkr.ecr.us-east-1.amazonaws.com/ws_streamlit:latest

echo "Stopping and removing old container..."
docker stop ws-analytics-streamlit 2>/dev/null || echo "Container not running"
docker rm ws-analytics-streamlit 2>/dev/null || echo "Container already removed"

echo "Getting Redshift configuration from SSM..."
DB_HOST=$(aws ssm get-parameter --name /ws-analytics/database/host --with-decryption --query 'Parameter.Value' --output text)
DB_DATABASE=$(aws ssm get-parameter --name /ws-analytics/database/database --query 'Parameter.Value' --output text)
DB_USER=$(aws ssm get-parameter --name /ws-analytics/database/username --with-decryption --query 'Parameter.Value' --output text)

if [ -z "$DB_HOST" ] || [ -z "$DB_DATABASE" ] || [ -z "$DB_USER" ]; then
    echo "⚠️  Warning: Could not retrieve all Redshift configuration from SSM"
    echo "DB_HOST: ${DB_HOST:0:30}..."
    echo "DB_DATABASE: $DB_DATABASE"
    echo "DB_USER: $DB_USER"
fi

echo "Starting new container..."
echo "Note: Using --network host to allow access to EC2 instance metadata service (IAM role)"
echo "      Port 8501 will be directly accessible on the host"
docker run -d \
  --name ws-analytics-streamlit \
  --restart unless-stopped \
  --network host \
  -v /home/ec2-user/.aws:/root/.aws:ro \
  -e ENVIRONMENT=staging \
  -e REGION=us-east-1 \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e REDSHIFT_HOST="$DB_HOST" \
  -e REDSHIFT_DATABASE="$DB_DATABASE" \
  -e REDSHIFT_USER="$DB_USER" \
  -e REDSHIFT_CLUSTER_ID=ws-redshift-workgroup \
  -e USE_IAM_AUTH=true \
  596947055484.dkr.ecr.us-east-1.amazonaws.com/ws_streamlit:latest

echo "Waiting for container to start..."
sleep 5

echo ""
echo "Container status:"
docker ps | grep streamlit || echo "⚠️  Container not found in running containers"

echo ""
echo "Recent logs:"
docker logs ws-analytics-streamlit 2>&1 | tail -20 || echo "No logs yet"
DEPLOY_EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "✅ Deployment completed successfully!"
    echo "========================================="
    echo ""
    echo "Application URL: http://${EC2_IP}:8501"
    echo ""
    echo "To view logs:"
    echo "  ssh -i $KEY_FILE ec2-user@${EC2_IP} 'docker logs ws-analytics-streamlit -f'"
    echo ""
    echo "To check status:"
    echo "  ssh -i $KEY_FILE ec2-user@${EC2_IP} 'docker ps | grep streamlit'"
else
    echo ""
    echo "❌ Deployment failed. Check the error messages above."
    exit 1
fi

