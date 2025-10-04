#!/bin/bash

# AWS Optimized Deployment Script for Arzana PO Processor
# Uses App Runner + S3 + CloudFront for best cost/performance ratio

echo "🚀 Starting AWS optimized deployment..."

# Check prerequisites
command -v aws >/dev/null 2>&1 || { echo "❌ AWS CLI not found. Please install it first."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ Node.js/npm not found. Please install it first."; exit 1; }

echo "✅ Prerequisites found"

# Step 1: Deploy Flask Server to AWS App Runner
echo "📦 Deploying Flask server to AWS App Runner..."

# Create App Runner service
aws apprunner create-service \
    --service-name "arzana-po-processor" \
    --source-configuration '{
        "AutoDeploymentsEnabled": true,
        "CodeRepository": {
            "RepositoryUrl": "https://github.com/your-username/arzana-po-processor",
            "SourceCodeVersion": {
                "Type": "BRANCH",
                "Value": "main"
            },
            "CodeConfiguration": {
                "ConfigurationSource": "REPOSITORY",
                "CodeConfigurationValues": {
                    "Runtime": "PYTHON_3",
                    "BuildCommand": "pip install -r requirements.txt",
                    "StartCommand": "python app.py",
                    "RuntimeEnvironmentVariables": {
                        "FLASK_ENV": "production",
                        "PORT": "8080"
                    }
                }
            }
        }
    }' \
    --instance-configuration '{
        "Cpu": "0.25 vCPU",
        "Memory": "0.5 GB",
        "InstanceRoleArn": "arn:aws:iam::YOUR_ACCOUNT:role/AppRunnerInstanceRole"
    }' \
    --auto-scaling-configuration-arn "arn:aws:apprunner:us-east-1:YOUR_ACCOUNT:autoscalingconfiguration/DefaultConfiguration/1/00000000000000000000000000000001"

# Wait for service to be ready
echo "⏳ Waiting for App Runner service to be ready..."
aws apprunner wait service-updated --service-arn $(aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`arzana-po-processor`].ServiceArn' --output text)

# Get App Runner URL
APP_RUNNER_URL=$(aws apprunner describe-service --service-arn $(aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`arzana-po-processor`].ServiceArn' --output text) --query 'Service.ServiceUrl' --output text)
echo "🔗 App Runner URL: $APP_RUNNER_URL"

# Step 2: Build Outlook Add-in
echo "📦 Building Outlook add-in..."
cd Arzana
npm run build
cd ..

# Step 3: Deploy Add-in to S3 + CloudFront
echo "☁️ Deploying add-in to S3 + CloudFront..."

# Create S3 bucket
BUCKET_NAME="arzana-outlook-addin-$(date +%s)"
aws s3 mb s3://$BUCKET_NAME --region us-east-1

# Set bucket policy for CloudFront
cat > bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
        }
    ]
}
EOF

aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://bucket-policy.json

# Upload add-in files
aws s3 sync Arzana/dist/ s3://$BUCKET_NAME --delete

# Create CloudFront distribution
cat > cloudfront-config.json << EOF
{
    "CallerReference": "arzana-addin-$(date +%s)",
    "Comment": "Arzana Outlook Add-in",
    "DefaultRootObject": "taskpane.html",
    "Origins": {
        "Quantity": 1,
        "Items": [
            {
                "Id": "S3-$BUCKET_NAME",
                "DomainName": "$BUCKET_NAME.s3.amazonaws.com",
                "S3OriginConfig": {
                    "OriginAccessIdentity": ""
                }
            }
        ]
    },
    "DefaultCacheBehavior": {
        "TargetOriginId": "S3-$BUCKET_NAME",
        "ViewerProtocolPolicy": "redirect-to-https",
        "TrustedSigners": {
            "Enabled": false,
            "Quantity": 0
        },
        "ForwardedValues": {
            "QueryString": false,
            "Cookies": {
                "Forward": "none"
            }
        },
        "MinTTL": 0,
        "DefaultTTL": 3600,
        "MaxTTL": 86400
    },
    "Enabled": true,
    "PriceClass": "PriceClass_100"
}
EOF

DISTRIBUTION_ID=$(aws cloudfront create-distribution --distribution-config file://cloudfront-config.json --query 'Distribution.Id' --output text)
echo "📡 CloudFront Distribution ID: $DISTRIBUTION_ID"

# Wait for distribution to deploy
echo "⏳ Waiting for CloudFront distribution to deploy..."
aws cloudfront wait distribution-deployed --id $DISTRIBUTION_ID

# Get CloudFront domain
CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution --id $DISTRIBUTION_ID --query 'Distribution.DomainName' --output text)
ADDIN_URL="https://$CLOUDFRONT_DOMAIN"
echo "🔗 Add-in URL: $ADDIN_URL"

# Step 4: Update URLs in code
echo "🔧 Updating URLs in manifest and taskpane..."

# Update manifest.xml
sed -i "s|https://localhost:3000|$ADDIN_URL|g" Arzana/manifest.xml
sed -i "s|https://localhost:5000|$APP_RUNNER_URL|g" Arzana/manifest.xml

# Update taskpane.ts
sed -i "s|http://127.0.0.1:5000|$APP_RUNNER_URL|g" Arzana/src/taskpane/taskpane.ts
sed -i "s|http://localhost:5000|$APP_RUNNER_URL|g" Arzana/src/taskpane/taskpane.ts

# Rebuild and redeploy with updated URLs
cd Arzana
npm run build
cd ..

aws s3 sync Arzana/dist/ s3://$BUCKET_NAME --delete
aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"

# Cleanup
rm bucket-policy.json cloudfront-config.json

echo ""
echo "🎉 AWS Optimized Deployment Complete!"
echo "====================================="
echo "Flask Server (App Runner): $APP_RUNNER_URL"
echo "Outlook Add-in (CloudFront): $ADDIN_URL"
echo "S3 Bucket: $BUCKET_NAME"
echo "CloudFront Distribution: $DISTRIBUTION_ID"
echo ""
echo "💰 Estimated Monthly Costs:"
echo "- App Runner: ~$25-45"
echo "- S3 + CloudFront: ~$2-8"
echo "- Total: ~$27-53/month"
echo ""
echo "📋 Next Steps:"
echo "1. Test Flask server: $APP_RUNNER_URL/api/health"
echo "2. Test add-in: $ADDIN_URL/taskpane.html"
echo "3. Update manifest.xml with production URLs"
echo "4. Distribute to users"
echo ""
echo "💾 Save these URLs for future reference!"
