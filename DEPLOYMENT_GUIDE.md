# Streamlit Dashboard - AWS EC2 Deployment Guide

## Overview
Deploy the Streamlit dashboard to AWS EC2 with Redshift integration using your existing infrastructure.

## Prerequisites
✅ Your infrastructure already has:
- EC2 instance configured (`ws_infrastructure/compute.tf`)
- ECR repository for Streamlit (`ws_infrastructure/ecr.tf`)
- Redshift Serverless cluster (`ws_infrastructure/database.tf`)
- User data script (`ws_infrastructure/templates/user_data.sh`)

## What Needs to Be Done

### 1. Add Redshift IAM Permissions to EC2 Role

**File**: `ws_infrastructure/iam.tf`

Add this IAM policy to allow EC2 to access Redshift with IAM authentication:

```terraform
# Add after existing policies in iam.tf

resource "aws_iam_policy" "redshift_policy" {
  name        = "${var.project_name}-redshift-policy"
  description = "Policy for EC2 to access Redshift with IAM authentication"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "redshift:GetClusterCredentials",
          "redshift:DescribeClusters",
          "redshift-serverless:GetCredentials",
          "redshift-serverless:GetWorkgroup"
        ]
        Resource = "*"
      }
    ]
  })
}
```

**File**: `ws_infrastructure/compute.tf`

Add this attachment (around line 133, after other attachments):

```terraform
resource "aws_iam_role_policy_attachment" "ec2_redshift_attachment" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.redshift_policy.arn
}
```

### 2. Update User Data Script

The `user_data.sh` already has the correct environment variables (we updated them earlier):
- `REDSHIFT_HOST`, `REDSHIFT_DATABASE`, `REDSHIFT_USER`, `REDSHIFT_CLUSTER_ID`
- `USE_IAM_AUTH=true`, `REGION`

**File**: `ws_infrastructure/templates/user_data.sh` (lines 49-56)

✅ Already updated with correct variables!

### 3. Add Cluster ID to user_data.sh

**File**: `ws_infrastructure/compute.tf` (line 21-29)

Update the user_data templatefile call to include `redshift_cluster_id`:

```terraform
user_data = base64encode(templatefile("${path.module}/templates/user_data.sh", {
    aws_region          = var.aws_region
    streamlit_repo_url  = aws_ecr_repository.streamlit.repository_url
    project_name        = var.project_name
    db_host             = aws_redshiftserverless_workgroup.analytics.endpoint[0].address
    db_password         = random_password.database_password.result
    db_username         = local.db_admin_username
    db_database         = local.db_name
    redshift_cluster_id = aws_redshiftserverless_workgroup.analytics.workgroup_name
  }))
```

## Deployment Steps

### Step 1: Build and Push Docker Image to ECR

```bash
cd /home/luiz/Programming/WS/ws_streamlit

# Get ECR login
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/ws_streamlit"

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO}

# Build Docker image
docker build -t ws-streamlit:latest .

# Tag for ECR
docker tag ws-streamlit:latest ${ECR_REPO}:latest

# Push to ECR
docker push ${ECR_REPO}:latest
```

### Step 2: Update Infrastructure

```bash
cd /home/luiz/Programming/WS/ws_infrastructure

# Initialize Terraform (if not already done)
terraform init

# Plan the changes
terraform plan

# Apply the changes
terraform apply
```

This will:
- Create/update the EC2 instance
- Pull the Streamlit Docker image from ECR
- Start the container with proper environment variables
- Connect to Redshift using IAM authentication

### Step 3: Verify Deployment

After Terraform completes:

```bash
# Get the EC2 public IP
terraform output ec2_public_ip

# Or get the Elastic IP
terraform output eip_public_ip
```

Access the dashboard:
```
http://<EC2_PUBLIC_IP>:8501
```

### Step 4: Check Logs (if needed)

SSH into EC2:
```bash
ssh -i your-key.pem ec2-user@<EC2_PUBLIC_IP>

# Check container status
docker ps

# View Streamlit logs
docker logs ws-streamlit-production

# View startup logs
tail -f /var/log/app-startup.log
```

## Architecture

```
┌─────────────────┐
│   Developer     │
│   (You)         │
└────────┬────────┘
         │ 1. Build & Push
         ▼
┌─────────────────┐
│   AWS ECR       │
│   ws_streamlit  │
└────────┬────────┘
         │ 2. Pull Image
         ▼
┌─────────────────┐      ┌──────────────────┐
│   EC2 Instance  │◄────►│ Redshift         │
│   - IAM Role    │ IAM  │ Serverless       │
│   - Streamlit   │ Auth │ (gold tables)    │
│   - Port 8501   │      │                  │
└─────────────────┘      └──────────────────┘
         │
         │ 3. Access Dashboard
         ▼
┌─────────────────┐
│   Browser       │
│   :8501         │
└─────────────────┘
```

## Environment Variables (Set by Terraform)

The EC2 instance will receive these environment variables:

```bash
ENVIRONMENT=production
REDSHIFT_HOST=<workgroup-endpoint>.us-east-1.redshift-serverless.amazonaws.com
REDSHIFT_DATABASE=dev
REDSHIFT_USER=admin
REDSHIFT_CLUSTER_ID=ws-redshift-workgroup
USE_IAM_AUTH=true
REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
```

## Redshift Connection Flow

1. **EC2 IAM Role**: Assumes role with `redshift-serverless:GetCredentials` permission
2. **Streamlit App**: Uses `boto3` to call `get_credentials()` API
3. **Temporary Credentials**: Receives temporary username/password (valid 15 minutes)
4. **Connection**: Connects to Redshift using temporary credentials
5. **Query**: Executes queries on `gold_team_match_summary`, `gold_player_match_summary`, `fct_events`
6. **Visualizations**: Displays data in Plotly charts

## Troubleshooting

### Issue: "Unable to connect to Redshift"

**Check**:
1. EC2 IAM role has Redshift permissions
2. Security group allows EC2 → Redshift (port 5439)
3. Redshift is publicly accessible or EC2 is in correct VPC
4. REDSHIFT_CLUSTER_ID matches workgroup name

**Fix**:
```bash
# SSH into EC2
ssh ec2-user@<EC2_IP>

# Check environment variables
docker exec ws-streamlit-production env | grep REDSHIFT

# Test IAM credentials
aws redshift-serverless get-credentials \
  --workgroup-name ws-redshift-workgroup \
  --db-name dev
```

### Issue: "Container not starting"

**Check**:
```bash
# View container logs
docker logs ws-streamlit-production

# Check if image was pulled
docker images | grep streamlit

# Restart container
cd /opt/ws
./start_app.sh
```

### Issue: "Demo mode showing instead of real data"

**Reasons**:
- Missing REDSHIFT_CLUSTER_ID environment variable
- IAM permissions not working
- Network connectivity to Redshift

**Fix**: Check logs for specific error messages

## Updating the Dashboard

To deploy a new version:

```bash
# 1. Make changes to code locally
cd /home/luiz/Programming/WS/ws_streamlit

# 2. Test locally
streamlit run src/app.py

# 3. Build and push new image
docker build -t ws-streamlit:latest .
docker tag ws-streamlit:latest ${ECR_REPO}:latest
docker push ${ECR_REPO}:latest

# 4. SSH to EC2 and restart
ssh ec2-user@<EC2_IP>
cd /opt/ws
./start_app.sh
```

Or use Terraform to recreate the instance:
```bash
terraform taint aws_instance.streamlit_server
terraform apply
```

## Security Considerations

✅ IAM role-based authentication (no passwords in environment)
✅ Encrypted EBS volumes
✅ Security groups limiting access
✅ HTTPS recommended (add ALB + SSL certificate)
✅ Secrets in SSM Parameter Store

## Cost Estimate

- **EC2 t3.medium**: ~$30/month (on-demand)
- **Redshift Serverless**: ~$0.50/hour when active (8 RPU base)
- **ECR Storage**: < $1/month
- **Data Transfer**: Minimal (same region)

**Total**: ~$30-100/month depending on Redshift usage

## Next Steps

1. ✅ Add IAM policy for Redshift access
2. ✅ Update user_data.sh with cluster_id
3. ✅ Build and push Docker image to ECR
4. ✅ Run `terraform apply`
5. ✅ Access dashboard at EC2 IP
6. 🔄 (Optional) Add ALB + Route53 for custom domain
7. 🔄 (Optional) Set up CloudWatch dashboards

